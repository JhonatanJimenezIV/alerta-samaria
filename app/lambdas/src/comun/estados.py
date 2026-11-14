"""
estados.py — Ciclo de vida de un reporte (AP15 y cambio automático en AP10).

    pendiente ──(3 confirmaciones)──▶ confirmado
    pendiente / confirmado ──(entidad)──▶ en_atencion ──▶ resuelto
    pendiente ──(TTL 48 h sin confirmar)──▶ eliminado por DynamoDB
"""
from typing import Any

from botocore.exceptions import ClientError

from comun import cache, db
from comun.http import ErrorApi

TRANSICIONES: dict[str, set[str]] = {
    "pendiente": {"confirmado", "en_atencion", "resuelto"},
    "confirmado": {"en_atencion", "resuelto"},
    "en_atencion": {"resuelto"},
    "resuelto": set(),
}


def cambiar_estado(meta: dict[str, Any], nuevo: str, actor_id: str, nota: str = "") -> dict[str, Any]:
    """
    Transacción: actualiza META (estado + clave del GSI3) y escribe el evento EVT#.
    La condición `estado = :anterior` evita que dos cambios concurrentes se pisen.
    Después invalida la caché (se prefiere invalidar a actualizar para evitar carreras).
    """
    anterior = meta["estado"]
    if nuevo not in TRANSICIONES.get(anterior, set()):
        raise ErrorApi(409, f"No se puede pasar de '{anterior}' a '{nuevo}'")

    rid = meta["id"]
    momento = db.iso(db.ahora())
    nombre = db.tabla().name
    valores = {
        ":n": {"S": nuevo}, ":anterior": {"S": anterior}, ":t": {"S": momento},
        ":g": {"S": f"CAT#{meta['categoria']}#EST#{nuevo}"},
    }
    expr = "SET estado = :n, GSI3PK = :g, actualizado_en = :t"
    if actor_id != "sistema":  # cambio hecho por una entidad
        expr += ", atendido_por = :a"
        valores[":a"] = {"S": actor_id}
    try:
        db.cliente().transact_write_items(TransactItems=[
            {"Update": {
                "TableName": nombre,
                "Key": {"PK": {"S": f"REP#{rid}"}, "SK": {"S": "META"}},
                "UpdateExpression": expr + " REMOVE #ttl",
                "ConditionExpression": "estado = :anterior",
                "ExpressionAttributeNames": {"#ttl": "ttl"},
                "ExpressionAttributeValues": valores,
            }},
            {"Put": {
                "TableName": nombre,
                "Item": {
                    "PK": {"S": f"REP#{rid}"}, "SK": {"S": f"EVT#{momento}#{nuevo}"},
                    "tipo": {"S": "EVENTO"}, "fecha": {"S": momento},
                    "estado_anterior": {"S": anterior}, "estado_nuevo": {"S": nuevo},
                    "actor_id": {"S": actor_id}, "nota": {"S": nota or ""},
                },
            }},
        ])
    except ClientError as e:
        if e.response["Error"]["Code"] == "TransactionCanceledException":
            raise ErrorApi(409, "El reporte cambió de estado mientras se procesaba; intenta de nuevo")
        raise

    cache.borrar(cache.k_pub(rid), cache.k_full(rid))
    if nuevo == "resuelto":
        cache.retirar_reportes([rid])
    actualizado = {**meta, "estado": nuevo, "actualizado_en": momento}
    if actor_id != "sistema":
        actualizado["atendido_por"] = actor_id
    return actualizado
