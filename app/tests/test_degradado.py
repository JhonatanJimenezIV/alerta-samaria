"""Modo degradado: si Redis no responde, la API sigue funcionando solo con DynamoDB."""
import reportes
from comun import cache
from conftest import crear_ciudadano, crear_reporte, cuerpo, evento


def test_api_funciona_sin_redis(tabla):
    import fakeredis
    servidor = fakeredis.FakeServer()
    cache.usar_cliente(fakeredis.FakeRedis(server=servidor, decode_responses=True))
    autor = crear_ciudadano()
    rid = crear_reporte(autor)["id"]
    crear_reporte(autor, barrio="Taganga", lat=11.2670, lng=-74.1900)

    servidor.connected = False  # Redis "se cae"

    feed = cuerpo(reportes.main(evento("GET", "/reportes/feed"), None))
    assert feed["_fuente"] == "dynamodb" and feed["total"] == 2           # respaldo GSI4

    cerca = cuerpo(reportes.main(evento("GET", "/reportes/cerca",
                                        qs={"lat": "11.1935", "lng": "-74.2245", "km": "2"}), None))
    assert cerca["_fuente"] == "dynamodb" and [r["id"] for r in cerca["reportes"]] == [rid]

    detalle = cuerpo(reportes.main(evento("GET", "/reportes/{id}", path={"id": rid}), None))
    assert detalle["_fuente"] == "dynamodb"

    ranking = cuerpo(reportes.main(evento("GET", "/ranking/barrios"), None))
    assert ranking["_fuente"] == "dynamodb" and ranking["ranking"][0]["total"] == 1

    # Crear reportes también funciona (se omite el write-through y el rate limit)
    crear_reporte(autor, categoria="vias", subtipo="hueco")
    cache.usar_cliente(None)


def test_health_degradado(redis_caido):
    import health
    datos = cuerpo(health.main({}, None))
    assert datos["dynamodb"] == "ok" and datos["estado"] == "degradado"
