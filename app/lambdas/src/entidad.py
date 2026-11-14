"""
Lambda entidad — panel de las entidades responsables (Alcaldía, servicios públicos, etc.).
Requiere un usuario con rol "entidad"; solo ve las categorías que atiende.

    GET   /entidad/reportes                AP13 pendientes por categoría, urgentes primero  GSI3
    GET   /entidad/reportes/{id}           AP14 detalle completo                            Cache-Aside rep:full:{id}
    PATCH /entidad/reportes/{id}/estado    AP15 cambiar estado                              TransactWriteItems + invalidación
    GET   /entidad/estadisticas            AP16 estadísticas de un día                      Query STAT#DIA#<fecha>
    GET   /entidad/riesgo/{barrio}         AP17 puntos de riesgo de un barrio               Query STAT#ZONA#<barrio>
"""
import logging
from datetime import timedelta
from typing import Any
from urllib.parse import unquote

from boto3.dynamodb.conditions import Key

from comun import cache, db, estados, media, modelo
from comun.http import ErrorApi, despachar, cuerpo_json, query, respuesta, usuario_actual

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ESTADOS_VALIDOS = ("pendiente", "confirmado", "en_atencion", "resuelto")
# Subtipos que alimentan el índice de riesgo (AP17)
SUBTIPOS_INSEGURIDAD = {"robo", "rina_disturbio", "actividad_sospechosa", "zona_oscura"}
SUBTIPOS_ALUMBRADO = {"alumbrado_danado", "sin_luz"}


def _entidad(event: dict[str, Any]) -> dict[str, Any]:
    return usuario_actual(event, rol="entidad")


def _verificar_categoria(entidad: dict[str, Any], categoria: str) -> None:
    if categoria not in entidad.get("categorias_atendidas", []):
        raise ErrorApi(403, f"Tu entidad no atiende la categoría '{categoria}'")


def _fecha(valor: str | None, defecto: str) -> str:
    valor = valor or defecto
    if len(valor) != 10 or valor[4] != "-" or valor[7] != "-":
        raise ErrorApi(400, "Las fechas deben tener formato AAAA-MM-DD")
    return valor


# ── AP13 ─────────────────────────────────────────────────────────────

def pendientes(event: dict[str, Any]) -> dict[str, Any]:
    ent = _entidad(event)
    q = query(event)
    categoria = q.get("categoria") or ent["categorias_atendidas"][0]
    estado = q.get("estado", "pendiente")
    if estado not in ESTADOS_VALIDOS:
        raise ErrorApi(400, f"Estado inválido. Use: {', '.join(ESTADOS_VALIDOS)}")
    _verificar_categoria(ent, categoria)
    # GSI3SK = <urgencia>#<fecha>#<id>: ascendente → urgencia 1 (alta) primero y, dentro, los más antiguos
    r = db.tabla().query(IndexName="GSI3",
                         KeyConditionExpression=Key("GSI3PK").eq(f"CAT#{categoria}#EST#{estado}"),
                         ScanIndexForward=True, Limit=100)
    reportes = [modelo.entidad(i) for i in r.get("Items", [])]
    return respuesta(200, {"categoria": categoria, "estado": estado, "reportes": reportes,
                           "total": len(reportes), "_fuente": "dynamodb"})


# ── AP14 ─────────────────────────────────────────────────────────────

def detalle(event: dict[str, Any]) -> dict[str, Any]:
    ent = _entidad(event)
    rid = event["pathParameters"]["id"]
    en_cache = cache.get_json(cache.k_full(rid))
    if en_cache:
        _verificar_categoria(ent, en_cache["categoria"])
        return respuesta(200, {**en_cache, "_fuente": "cache"})

    meta, eventos, medias = db.obtener_reporte_completo(rid)
    if not meta:
        raise ErrorApi(404, f"Reporte '{rid}' no encontrado")
    _verificar_categoria(ent, meta["categoria"])
    contacto = None
    if meta.get("contacto_autorizado"):
        autor = db.obtener_usuario(meta["autor_id"]) or {}
        contacto = {"nombre": autor.get("nombre"), "telefono": autor.get("telefono"), "email": autor.get("email")}
    datos = {**modelo.entidad(meta, contacto), "historial": [modelo.evento(e) for e in eventos],
             "media": [media.publico(m) for m in medias]}
    cache.set_json(cache.k_full(rid), datos, cache.TTL_ENTIDAD)
    return respuesta(200, {**datos, "_fuente": "dynamodb"})


