"""
modelo.py — Proyecciones de un reporte según quién lo consulta (privacidad por niveles)
y utilidades geográficas.

    publico  → sin datos del reportante; ubicación aproximada (~150 m) en Seguridad,
               sin dirección exacta ni referencia en Seguridad.
    propio   → lo que ve el autor en "mis reportes".
    entidad  → ubicación exacta, dirección, referencia y contacto solo si fue autorizado.
"""
import math
from typing import Any

from comun import db

# Límites aproximados del distrito de Santa Marta (incluye zona rural y Sierra)
LAT_MIN, LAT_MAX = 10.80, 11.40
LNG_MIN, LNG_MAX = -74.30, -73.50

PASO_APROX = 0.0015  # ≈ 150 m


def aproximar(valor: float) -> float:
    return round(round(valor / PASO_APROX) * PASO_APROX, 6)


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def dentro_de_santa_marta(lat: float, lng: float) -> bool:
    return LAT_MIN <= lat <= LAT_MAX and LNG_MIN <= lng <= LNG_MAX


def _base(item: dict[str, Any]) -> dict[str, Any]:
    i = db.desde_dynamo(item)
    return {
        "id": i["id"],
        "categoria": i["categoria"],
        "categoria_nombre": i.get("categoria_nombre"),
        "subtipo": i["subtipo"],
        "subtipo_nombre": i.get("subtipo_nombre"),
        "urgencia": i["urgencia"],
        "tambien_afecta": i.get("tambien_afecta", []),
        "titulo": i.get("titulo", ""),
        "descripcion": i.get("descripcion", ""),
        "estado": i["estado"],
        "barrio": i["barrio"],
        "comuna": i.get("comuna", ""),
        "confirmaciones": i.get("confirmaciones", 0),
        "creado_en": i["creado_en"],
        "actualizado_en": i.get("actualizado_en", i["creado_en"]),
        "activo_hasta": i.get("activo_hasta"),
        "aviso_123": i.get("aviso_123", False),
        "media_count": i.get("media_count", 0),
        "tiene_video": i.get("tiene_video", False),
    }


def publico(item: dict[str, Any]) -> dict[str, Any]:
    i = db.desde_dynamo(item)
    p = _base(i)
    p["lat"], p["lng"] = i["lat_pub"], i["lng_pub"]
    p["ubicacion_aproximada"] = i.get("ubicacion_aproximada", False)
    if not p["ubicacion_aproximada"]:
        p["direccion"] = i.get("direccion", "")
        p["referencia"] = i.get("referencia", "")
    p["autor"] = "Anónimo" if i.get("anonimo") else "Usuario verificado"
    return p


def propio(item: dict[str, Any]) -> dict[str, Any]:
    i = db.desde_dynamo(item)
    p = _base(i)
    p.update(lat=i["lat"], lng=i["lng"], direccion=i.get("direccion", ""),
             referencia=i.get("referencia", ""), anonimo=i.get("anonimo", False))
    return p


def entidad(item: dict[str, Any], contacto: dict[str, Any] | None = None) -> dict[str, Any]:
    i = db.desde_dynamo(item)
    p = propio(i)
    p["confianza_reporte"] = i.get("confianza_reporte", "normal")
    p["atendido_por"] = i.get("atendido_por")
    p["contacto"] = contacto if i.get("contacto_autorizado") else None
    return p


def evento(item: dict[str, Any]) -> dict[str, Any]:
    i = db.desde_dynamo(item)
    return {"fecha": i["fecha"], "estado_anterior": i.get("estado_anterior"),
            "estado_nuevo": i["estado_nuevo"], "nota": i.get("nota", "")}
