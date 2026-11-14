"""Tests de la Lambda entidad (AP13–AP17)."""
import entidad
import reportes
from comun import cache
from conftest import crear_ciudadano, crear_entidad, crear_reporte, cuerpo, evento


def test_pendientes_urgentes_primero(redis_fake, tabla):
    ent = crear_entidad(["vias"])
    autor = crear_ciudadano()
    hueco = crear_reporte(autor, categoria="vias", subtipo="hueco")              # urgencia 2
    inundada = crear_reporte(autor, categoria="vias", subtipo="calle_inundada")  # urgencia 1
    datos = cuerpo(entidad.main(evento("GET", "/entidad/reportes", usuario=ent, qs={"categoria": "vias"}), None))
    assert [r["id"] for r in datos["reportes"]] == [inundada["id"], hueco["id"]]


def test_solo_categorias_atendidas(redis_fake, tabla):
    ent = crear_entidad(["vias"])
    autor = crear_ciudadano()
    rid = crear_reporte(autor)["id"]  # servicios
    assert entidad.main(evento("GET", "/entidad/reportes", usuario=ent,
                               qs={"categoria": "servicios"}), None)["statusCode"] == 403
    assert entidad.main(evento("GET", "/entidad/reportes/{id}", path={"id": rid}, usuario=ent), None)["statusCode"] == 403
    assert entidad.main(evento("GET", "/entidad/reportes", usuario=autor), None)["statusCode"] == 403  # ciudadano


def test_detalle_con_contacto_solo_si_autorizado(redis_fake, tabla):
    ent = crear_entidad(["servicios"])
    autor = crear_ciudadano()
    con = crear_reporte(autor, contacto_autorizado=True)["id"]
    sin = crear_reporte(autor)["id"]
    d1 = cuerpo(entidad.main(evento("GET", "/entidad/reportes/{id}", path={"id": con}, usuario=ent), None))
    d2 = cuerpo(entidad.main(evento("GET", "/entidad/reportes/{id}", path={"id": sin}, usuario=ent), None))
    assert d1["contacto"]["telefono"] == "3001234567" and d2["contacto"] is None
    assert d1["direccion"] == "Cra 4 #22-10" and d1["_fuente"] == "dynamodb"
    d1b = cuerpo(entidad.main(evento("GET", "/entidad/reportes/{id}", path={"id": con}, usuario=ent), None))
    assert d1b["_fuente"] == "cache"


def test_cambio_estado_invalida_cache_y_retira_del_feed(redis_fake, tabla):
    ent = crear_entidad(["servicios"])
    autor = crear_ciudadano()
    rid = crear_reporte(autor)["id"]
    reportes.main(evento("GET", "/reportes/{id}", path={"id": rid}), None)  # queda en caché

    def cambiar(estado):
        return entidad.main(evento("PATCH", "/entidad/reportes/{id}/estado", path={"id": rid},
                                   usuario=ent, body={"estado": estado, "nota": "Cuadrilla asignada"}), None)

    assert cambiar("en_atencion")["statusCode"] == 200
    assert not redis_fake.exists(cache.k_pub(rid))                  # invalidada
    pub = cuerpo(reportes.main(evento("GET", "/reportes/{id}", path={"id": rid}), None))
    assert pub["estado"] == "en_atencion" and pub["_fuente"] == "dynamodb"
    assert [h["estado_nuevo"] for h in pub["historial"]] == ["pendiente", "en_atencion"]

    assert cambiar("resuelto")["statusCode"] == 200
    assert redis_fake.zscore(cache.FEED, rid) is None               # sale del feed y del mapa
    assert cambiar("en_atencion")["statusCode"] == 400 or cambiar("en_atencion")["statusCode"] == 409
    item = tabla.get_item(Key={"PK": f"REP#{rid}", "SK": "META"})["Item"]
    assert item["GSI3PK"] == "CAT#servicios#EST#resuelto" and item["atendido_por"] == ent


def test_estadisticas_y_riesgo(redis_fake, tabla):
    ent = crear_entidad(["seguridad", "servicios"])
    a, b = crear_ciudadano("Ana Pérez"), crear_ciudadano("Beto Ruiz")
    for u in (a, b):
        crear_reporte(u, categoria="seguridad", subtipo="robo", barrio="Bastidas", lat=11.253, lng=-74.198)
    crear_reporte(a, categoria="servicios", subtipo="alumbrado_danado", barrio="Bastidas", lat=11.253, lng=-74.198)
    crear_reporte(b)  # Gaira

    stats = cuerpo(entidad.main(evento("GET", "/entidad/estadisticas", usuario=ent), None))
    assert stats["total"] == 4 and stats["por_barrio"]["Bastidas"] == 3

    riesgo = cuerpo(entidad.main(evento("GET", "/entidad/riesgo/{barrio}", path={"barrio": "Bastidas"}, usuario=ent), None))
    assert riesgo["reportes_inseguridad"] == 2 and riesgo["reportes_alumbrado"] == 1
    assert riesgo["hallazgo"] is not None
    assert entidad.main(evento("GET", "/entidad/estadisticas", usuario=ent,
                               qs={"fecha": "13-11-2026"}), None)["statusCode"] == 400