# ── AP15 ─────────────────────────────────────────────────────────────

def cambiar_estado(event: dict[str, Any]) -> dict[str, Any]:
    ent = _entidad(event)
    rid = event["pathParameters"]["id"]
    datos = cuerpo_json(event)
    nuevo = str(datos.get("estado", ""))
    if nuevo not in ("en_atencion", "resuelto"):
        raise ErrorApi(400, "Una entidad solo puede pasar un reporte a 'en_atencion' o 'resuelto'")
    meta = db.obtener_reporte(rid)
    if not meta:
        raise ErrorApi(404, f"Reporte '{rid}' no encontrado")
    _verificar_categoria(ent, meta["categoria"])
    actualizado = estados.cambiar_estado(meta, nuevo, ent["id"], str(datos.get("nota", ""))[:500])
    return respuesta(200, {"id": rid, "estado": actualizado["estado"],
                           "actualizado_en": actualizado["actualizado_en"]})


# ── AP16 ─────────────────────────────────────────────────────────────

def estadisticas(event: dict[str, Any]) -> dict[str, Any]:
    _entidad(event)
    fecha = _fecha(query(event).get("fecha"), db.ahora().strftime("%Y-%m-%d"))
    items = db.tabla().query(KeyConditionExpression=Key("PK").eq(f"STAT#DIA#{fecha}")).get("Items", [])
    por_barrio: dict[str, int] = {}
    por_categoria: dict[str, int] = {}
    for it in items:
        t = int(it["total"])
        por_barrio[it["barrio"]] = por_barrio.get(it["barrio"], 0) + t
        por_categoria[it["categoria"]] = por_categoria.get(it["categoria"], 0) + t
    detalle_ = [{"barrio": i["barrio"], "categoria": i["categoria"], "subtipo": i["subtipo"],
                 "total": int(i["total"])} for i in items]
    return respuesta(200, {"fecha": fecha, "total": sum(por_barrio.values()),
                           "por_barrio": dict(sorted(por_barrio.items(), key=lambda x: -x[1])),
                           "por_categoria": dict(sorted(por_categoria.items(), key=lambda x: -x[1])),
                           "detalle": detalle_})


# ── AP17 ─────────────────────────────────────────────────────────────

def riesgo(event: dict[str, Any]) -> dict[str, Any]:
    _entidad(event)
    barrio = unquote(event["pathParameters"]["barrio"])
    hoy = db.ahora()
    q = query(event)
    desde = _fecha(q.get("desde"), (hoy - timedelta(days=30)).strftime("%Y-%m-%d"))
    hasta = _fecha(q.get("hasta"), hoy.strftime("%Y-%m-%d"))
    # SK = <fecha>#<cat>#<subtipo> → un rango de fechas es un BETWEEN sobre la sort key
    items = db.tabla().query(
        KeyConditionExpression=Key("PK").eq(f"STAT#ZONA#{db.slug(barrio)}") & Key("SK").between(desde, hasta + "~"),
    ).get("Items", [])
    inseguridad = sum(int(i["total"]) for i in items if i["subtipo"] in SUBTIPOS_INSEGURIDAD)
    alumbrado = sum(int(i["total"]) for i in items if i["subtipo"] in SUBTIPOS_ALUMBRADO)
    por_subtipo: dict[str, int] = {}
    for i in items:
        por_subtipo[i["subtipo"]] = por_subtipo.get(i["subtipo"], 0) + int(i["total"])
    indice = inseguridad + alumbrado
    nivel = "alto" if indice >= 10 else "medio" if indice >= 4 else "bajo"
    hallazgo = None
    if inseguridad and alumbrado:
        hallazgo = ("En este período hay reportes de inseguridad y de alumbrado dañado en el mismo barrio: "
                    "reparar el alumbrado podría reducir los incidentes.")
    return respuesta(200, {"barrio": barrio, "desde": desde, "hasta": hasta,
                           "reportes_inseguridad": inseguridad, "reportes_alumbrado": alumbrado,
                           "indice_riesgo": indice, "nivel": nivel, "hallazgo": hallazgo,
                           "por_subtipo": por_subtipo})


RUTAS = {
    ("GET", "/entidad/reportes"): pendientes,
    ("GET", "/entidad/reportes/{id}"): detalle,
    ("PATCH", "/entidad/reportes/{id}/estado"): cambiar_estado,
    ("GET", "/entidad/estadisticas"): estadisticas,
    ("GET", "/entidad/riesgo/{barrio}"): riesgo,
}


def main(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return despachar(event, RUTAS)
