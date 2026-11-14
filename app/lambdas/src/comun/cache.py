"""
cache.py — Capa Redis.

Redis NO es la fuente de verdad: todo lo que guarda se puede reconstruir
desde DynamoDB. Si Redis no responde, las funciones devuelven None/False y
la Lambda continúa en modo degradado (solo DynamoDB).

Claves:
    feed:ciudad                 Sorted Set  score = timestamp de creación   (AP1)
    geo:activos                 Geo         coordenadas públicas            (AP2)
    expira:activos              Sorted Set  score = fin de vigencia         (AP1, AP2)
    rep:pub:{id}                String JSON proyección pública  TTL 10 min  (AP3)
    rep:full:{id}               String JSON vista de entidad    TTL 5 min   (AP14)
    conf:{id}                   String      confirmaciones                  (AP10)
    ranking:barrios:{AAAA-Wss}  Sorted Set  reportes por barrio, semana     (AP5)
    cfg:categorias              String JSON catálogo           TTL 24 h     (AP6)
    rl:rep:{usuario}:{hora}     contador    rate limit de reportes          (AP18)
    rl:ip:{ip}:{minuto}         contador    rate limit de lecturas          (AP18)
"""
import json
import logging
import os
from datetime import datetime
from typing import Any

import redis

logger = logging.getLogger(__name__)

TTL_PUBLICO = 600
TTL_ENTIDAD = 300
TTL_CATALOGO = 86400
TTL_RANKING = 14 * 86400

FEED = "feed:ciudad"
GEO = "geo:activos"
EXPIRA = "expira:activos"

_cliente: redis.Redis | None = None


def cliente() -> redis.Redis:
    """
    Cliente reutilizado entre invocaciones (se crea fuera del handler).
    Timeouts cortos: si Redis cae, la Lambda no se queda esperando.
    """
    global _cliente
    if _cliente is None:
        _cliente = redis.Redis(
            host=os.environ.get("REDIS_HOST", "redis"),
            port=int(os.environ.get("REDIS_PORT", 6379)),
            decode_responses=True,
            socket_timeout=0.5,
            socket_connect_timeout=0.5,
        )
    return _cliente


def usar_cliente(c: Any) -> None:
    """Solo para tests: inyecta fakeredis."""
    global _cliente
    _cliente = c


def k_pub(rid: str) -> str:
    return f"rep:pub:{rid}"


def k_full(rid: str) -> str:
    return f"rep:full:{rid}"


def k_conf(rid: str) -> str:
    return f"conf:{rid}"


def k_ranking(dt: datetime) -> str:
    anio, semana, _ = dt.isocalendar()
    return f"ranking:barrios:{anio}-W{semana:02d}"


# ── Operaciones básicas con manejo de errores ────────────────────────

def get_json(clave: str) -> Any | None:
    try:
        valor = cliente().get(clave)
        if valor is None:
            logger.info("CACHE MISS %s", clave)
            return None
        logger.info("CACHE HIT %s", clave)
        return json.loads(valor)
    except redis.RedisError as e:
        logger.warning("Redis no disponible (get %s): %s", clave, e)
        return None


def set_json(clave: str, valor: Any, ttl: int) -> bool:
    try:
        cliente().set(clave, json.dumps(valor, default=str), ex=ttl)
        return True
    except redis.RedisError as e:
        logger.warning("Redis no disponible (set %s): %s", clave, e)
        return False


def mget_json(claves: list[str]) -> list[Any | None] | None:
    """Varios valores en una sola ida a Redis. None si Redis no responde."""
    if not claves:
        return []
    try:
        return [json.loads(v) if v else None for v in cliente().mget(claves)]
    except redis.RedisError as e:
        logger.warning("Redis no disponible (mget): %s", e)
        return None


def borrar(*claves: str) -> bool:
    try:
        cliente().delete(*claves)
        return True
    except redis.RedisError as e:
        logger.warning("Redis no disponible (delete): %s", e)
        return False


def disponible() -> bool:
    try:
        return bool(cliente().ping())
    except redis.RedisError:
        return False


# ── Rate limiting (AP18) ─────────────────────────────────────────────

def excede_limite(clave: str, limite: int, ventana_seg: int) -> bool:
    """INCR + EXPIRE. Si Redis no responde, no se bloquea al usuario."""
    try:
        pipe = cliente().pipeline()
        pipe.incr(clave)
        pipe.expire(clave, ventana_seg, nx=True)
        conteo, _ = pipe.execute()
        return int(conteo) > limite
    except redis.RedisError as e:
        logger.warning("Rate limit omitido, Redis no disponible: %s", e)
        return False


# ── Feed, GEO y ranking ──────────────────────────────────────────────

def publicar_reporte(publico: dict[str, Any], creado_ts: int, expira_ts: int,
                     barrio: str, semana_clave: str, confirmaciones: int = 0) -> bool:
    """
    Write-Through al crear un reporte: feed + GEO + vigencia + ranking +
    proyección pública + contador, en un solo pipeline (una ida a Redis).
    """
    rid = publico["id"]
    try:
        pipe = cliente().pipeline()
        pipe.zadd(FEED, {rid: creado_ts})
        pipe.geoadd(GEO, (publico["lng"], publico["lat"], rid))
        pipe.zadd(EXPIRA, {rid: expira_ts})
        pipe.zincrby(semana_clave, 1, barrio)
        pipe.expire(semana_clave, TTL_RANKING)
        pipe.set(k_pub(rid), json.dumps(publico, default=str), ex=TTL_PUBLICO)
        pipe.set(k_conf(rid), confirmaciones, ex=max(expira_ts - creado_ts, 60))
        pipe.execute()
        return True
    except redis.RedisError as e:
        logger.warning("Write-through omitido, Redis no disponible: %s", e)
        return False


def retirar_reportes(ids: list[str]) -> None:
    """Saca reportes del feed y del índice GEO (resueltos o vencidos)."""
    if not ids:
        return
    try:
        pipe = cliente().pipeline()
        pipe.zrem(FEED, *ids)
        pipe.zrem(GEO, *ids)
        pipe.zrem(EXPIRA, *ids)
        pipe.delete(*[k_conf(x) for x in ids])
        pipe.execute()
    except redis.RedisError as e:
        logger.warning("No se pudieron retirar reportes de Redis: %s", e)


def limpiar_vencidos(ahora_ts: int) -> list[str]:
    """
    Los miembros de un Sorted Set no expiran solos: en cada lectura se retiran
    los reportes cuya vigencia terminó (limpieza perezosa).
    """
    vencidos = cliente().zrangebyscore(EXPIRA, "-inf", ahora_ts)
    if vencidos:
        retirar_reportes(list(vencidos))
        logger.info("Retirados %d reportes vencidos del feed", len(vencidos))
    return list(vencidos)


def ids_feed(limite: int) -> list[str]:
    return list(cliente().zrevrange(FEED, 0, limite - 1))


def ids_cerca(lat: float, lng: float, km: float, limite: int) -> list[tuple[str, float]]:
    resultado = cliente().geosearch(GEO, longitude=lng, latitude=lat, radius=km, unit="km",
                                    withdist=True, sort="ASC", count=limite)
    return [(str(r[0]), float(r[1])) for r in resultado]


def conteos_confirmacion(ids: list[str]) -> dict[str, int]:
    if not ids:
        return {}
    try:
        valores = cliente().mget([k_conf(x) for x in ids])
        return {rid: int(v) for rid, v in zip(ids, valores) if v is not None}
    except redis.RedisError:
        return {}
