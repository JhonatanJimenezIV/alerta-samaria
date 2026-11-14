"""http.py — Respuestas en formato proxy de API Gateway, CORS y utilidades de request."""
import json
import logging
from decimal import Decimal
from typing import Any, Callable

from comun.db import desde_dynamo, obtener_usuario

logger = logging.getLogger(__name__)

CORS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,X-Usuario-Id",
    "Access-Control-Allow-Methods": "GET,POST,PATCH,OPTIONS",
}


class ErrorApi(Exception):
    """Error controlado: se convierte en una respuesta HTTP con su código."""

    def __init__(self, status: int, mensaje: str) -> None:
        super().__init__(mensaje)
        self.status = status
        self.mensaje = mensaje


def respuesta(status: int, body: Any) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", **CORS},
        "body": json.dumps(desde_dynamo(body), default=str, ensure_ascii=False),
    }


def error(status: int, mensaje: str) -> dict[str, Any]:
    return respuesta(status, {"error": mensaje})


def cuerpo_json(event: dict[str, Any]) -> dict[str, Any]:
    """Body JSON; los decimales se leen como Decimal (DynamoDB no acepta float)."""
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    if "application/json" not in headers.get("content-type", ""):
        raise ErrorApi(400, "Se requiere el header Content-Type: application/json")
    try:
        datos = json.loads(event.get("body") or "{}", parse_float=Decimal)
    except json.JSONDecodeError:
        raise ErrorApi(400, "El cuerpo de la petición no es JSON válido")
    if not isinstance(datos, dict):
        raise ErrorApi(400, "El cuerpo debe ser un objeto JSON")
    return datos


def usuario_actual(event: dict[str, Any], rol: str | None = None) -> dict[str, Any]:
    """
    Autenticación simplificada del proyecto: header X-Usuario-Id.
    (En producción se reemplazaría por un JWT/Cognito; no es el foco del curso.)
    """
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    uid = headers.get("x-usuario-id")
    if not uid:
        raise ErrorApi(401, "Se requiere iniciar sesión (header X-Usuario-Id)")
    usuario = obtener_usuario(uid)
    if not usuario:
        raise ErrorApi(401, "Usuario no encontrado")
    if rol and usuario.get("rol") != rol:
        raise ErrorApi(403, f"Esta operación requiere el rol '{rol}'")
    return usuario


def query(event: dict[str, Any]) -> dict[str, str]:
    return event.get("queryStringParameters") or {}


def ip_origen(event: dict[str, Any]) -> str:
    return ((event.get("requestContext") or {}).get("identity") or {}).get("sourceIp") or "desconocida"


def despachar(event: dict[str, Any], rutas: dict[tuple[str, str], Callable[[dict[str, Any]], dict[str, Any]]]) -> dict[str, Any]:
    """Enruta por (método, recurso de API Gateway), p. ej. ('GET', '/reportes/{id}')."""
    metodo = event.get("httpMethod", "GET")
    recurso = event.get("resource", "")
    logger.info("REQUEST %s %s", metodo, recurso)
    if metodo == "OPTIONS":
        return respuesta(200, {})
    manejador = rutas.get((metodo, recurso))
    if not manejador:
        return error(405, f"Ruta no soportada: {metodo} {recurso}")
    try:
        return manejador(event)
    except ErrorApi as e:
        return error(e.status, e.mensaje)
    except Exception:  # noqa: BLE001
        logger.exception("Error no controlado")
        return error(500, "Error interno del servidor")
