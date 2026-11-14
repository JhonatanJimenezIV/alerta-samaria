"""Tests de la Lambda reportes (AP1–AP6, AP9, AP10, AP18, AP19)."""
import reportes
from comun import cache
from conftest import REPORTE_BASE, crear_ciudadano, crear_reporte, cuerpo, evento


def test_crear_reporte_write_through(redis_fake, tabla):
    autor = crear_ciudadano()
    rep = crear_reporte(autor)
    rid = rep["id"]
    item = tabla.get_item(Key={"PK": f"REP#{rid}", "SK": "META"})["Item"]
    assert item["estado"] == "pendiente"
    assert item["tambien_afecta"] == ["vias"]           # tubería rota también afecta Vías
    assert item["GSI3PK"] == "CAT#servicios#EST#pendiente"
    assert "ttl" in item                                # AP19: se borra a las 48 h si nadie confirma
    # Write-Through: ya está en el feed, en el índice GEO, en el ranking y cacheado
    assert redis_fake.zscore(cache.FEED, rid) is not None
    assert redis_fake.geopos(cache.GEO, rid)[0] is not None
    assert redis_fake.exists(cache.k_pub(rid))
    assert any(b == "Gaira" for b, _ in redis_fake.zrevrange(cache.k_ranking(__import__("comun.db").db.ahora()), 0, -1, withscores=True))
    # Estadísticas desnormalizadas (por día y por zona)
    stats = [i for i in tabla.scan()["Items"] if i["PK"].startswith("STAT#")]
    assert len(stats) == 2 and all(int(s["total"]) == 1 for s in stats)


def test_validaciones_de_creacion(redis_fake, tabla):
    autor = crear_ciudadano()
    malos = [
        {**REPORTE_BASE, "subtipo": "no_existe"},
        {**REPORTE_BASE, "lat": 4.6, "lng": -74.08},     # Bogotá: fuera de Santa Marta
        {**REPORTE_BASE, "barrio": ""},
        {**REPORTE_BASE, "categoria": "otro", "subtipo": "otro", "descripcion": "corto"},
    ]
    for body in malos:
        assert reportes.main(evento("POST", "/reportes", body=body, usuario=autor), None)["statusCode"] == 400
    assert reportes.main(evento("POST", "/reportes", body=REPORTE_BASE), None)["statusCode"] == 401


def test_rate_limit_por_usuario(redis_fake, tabla):
    autor = crear_ciudadano()
    for _ in range(5):
        crear_reporte(autor)
    resp = reportes.main(evento("POST", "/reportes", body=REPORTE_BASE, usuario=autor), None)
    assert resp["statusCode"] == 429


def test_seguridad_ubicacion_aproximada_y_sin_direccion(redis_fake, tabla):
    autor = crear_ciudadano()
    rep = crear_reporte(autor, categoria="seguridad", subtipo="robo", lat=11.242137, lng=-74.211093,
                        barrio="Centro Histórico")
    resp = reportes.main(evento("GET", "/reportes/{id}", path={"id": rep["id"]}), None)
    pub = cuerpo(resp)
    assert pub["ubicacion_aproximada"] is True
    assert (pub["lat"], pub["lng"]) != (11.242137, -74.211093)
    assert "direccion" not in pub and "referencia" not in pub
    assert pub["autor"] == "Usuario verificado"
    assert pub["aviso_123"] is True


def test_detalle_cache_aside(redis_fake, tabla):
    autor = crear_ciudadano()
    rid = crear_reporte(autor)["id"]
    redis_fake.delete(cache.k_pub(rid))  # forzamos un miss
    r1 = cuerpo(reportes.main(evento("GET", "/reportes/{id}", path={"id": rid}), None))
    r2 = cuerpo(reportes.main(evento("GET", "/reportes/{id}", path={"id": rid}), None))
    assert r1["_fuente"] == "dynamodb" and r2["_fuente"] == "cache"
    assert r1["historial"][0]["estado_nuevo"] == "pendiente"
    assert reportes.main(evento("GET", "/reportes/{id}", path={"id": "NOEXISTE"}), None)["statusCode"] == 404


