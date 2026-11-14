"""
Lambda reportes — endpoints públicos (sin cuenta) y del ciudadano.

    GET  /reportes/feed                  AP1  feed en vivo            Redis ZSET  (respaldo GSI4)
    GET  /reportes/cerca                 AP2  incidentes cercanos     Redis GEO   (respaldo GSI4)
    GET  /reportes/{id}                  AP3  detalle + historial     Cache-Aside rep:pub:{id}
    GET  /barrios/{barrio}/reportes      AP4  reportes de un barrio   GSI2
    GET  /ranking/barrios                AP5  ranking semanal         Redis ZSET  (respaldo STAT#DIA)
    GET  /categorias                     AP6  catálogo                Cache-Aside cfg:categorias
    POST /reportes                       AP9  crear reporte           DynamoDB + Write-Through
    POST /reportes/{id}/confirmaciones   AP10 confirmar               TransactWriteItems + Redis
"""
import logging
import os
from datetime import timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import unquote

import redis
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from comun import cache, catalogo, db, estados, modelo
from comun.http import ErrorApi, despachar, cuerpo_json, ip_origen, query, respuesta, usuario_actual

logger = logging.getLogger()
logger.setLevel(logging.INFO)

ESTADOS_ACTIVOS = {"pendiente", "confirmado", "en_atencion"}


def _entero(valor: str | None, defecto: int, minimo: int, maximo: int) -> int:
    try:
        return max(minimo, min(maximo, int(valor))) if valor is not None else defecto
    except ValueError:
        raise ErrorApi(400, f"Valor numérico inválido: {valor}")


def _limitar_lectura(event: dict[str, Any]) -> None:
    """AP18: lecturas públicas sin cuenta → límite por IP y minuto."""
    limite = int(os.environ.get("RATE_LECTURAS_MINUTO", 120))
    minuto = db.ahora().strftime("%Y%m%d%H%M")
    if cache.excede_limite(f"rl:ip:{ip_origen(event)}:{minuto}", limite, 60):
        raise ErrorApi(429, "Demasiadas consultas; intenta de nuevo en un minuto")


def _hidratar(ids: list[str]) -> list[dict[str, Any]]:
    """
    Convierte ids del feed/GEO en reportes: MGET de rep:pub:* en Redis y,
    para los que falten, un solo BatchGetItem en DynamoDB (que se vuelven a cachear).
    """
    en_cache = cache.mget_json([cache.k_pub(x) for x in ids]) or [None] * len(ids)
    faltantes = [rid for rid, v in zip(ids, en_cache) if v is None]
    desde_db = db.obtener_reportes_lote(faltantes)
    conteos = cache.conteos_confirmacion(ids)
    resultado = []
    for rid, valor in zip(ids, en_cache):
        if valor is None:
            item = desde_db.get(rid)
            if not item:
                continue  # eliminado por TTL; la limpieza lo sacará del feed
            valor = modelo.publico(item)
            cache.set_json(cache.k_pub(rid), valor, cache.TTL_PUBLICO)
        if rid in conteos:
            valor["confirmaciones"] = conteos[rid]
        resultado.append(valor)
    return resultado


def _activos_desde_dynamo(limite: int) -> list[dict[str, Any]]:
    """
    Modo degradado / reconstrucción (AP20): reportes de hoy y de ayer desde GSI4,
    filtrando los resueltos y los que ya terminaron su tiempo activo.
    """
    hoy = db.ahora()
    ahora_iso = db.iso(hoy)
    items: list[dict[str, Any]] = []
    for dias in (0, 1):
        dia = (hoy - timedelta(days=dias)).strftime("%Y-%m-%d")
        r = db.tabla().query(IndexName="GSI4", KeyConditionExpression=Key("GSI4PK").eq(f"FEED#{dia}"),
                             ScanIndexForward=False, Limit=200)
        items.extend(r.get("Items", []))
    activos = [i for i in items if i["estado"] in ESTADOS_ACTIVOS and i.get("activo_hasta", "") > ahora_iso]
    return [modelo.publico(i) for i in activos[:limite]]


# ── AP1 ──────────────────────────────────────────────────────────────

def feed(event: dict[str, Any]) -> dict[str, Any]:
    _limitar_lectura(event)
    q = query(event)
    limite = _entero(q.get("limite"), 50, 1, 200)
    categoria = q.get("categoria")
    try:
        cache.limpiar_vencidos(db.epoch(db.ahora()))
        reportes = _hidratar(cache.ids_feed(limite if not categoria else 200))
        fuente = "cache"
    except redis.RedisError as e:
        logger.warning("Feed en modo degradado: %s", e)
        reportes = _activos_desde_dynamo(200)
        fuente = "dynamodb"
    if categoria:
        reportes = [r for r in reportes if r["categoria"] == categoria or categoria in r.get("tambien_afecta", [])]
    return respuesta(200, {"reportes": reportes[:limite], "total": len(reportes[:limite]), "_fuente": fuente})


