"""
db.py — Acceso a la tabla única de DynamoDB y utilidades de datos.

Claves (Single Table Design):
    Reporte        PK=REP#<id>            SK=META
    Evento         PK=REP#<id>            SK=EVT#<fecha>
    Confirmación   PK=REP#<id>            SK=CONF#<usuario>
    Usuario        PK=USR#<id>            SK=PERFIL
    Correo único   PK=EMAIL#<correo>      SK=USUARIO
    Estadística    PK=STAT#DIA#<fecha>    SK=ZONA#<barrio>#CAT#<cat>#<subtipo>
    Estadística    PK=STAT#ZONA#<barrio>  SK=<fecha>#<cat>#<subtipo>
    Catálogo       PK=CONFIG              SK=CATEGORIAS
"""
import os
import secrets
import time
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import boto3

_recurso: Any = None
_tabla: Any = None
_cliente: Any = None


def tabla() -> Any:
    """Tabla DynamoDB (se crea una vez por contenedor Lambda y se reutiliza)."""
    global _recurso, _tabla
    if _tabla is None:
        # boto3 lee AWS_ENDPOINT_URL del entorno y apunta al emulador
        _recurso = boto3.resource("dynamodb")
        _tabla = _recurso.Table(os.environ["TABLE_NAME"])
    return _tabla


def cliente() -> Any:
    """
    Cliente de bajo nivel (para TransactWriteItems con tipos {"S": ...}).
    Ojo: resource.meta.client NO sirve, porque re-serializa los valores.
    """
    global _cliente
    if _cliente is None:
        _cliente = boto3.client("dynamodb")
    return _cliente


def reiniciar() -> None:
    """Solo para tests: fuerza a crear de nuevo el recurso (moto)."""
    global _recurso, _tabla, _cliente
    _recurso = None
    _tabla = None
    _cliente = None


# ── Tiempo e identificadores ─────────────────────────────────────────

def ahora() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    """Fecha ISO-8601 en UTC con milisegundos (ordenable como texto)."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def epoch(dt: datetime) -> int:
    return int(dt.timestamp())


_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def ulid() -> str:
    """
    ULID: 48 bits de tiempo (ms) + 80 bits aleatorios en base32 Crockford.
    Es único y además se ordena por fecha de creación.
    """
    valor = (int(time.time() * 1000) << 80) | secrets.randbits(80)
    chars = []
    for _ in range(26):
        chars.append(_CROCKFORD[valor & 31])
        valor >>= 5
    return "".join(reversed(chars))


def slug(texto: str) -> str:
    """'El Rodadero' → 'el-rodadero' (sin tildes, para usar en claves)."""
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return "-".join(sin_tildes.lower().split())


# ── Conversión de tipos ──────────────────────────────────────────────

def desde_dynamo(valor: Any) -> Any:
    """Decimal → int/float, recursivo (json.dumps no serializa Decimal)."""
    if isinstance(valor, Decimal):
        return int(valor) if valor == valor.to_integral_value() else float(valor)
    if isinstance(valor, dict):
        return {k: desde_dynamo(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [desde_dynamo(v) for v in valor]
    if isinstance(valor, set):
        return [desde_dynamo(v) for v in valor]
    return valor


def a_decimal(valor: Any) -> Decimal:
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


# ── Lecturas frecuentes ──────────────────────────────────────────────

def obtener_usuario(usuario_id: str) -> dict[str, Any] | None:
    r = tabla().get_item(Key={"PK": f"USR#{usuario_id}", "SK": "PERFIL"})
    return r.get("Item")


def obtener_reporte(reporte_id: str) -> dict[str, Any] | None:
    r = tabla().get_item(Key={"PK": f"REP#{reporte_id}", "SK": "META"})
    return r.get("Item")


def obtener_reporte_completo(reporte_id: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """
    Un solo Query sobre PK=REP#<id> trae el reporte (META), su historial
    (EVT#...) y sus confirmaciones (CONF#...). Sin "JOIN" en la Lambda.
    """
    r = tabla().query(KeyConditionExpression="PK = :pk",
                      ExpressionAttributeValues={":pk": f"REP#{reporte_id}"})
    meta = None
    eventos: list[dict[str, Any]] = []
    for item in r.get("Items", []):
        if item["SK"] == "META":
            meta = item
        elif item["SK"].startswith("EVT#"):
            eventos.append(item)
    eventos.sort(key=lambda e: e["SK"])
    return meta, eventos


def obtener_reportes_lote(ids: list[str]) -> dict[str, dict[str, Any]]:
    """BatchGetItem de varios reportes (máx. 100 por llamada)."""
    resultado: dict[str, dict[str, Any]] = {}
    if not ids:
        return resultado
    nombre = tabla().name
    for i in range(0, len(ids), 100):
        claves = [{"PK": f"REP#{x}", "SK": "META"} for x in ids[i:i + 100]]
        pendientes: dict[str, Any] = {nombre: {"Keys": claves}}
        while pendientes:
            r = _recurso.batch_get_item(RequestItems=pendientes)
            for item in r.get("Responses", {}).get(nombre, []):
                resultado[item["id"]] = item
            pendientes = r.get("UnprocessedKeys") or {}
    return resultado


def registrar_estadistica(fecha_dia: str, barrio: str, categoria: str, subtipo: str) -> None:
    """
    Desnormalización controlada: dos contadores atómicos por reporte, uno
    por día (AP16) y otro por zona (AP17), para que cada lectura sea un Query.
    """
    b = slug(barrio)
    valores = {":uno": 1, ":b": barrio, ":c": categoria, ":s": subtipo, ":f": fecha_dia}
    expr = "ADD #total :uno SET barrio = :b, categoria = :c, subtipo = :s, fecha = :f"
    tabla().update_item(
        Key={"PK": f"STAT#DIA#{fecha_dia}", "SK": f"ZONA#{b}#CAT#{categoria}#{subtipo}"},
        UpdateExpression=expr, ExpressionAttributeValues=valores,
        ExpressionAttributeNames={"#total": "total"})
    tabla().update_item(
        Key={"PK": f"STAT#ZONA#{b}", "SK": f"{fecha_dia}#{categoria}#{subtipo}"},
        UpdateExpression=expr, ExpressionAttributeValues=valores,
        ExpressionAttributeNames={"#total": "total"})