def test_feed_y_filtro_por_categoria(redis_fake, tabla):
    autor = crear_ciudadano()
    a = crear_reporte(autor)                                          # servicios (afecta vías)
    b = crear_reporte(autor, categoria="transito", subtipo="semaforo_danado")
    feed = cuerpo(reportes.main(evento("GET", "/reportes/feed"), None))
    assert feed["_fuente"] == "cache"
    assert [r["id"] for r in feed["reportes"]] == [b["id"], a["id"]]
    vias = cuerpo(reportes.main(evento("GET", "/reportes/feed", qs={"categoria": "vias"}), None))
    assert [r["id"] for r in vias["reportes"]] == [a["id"]]          # aparece por "también afecta"


def test_feed_retira_vencidos(redis_fake, tabla):
    autor = crear_ciudadano()
    rid = crear_reporte(autor)["id"]
    redis_fake.zadd(cache.EXPIRA, {rid: 1})  # simulamos que su vigencia terminó
    feed = cuerpo(reportes.main(evento("GET", "/reportes/feed"), None))
    assert feed["total"] == 0
    assert redis_fake.zscore(cache.FEED, rid) is None


def test_cerca_con_geo(redis_fake, tabla):
    autor = crear_ciudadano()
    gaira = crear_reporte(autor)                                                       # Gaira
    taganga = crear_reporte(autor, lat=11.2670, lng=-74.1900, barrio="Taganga")        # ~9 km
    resp = cuerpo(reportes.main(evento("GET", "/reportes/cerca",
                                       qs={"lat": "11.1935", "lng": "-74.2245", "km": "2"}), None))
    ids = [r["id"] for r in resp["reportes"]]
    assert gaira["id"] in ids and taganga["id"] not in ids
    assert resp["reportes"][0]["distancia_km"] < 1


def test_por_barrio_gsi2(redis_fake, tabla):
    autor = crear_ciudadano()
    crear_reporte(autor, barrio="El Rodadero", lat=11.2050, lng=-74.2270)
    crear_reporte(autor)  # Gaira
    resp = cuerpo(reportes.main(evento("GET", "/barrios/{barrio}/reportes", path={"barrio": "el%20rodadero"}), None))
    assert resp["total"] == 1 and resp["reportes"][0]["barrio"] == "El Rodadero"


def test_confirmaciones(redis_fake, tabla):
    autor = crear_ciudadano("Autor Uno")
    rid = crear_reporte(autor)["id"]
    v1, v2, v3 = (crear_ciudadano(f"Vecino {n}") for n in ("Uno", "Dos", "Tres"))

    def confirmar(u):
        return reportes.main(evento("POST", "/reportes/{id}/confirmaciones", path={"id": rid}, usuario=u), None)

    assert confirmar(autor)["statusCode"] == 400            # no puede confirmar el propio
    assert confirmar(v1)["statusCode"] == 201
    assert confirmar(v1)["statusCode"] == 409               # un voto por usuario
    item = tabla.get_item(Key={"PK": f"REP#{rid}", "SK": "META"})["Item"]
    assert "ttl" not in item                                # confirmado una vez: ya no se borra
    confirmar(v2)
    final = cuerpo(confirmar(v3))
    assert final == {"id": rid, "confirmaciones": 3, "estado": "confirmado"}
    item = tabla.get_item(Key={"PK": f"REP#{rid}", "SK": "META"})["Item"]
    assert item["GSI3PK"] == "CAT#servicios#EST#confirmado"
    assert redis_fake.get(cache.k_conf(rid)) == "3"


def test_categorias_cache_aside(redis_fake, tabla):
    r1 = cuerpo(reportes.main(evento("GET", "/categorias"), None))
    r2 = cuerpo(reportes.main(evento("GET", "/categorias"), None))
    assert len(r1["categorias"]) == 9
    assert r1["_fuente"] == "inicial" and r2["_fuente"] == "cache"


def test_ranking_semanal(redis_fake, tabla):
    autor, otro = crear_ciudadano(), crear_ciudadano("Otro Vecino")
    crear_reporte(autor)
    crear_reporte(autor)
    crear_reporte(otro, barrio="Taganga", lat=11.2670, lng=-74.1900)
    datos = cuerpo(reportes.main(evento("GET", "/ranking/barrios"), None))
    assert datos["ranking"][0] == {"barrio": "Gaira", "total": 2}