# ── AP2 ──────────────────────────────────────────────────────────────

def cerca(event: dict[str, Any]) -> dict[str, Any]:
    _limitar_lectura(event)
    q = query(event)
    try:
        lat, lng = float(q["lat"]), float(q["lng"])
    except (KeyError, ValueError):
        raise ErrorApi(400, "Se requieren los parámetros numéricos lat y lng")
    km = min(max(float(q.get("km", 1)), 0.1), 20)
    limite = _entero(q.get("limite"), 50, 1, 200)
    try:
        cache.limpiar_vencidos(db.epoch(db.ahora()))
        cercanos = cache.ids_cerca(lat, lng, km, limite)
        distancias = dict(cercanos)
        reportes = _hidratar([rid for rid, _ in cercanos])
        fuente = "cache"
    except redis.RedisError as e:
        logger.warning("Cercanía en modo degradado: %s", e)
        reportes = []
        distancias = {}
        for r in _activos_desde_dynamo(500):
            d = modelo.haversine_km(lat, lng, r["lat"], r["lng"])
            if d <= km:
                reportes.append(r)
                distancias[r["id"]] = d
        reportes.sort(key=lambda r: distancias[r["id"]])
        reportes = reportes[:limite]
        fuente = "dynamodb"
    for r in reportes:
        r["distancia_km"] = round(distancias.get(r["id"], 0), 3)
    return respuesta(200, {"reportes": reportes, "total": len(reportes), "radio_km": km, "_fuente": fuente})


# ── AP3 + AP12 ───────────────────────────────────────────────────────

def detalle(event: dict[str, Any]) -> dict[str, Any]:
    _limitar_lectura(event)
    rid = event["pathParameters"]["id"]
    en_cache = cache.get_json(cache.k_pub(rid))
    if en_cache and "historial" in en_cache:
        conteo = cache.conteos_confirmacion([rid]).get(rid)
        if conteo is not None:
            en_cache["confirmaciones"] = conteo
        return respuesta(200, {**en_cache, "_fuente": "cache"})

    meta, eventos = db.obtener_reporte_completo(rid)
    if not meta:
        raise ErrorApi(404, f"Reporte '{rid}' no encontrado")
    datos = {**modelo.publico(meta), "historial": [modelo.evento(e) for e in eventos]}
    cache.set_json(cache.k_pub(rid), datos, cache.TTL_PUBLICO)
    return respuesta(200, {**datos, "_fuente": "dynamodb"})


# ── AP4 ──────────────────────────────────────────────────────────────

def por_barrio(event: dict[str, Any]) -> dict[str, Any]:
    _limitar_lectura(event)
    barrio = unquote(event["pathParameters"]["barrio"])
    limite = _entero(query(event).get("limite"), 20, 1, 100)
    r = db.tabla().query(IndexName="GSI2", KeyConditionExpression=Key("GSI2PK").eq(f"ZONA#{db.slug(barrio)}"),
                         ScanIndexForward=False, Limit=limite)
    reportes = [modelo.publico(i) for i in r.get("Items", [])]
    return respuesta(200, {"barrio": barrio, "reportes": reportes, "total": len(reportes), "_fuente": "dynamodb"})


# ── AP5 ──────────────────────────────────────────────────────────────

def ranking(event: dict[str, Any]) -> dict[str, Any]:
    _limitar_lectura(event)
    hoy = db.ahora()
    clave = cache.k_ranking(hoy)
    try:
        filas = cache.cliente().zrevrange(clave, 0, 9, withscores=True)
        datos = [{"barrio": b, "total": int(t)} for b, t in filas]
        fuente = "cache"
    except redis.RedisError:
        # Respaldo: suma las estadísticas diarias de la semana ISO actual
        totales: dict[str, int] = {}
        lunes = hoy - timedelta(days=hoy.weekday())
        for d in range((hoy - lunes).days + 1):
            dia = (lunes + timedelta(days=d)).strftime("%Y-%m-%d")
            for it in db.tabla().query(KeyConditionExpression=Key("PK").eq(f"STAT#DIA#{dia}")).get("Items", []):
                totales[it["barrio"]] = totales.get(it["barrio"], 0) + int(it["total"])
        datos = [{"barrio": b, "total": t} for b, t in sorted(totales.items(), key=lambda x: -x[1])[:10]]
        fuente = "dynamodb"
    return respuesta(200, {"semana": clave.split(":")[-1], "ranking": datos, "_fuente": fuente})


# ── AP6 ──────────────────────────────────────────────────────────────

def categorias(event: dict[str, Any]) -> dict[str, Any]:
    datos, fuente = catalogo.obtener()
    return respuesta(200, {**datos, "_fuente": fuente})


