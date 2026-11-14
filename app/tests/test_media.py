"""Fotos y videos (AP21–AP23): URL prefirmada, confirmación, privacidad y feed de videos."""
import boto3
import reportes
from comun import cache
from conftest import crear_ciudadano, crear_reporte, cuerpo, evento


def _pedir(rid, usuario, content_type="video/mp4", tamano=1000):
    return reportes.main(evento("POST", "/reportes/{id}/media", path={"id": rid}, usuario=usuario,
                                body={"content_type": content_type, "tamano": tamano}), None)


def _subir(rid, usuario, content_type="video/mp4", datos=b"x" * 1000):
    pedido = cuerpo(_pedir(rid, usuario, content_type, len(datos)))
    # Simula al navegador: sube el archivo directo a S3 (moto) en la clave reservada
    clave = f"reportes/{rid}/{pedido['id']}.{'mp4' if 'video' in content_type else 'jpg'}"
    boto3.client("s3", region_name="us-east-1").put_object(Bucket="test-media", Key=clave, Body=datos)
    return pedido["id"], reportes.main(evento("POST", "/reportes/{id}/media/{mid}/confirmar",
                                              path={"id": rid, "mid": pedido["id"]}, usuario=usuario), None)


def test_flujo_completo_video(redis_fake, tabla):
    autor = crear_ciudadano()
    rid = crear_reporte(autor, categoria="vias", subtipo="arroyo")["id"]
    pedido = cuerpo(_pedir(rid, autor))
    assert pedido["metodo"] == "PUT" and "test-media" in pedido["url_subida"]

    mid, resp = _subir(rid, autor)
    assert resp["statusCode"] == 200 and cuerpo(resp)["clase"] == "video"
    meta = tabla.get_item(Key={"PK": f"REP#{rid}", "SK": "META"})["Item"]
    assert int(meta["media_count"]) == 1 and meta["tiene_video"] is True
    assert redis_fake.zscore("media:videos", f"{rid}|{mid}") is not None

    detalle = cuerpo(reportes.main(evento("GET", "/reportes/{id}", path={"id": rid}), None))
    assert len(detalle["media"]) == 1 and detalle["media"][0]["url"].startswith("http")

    feed = cuerpo(reportes.main(evento("GET", "/videos"), None))
    assert feed["_fuente"] == "cache" and feed["videos"][0]["rid"] == rid and "url" in feed["videos"][0]


def test_confirmar_sin_subir_falla(redis_fake, tabla):
    autor = crear_ciudadano()
    rid = crear_reporte(autor)["id"]
    mid = cuerpo(_pedir(rid, autor, "image/jpeg"))["id"]
    resp = reportes.main(evento("POST", "/reportes/{id}/media/{mid}/confirmar", path={"id": rid, "mid": mid}, usuario=autor), None)
    assert resp["statusCode"] == 409


def test_validaciones(redis_fake, tabla):
    autor, otro = crear_ciudadano(), crear_ciudadano("Otro Vecino")
    rid = crear_reporte(autor)["id"]
    assert _pedir(rid, otro)["statusCode"] == 403                                  # solo el autor
    assert _pedir(rid, autor, "application/pdf")["statusCode"] == 400              # formato
    assert _pedir(rid, autor, "video/mp4", 80 * 1024 * 1024)["statusCode"] == 400  # tamaño
    seg = crear_reporte(autor, categoria="seguridad", subtipo="robo")["id"]
    assert _pedir(seg, autor, "image/jpeg")["statusCode"] == 400                   # privacidad
    for _ in range(4):
        assert _pedir(rid, autor, "image/jpeg")["statusCode"] == 201
    assert _pedir(rid, autor, "image/jpeg")["statusCode"] == 409                   # máximo 4


def test_videos_sin_redis(tabla):
    import fakeredis
    servidor = fakeredis.FakeServer()
    cache.usar_cliente(fakeredis.FakeRedis(server=servidor, decode_responses=True))
    autor = crear_ciudadano()
    rid = crear_reporte(autor, categoria="emergencias", subtipo="incendio_forestal", barrio="Taganga", lat=11.267, lng=-74.19)["id"]
    _subir(rid, autor)
    servidor.connected = False
    feed = cuerpo(reportes.main(evento("GET", "/videos"), None))
    assert feed["_fuente"] == "dynamodb" and feed["videos"][0]["barrio"] == "Taganga"
    cache.usar_cliente(None)
