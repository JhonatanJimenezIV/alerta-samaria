"""Lambda health — GET /health: verifica DynamoDB y Redis."""
from typing import Any

from comun import cache, db
from comun.http import respuesta


def main(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        db.tabla().get_item(Key={"PK": "CONFIG", "SK": "CATEGORIAS"})
        dynamo = "ok"
    except Exception as e:  # noqa: BLE001
        dynamo = f"error: {e}"
    redis_ok = cache.disponible()
    estado = "ok" if dynamo == "ok" and redis_ok else ("degradado" if dynamo == "ok" else "error")
    return respuesta(200 if dynamo == "ok" else 503, {
        "servicio": "alerta-samaria",
        "estado": estado,
        "dynamodb": dynamo,
        "redis": "ok" if redis_ok else "no disponible (modo degradado)",
        "hora": db.iso(db.ahora()),
    })