# ── AP9 ──────────────────────────────────────────────────────────────

def _numero(datos: dict[str, Any], campo: str) -> Decimal:
    try:
        return db.a_decimal(datos[campo])
    except (KeyError, ArithmeticError, ValueError):
        raise ErrorApi(400, f"El campo '{campo}' es obligatorio y debe ser numérico")


def crear(event: dict[str, Any]) -> dict[str, Any]:
    usuario = usuario_actual(event)
    datos = cuerpo_json(event)

    # Rate limiting por usuario y hora
    limite = int(os.environ.get("RATE_REPORTES_HORA", 5))
    hora = db.ahora().strftime("%Y%m%d%H")
    if cache.excede_limite(f"rl:rep:{usuario['id']}:{hora}", limite, 3600):
        raise ErrorApi(429, f"Máximo {limite} reportes por hora")

    # Validaciones
    encontrado = catalogo.buscar(str(datos.get("categoria", "")), str(datos.get("subtipo", "")))
    if not encontrado:
        raise ErrorApi(400, "Categoría o subtipo inválido (consulta GET /categorias)")
    cat, sub = encontrado
    lat, lng = _numero(datos, "lat"), _numero(datos, "lng")
    if not modelo.dentro_de_santa_marta(float(lat), float(lng)):
        raise ErrorApi(400, "La ubicación está fuera del distrito de Santa Marta")
    barrio = str(datos.get("barrio", "")).strip()
    if not barrio:
        raise ErrorApi(400, "El campo 'barrio' es obligatorio")
    descripcion = str(datos.get("descripcion", "")).strip()[:1000]
    if cat["id"] == "otro" and len(descripcion) < 10:
        raise ErrorApi(400, "Para la categoría 'Otro' describe el incidente (mínimo 10 caracteres)")

    # Confianza: ¿el reportante estaba cerca del incidente?
    confianza = "normal"
    ubic_rep = datos.get("ubic_reportante")
    if isinstance(ubic_rep, dict) and "lat" in ubic_rep and "lng" in ubic_rep:
        distancia = modelo.haversine_km(float(lat), float(lng), float(ubic_rep["lat"]), float(ubic_rep["lng"]))
        confianza = "baja" if distancia > 20 else "normal"
        ubic_rep = {"lat": db.a_decimal(ubic_rep["lat"]), "lng": db.a_decimal(ubic_rep["lng"])}
    else:
        ubic_rep = None

    aproximada = bool(cat.get("ubicacion_aproximada"))
    lat_pub = db.a_decimal(modelo.aproximar(float(lat))) if aproximada else lat
    lng_pub = db.a_decimal(modelo.aproximar(float(lng))) if aproximada else lng

    momento = db.ahora()
    creado = db.iso(momento)
    activo_hasta = momento + timedelta(hours=int(sub["horas"]))
    rid = db.ulid()
    afecta = datos.get("tambien_afecta") or sub.get("tambien_afecta", [])
    afecta = [a for a in afecta if isinstance(a, str) and a != cat["id"]][:3]

    item: dict[str, Any] = {
        "PK": f"REP#{rid}", "SK": "META", "tipo": "REPORTE", "id": rid,
        "categoria": cat["id"], "categoria_nombre": cat["nombre"],
        "subtipo": sub["id"], "subtipo_nombre": sub["nombre"],
        "urgencia": int(sub["urgencia"]), "tambien_afecta": afecta,
        "aviso_123": bool(cat.get("aviso_123")),
        "titulo": str(datos.get("titulo") or sub["nombre"]).strip()[:120],
        "descripcion": descripcion,
        "estado": "pendiente",
        "lat": lat, "lng": lng, "lat_pub": lat_pub, "lng_pub": lng_pub,
        "ubicacion_aproximada": aproximada,
        "direccion": str(datos.get("direccion", "")).strip()[:200],
        "referencia": str(datos.get("referencia", "")).strip()[:200],
        "barrio": barrio, "comuna": str(datos.get("comuna", "")).strip(),
        "autor_id": usuario["id"], "anonimo": bool(datos.get("anonimo", False)),
        "contacto_autorizado": bool(datos.get("contacto_autorizado", False)),
        "confianza_reporte": confianza,
        "confirmaciones": 0,
        "creado_en": creado, "actualizado_en": creado, "activo_hasta": db.iso(activo_hasta),
        "ttl": db.epoch(momento + timedelta(hours=48)),  # AP19: se borra si nadie lo confirma
        # Índices secundarios
        "GSI1PK": f"USR#{usuario['id']}", "GSI1SK": f"{creado}#{rid}",
        "GSI2PK": f"ZONA#{db.slug(barrio)}", "GSI2SK": f"{creado}#{rid}",
        "GSI3PK": f"CAT#{cat['id']}#EST#pendiente", "GSI3SK": f"{int(sub['urgencia'])}#{creado}#{rid}",
        "GSI4PK": f"FEED#{momento.strftime('%Y-%m-%d')}", "GSI4SK": f"{creado}#{rid}",
    }
    if ubic_rep:
        item["ubic_reportante"] = ubic_rep

    # 1. DynamoDB (fuente de verdad): reporte + evento de creación + estadísticas
    with db.tabla().batch_writer() as lote:
        lote.put_item(Item=item)
        lote.put_item(Item={"PK": f"REP#{rid}", "SK": f"EVT#{creado}#pendiente", "tipo": "EVENTO",
                            "fecha": creado, "estado_nuevo": "pendiente", "actor_id": usuario["id"]})
    db.registrar_estadistica(momento.strftime("%Y-%m-%d"), barrio, cat["id"], sub["id"])

    # 2. Write-Through: aparece de inmediato en el feed, el mapa y el ranking
    publico = modelo.publico(item)
    cache.publicar_reporte(publico, db.epoch(momento), db.epoch(activo_hasta), barrio, cache.k_ranking(momento))

    return respuesta(201, {**modelo.propio(item), "aviso": "Si hay riesgo para la vida, llama al 123" if item["aviso_123"] else None})


