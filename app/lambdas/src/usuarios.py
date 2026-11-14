"""
Lambda usuarios — registro, perfil y "mis reportes".

    POST /usuarios                AP7  registro con correo único   TransactWriteItems
    GET  /usuarios/{id}           AP8  perfil y nivel de confianza GetItem
    GET  /usuarios/{id}/reportes  AP11 mis reportes                GSI1
"""
import logging
import re
from typing import Any

from decimal import Decimal

from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

from comun import db, modelo
from comun.http import ErrorApi, despachar, cuerpo_json, query, respuesta, usuario_actual

logger = logging.getLogger()
logger.setLevel(logging.INFO)

VERSION_POLITICA = "2026-11"
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
CAMPOS_PUBLICOS = ("id", "nombre", "email", "telefono", "rol", "barrio", "direccion",
                   "confianza", "creado_en", "entidad", "categorias_atendidas")


def _perfil(item: dict[str, Any]) -> dict[str, Any]:
    i = db.desde_dynamo(item)
    return {k: i[k] for k in CAMPOS_PUBLICOS if k in i}


def registrar(event: dict[str, Any]) -> dict[str, Any]:
    datos = cuerpo_json(event)
    nombre = str(datos.get("nombre", "")).strip()
    email = str(datos.get("email", "")).strip().lower()
    if len(nombre) < 3:
        raise ErrorApi(400, "El nombre es obligatorio (mínimo 3 caracteres)")
    if not _EMAIL.match(email):
        raise ErrorApi(400, "Correo electrónico inválido")
    if datos.get("acepta_politica") is not True:
        raise ErrorApi(400, "Debes aceptar la política de tratamiento de datos (Ley 1581 de 2012)")

    uid = db.ulid()
    momento = db.iso(db.ahora())
    usuario = {
        "PK": f"USR#{uid}", "SK": "PERFIL", "tipo": "USUARIO", "id": uid,
        "nombre": nombre[:80], "email": email,
        "telefono": str(datos.get("telefono", "")).strip()[:20],
        "barrio": str(datos.get("barrio", "")).strip()[:60],
        "direccion": str(datos.get("direccion", "")).strip()[:120],
        "rol": "ciudadano", "confianza": Decimal("0.5"), "creado_en": momento,
        "consentimiento": {"fecha": momento, "version": VERSION_POLITICA},
    }
    nombre_tabla = db.tabla().name
    ts = TypeSerializer()
    try:
        # Transacción: perfil + "candado" de correo único. Si el correo ya existe, no se crea nada.
        db.cliente().transact_write_items(TransactItems=[
            {"Put": {"TableName": nombre_tabla,
                     "Item": {k: ts.serialize(v) for k, v in usuario.items()},
                     "ConditionExpression": "attribute_not_exists(PK)"}},
            {"Put": {"TableName": nombre_tabla,
                     "Item": {"PK": {"S": f"EMAIL#{email}"}, "SK": {"S": "USUARIO"},
                              "tipo": {"S": "EMAIL"}, "usuario_id": {"S": uid}},
                     "ConditionExpression": "attribute_not_exists(PK)"}},
        ])
    except ClientError as e:
        if e.response["Error"]["Code"] == "TransactionCanceledException":
            raise ErrorApi(409, "Ya existe una cuenta con ese correo")
        raise
    return respuesta(201, _perfil(usuario))


def _verificar_mismo_usuario(event: dict[str, Any]) -> dict[str, Any]:
    actual = usuario_actual(event)
    if actual["id"] != event["pathParameters"]["id"]:
        raise ErrorApi(403, "Solo puedes consultar tu propia información")
    return actual


def perfil(event: dict[str, Any]) -> dict[str, Any]:
    return respuesta(200, _perfil(_verificar_mismo_usuario(event)))


def mis_reportes(event: dict[str, Any]) -> dict[str, Any]:
    actual = _verificar_mismo_usuario(event)
    try:
        limite = max(1, min(100, int(query(event).get("limite", 20))))
    except ValueError:
        raise ErrorApi(400, "limite debe ser numérico")
    r = db.tabla().query(IndexName="GSI1", KeyConditionExpression=Key("GSI1PK").eq(f"USR#{actual['id']}"),
                         ScanIndexForward=False, Limit=limite)
    reportes = [modelo.propio(i) for i in r.get("Items", [])]
    return respuesta(200, {"reportes": reportes, "total": len(reportes)})


RUTAS = {
    ("POST", "/usuarios"): registrar,
    ("GET", "/usuarios/{id}"): perfil,
    ("GET", "/usuarios/{id}/reportes"): mis_reportes,
}


def main(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return despachar(event, RUTAS)
