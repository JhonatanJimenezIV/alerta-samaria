"""Tests de la Lambda usuarios (AP7, AP8, AP11)."""
import usuarios
from conftest import crear_ciudadano, crear_reporte, cuerpo, evento


def test_registro_exitoso(redis_fake, tabla):
    resp = usuarios.main(evento("POST", "/usuarios", body={
        "nombre": "Carlos Díaz", "email": "Carlos@Correo.com", "acepta_politica": True}), None)
    assert resp["statusCode"] == 201
    datos = cuerpo(resp)
    assert datos["email"] == "carlos@correo.com"
    assert datos["rol"] == "ciudadano"
    # Se guardan el perfil y el candado de correo único
    assert tabla.get_item(Key={"PK": f"USR#{datos['id']}", "SK": "PERFIL"}).get("Item")
    assert tabla.get_item(Key={"PK": "EMAIL#carlos@correo.com", "SK": "USUARIO"}).get("Item")


def test_correo_duplicado_no_crea_nada(redis_fake, tabla):
    crear_ciudadano("Ana Uno", email="ana@correo.com")
    resp = usuarios.main(evento("POST", "/usuarios", body={
        "nombre": "Ana Dos", "email": "ana@correo.com", "acepta_politica": True}), None)
    assert resp["statusCode"] == 409
    perfiles = [i for i in tabla.scan()["Items"] if i["SK"] == "PERFIL"]
    assert len(perfiles) == 1  # la transacción no dejó un perfil huérfano


def test_registro_requiere_consentimiento(redis_fake, tabla):
    resp = usuarios.main(evento("POST", "/usuarios", body={"nombre": "Luis Mora", "email": "luis@correo.com"}), None)
    assert resp["statusCode"] == 400
    assert "1581" in cuerpo(resp)["error"]


def test_perfil_solo_propio(redis_fake, tabla):
    a, b = crear_ciudadano("Ana Pérez"), crear_ciudadano("Beto Ruiz")
    assert usuarios.main(evento("GET", "/usuarios/{id}", path={"id": a}, usuario=a), None)["statusCode"] == 200
    assert usuarios.main(evento("GET", "/usuarios/{id}", path={"id": a}, usuario=b), None)["statusCode"] == 403
    assert usuarios.main(evento("GET", "/usuarios/{id}", path={"id": a}), None)["statusCode"] == 401


def test_mis_reportes_mas_recientes_primero(redis_fake, tabla):
    a = crear_ciudadano()
    r1 = crear_reporte(a)
    r2 = crear_reporte(a, categoria="vias", subtipo="hueco")
    resp = usuarios.main(evento("GET", "/usuarios/{id}/reportes", path={"id": a}, usuario=a), None)
    ids = [r["id"] for r in cuerpo(resp)["reportes"]]
    assert ids == [r2["id"], r1["id"]]