# ── AP10 ─────────────────────────────────────────────────────────────

def confirmar(event: dict[str, Any]) -> dict[str, Any]:
    usuario = usuario_actual(event)
    rid = event["pathParameters"]["id"]
    meta = db.obtener_reporte(rid)
    if not meta:
        raise ErrorApi(404, f"Reporte '{rid}' no encontrado")
    if meta["autor_id"] == usuario["id"]:
        raise ErrorApi(400, "No puedes confirmar tu propio reporte")
    if meta["estado"] not in ESTADOS_ACTIVOS:
        raise ErrorApi(409, "El reporte ya fue resuelto")

    nombre = db.tabla().name
    momento = db.iso(db.ahora())
    try:
        # Transacción: un voto por usuario (Put condicional) + contador atómico.
        # REMOVE ttl: un reporte confirmado ya no se borra a las 48 h.
        db.cliente().transact_write_items(TransactItems=[
            {"Put": {
                "TableName": nombre,
                "Item": {"PK": {"S": f"REP#{rid}"}, "SK": {"S": f"CONF#{usuario['id']}"},
                         "tipo": {"S": "CONFIRMACION"}, "creado_en": {"S": momento}},
                "ConditionExpression": "attribute_not_exists(PK)",
            }},
            {"Update": {
                "TableName": nombre,
                "Key": {"PK": {"S": f"REP#{rid}"}, "SK": {"S": "META"}},
                "UpdateExpression": "ADD confirmaciones :uno REMOVE #ttl",
                "ConditionExpression": "attribute_exists(PK)",
                "ExpressionAttributeNames": {"#ttl": "ttl"},
                "ExpressionAttributeValues": {":uno": {"N": "1"}},
            }},
        ])
    except ClientError as e:
        if e.response["Error"]["Code"] == "TransactionCanceledException":
            razones = e.response.get("CancellationReasons") or []
            if razones and razones[0].get("Code") == "ConditionalCheckFailed":
                raise ErrorApi(409, "Ya confirmaste este reporte")
            raise ErrorApi(409, "No se pudo registrar la confirmación")
        raise

    meta = db.obtener_reporte(rid)  # valor oficial del contador
    total = int(meta["confirmaciones"])
    requeridas = int(os.environ.get("CONFIRMACIONES_REQUERIDAS", 3))
    if meta["estado"] == "pendiente" and total >= requeridas:
        try:
            meta = estados.cambiar_estado(meta, "confirmado", "sistema",
                                          f"{total} usuarios confirmaron el reporte")
        except ErrorApi:
            pass  # otro cambio concurrente ya lo movió de estado
    try:
        cache.cliente().set(cache.k_conf(rid), total, keepttl=True)
    except redis.RedisError:
        pass
    cache.borrar(cache.k_full(rid))
    return respuesta(201, {"id": rid, "confirmaciones": total, "estado": meta["estado"]})


RUTAS = {
    ("GET", "/reportes/feed"): feed,
    ("GET", "/reportes/cerca"): cerca,
    ("GET", "/reportes/{id}"): detalle,
    ("GET", "/barrios/{barrio}/reportes"): por_barrio,
    ("GET", "/ranking/barrios"): ranking,
    ("GET", "/categorias"): categorias,
    ("POST", "/reportes"): crear,
    ("POST", "/reportes/{id}/confirmaciones"): confirmar,
}


def main(event: dict[str, Any], context: Any) -> dict[str, Any]:
    return despachar(event, RUTAS)
