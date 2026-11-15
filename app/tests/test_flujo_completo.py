"""
test_flujo_completo.py — Pruebas de integración de flujo completo.

Simula el recorrido real de un usuario:
  1. Registro de cuenta (ciudadano)
  2. Consulta de perfil (equivale a "iniciar sesión")
  3. Creación de un reporte con ubicación GPS
  4. Solicitud de URL prefirmada para subir video
  5. Subida del video a S3 (simulada)
  6. Confirmación del video
  7. Visualización del video en el feed público
  8. Registro de un segundo usuario que confirma el reporte
  9. Verificación de que el reporte se ve en "mis reportes"
"""
import boto3
import reportes
import usuarios
from comun import cache
from conftest import cuerpo, evento


# ── 1. FLUJO COMPLETO: REGISTRO → SESIÓN → REPORTE → VIDEO ─────────

def test_flujo_registro_a_video(redis_fake, tabla):
    """Un ciudadano se registra, crea un reporte, sube un video y lo ve en el feed."""

    # ── Paso 1: Registro ──────────────────────────────────────────────
    resp = usuarios.main(evento("POST", "/usuarios", body={
        "nombre": "María García",
        "email": "maria.garcia@correo.com",
        "telefono": "3109876543",
        "barrio": "El Rodadero",
        "direccion": "Calle 10 #5-20",
        "acepta_politica": True,
    }), None)
    assert resp["statusCode"] == 201, f"Registro falló: {resp['body']}"
    maria = cuerpo(resp)
    uid = maria["id"]
    assert maria["nombre"] == "María García"
    assert maria["email"] == "maria.garcia@correo.com"
    assert maria["rol"] == "ciudadano"

    # ── Paso 2: Consultar perfil (simula "iniciar sesión") ────────────
    resp = usuarios.main(evento("GET", "/usuarios/{id}", path={"id": uid}, usuario=uid), None)
    assert resp["statusCode"] == 200
    perfil = cuerpo(resp)
    assert perfil["id"] == uid
    assert perfil["barrio"] == "El Rodadero"

    # ── Paso 3: Crear un reporte con ubicación GPS ────────────────────
    resp = reportes.main(evento("POST", "/reportes", body={
        "categoria": "vias",
        "subtipo": "calle_inundada",
        "lat": 11.2050,
        "lng": -74.2270,
        "barrio": "El Rodadero",
        "comuna": "Comuna 7",
        "direccion": "Cra 3 con Calle 12",
        "referencia": "frente al centro comercial",
        "descripcion": "La calle está completamente inundada por la lluvia, no pasan carros ni motos",
        "ubic_reportante": {"lat": 11.2051, "lng": -74.2271},
    }, usuario=uid), None)
    assert resp["statusCode"] == 201, f"Crear reporte falló: {resp['body']}"
    reporte = cuerpo(resp)
    rid = reporte["id"]
    assert reporte["estado"] == "pendiente"

    # ── Paso 4: Solicitar URL prefirmada para subir video ─────────────
    resp = reportes.main(evento("POST", "/reportes/{id}/media", path={"id": rid}, usuario=uid,
                                body={"content_type": "video/mp4", "tamano": 5000}), None)
    assert resp["statusCode"] == 201, f"Pedir URL falló: {resp['body']}"
    pedido = cuerpo(resp)
    mid = pedido["id"]
    assert pedido["metodo"] == "PUT"
    assert "test-media" in pedido["url_subida"]

    # ── Paso 5: Subir el video a S3 (simula lo que hace el navegador) ─
    clave = f"reportes/{rid}/{mid}.mp4"
    datos_video = b"\x00\x00\x00\x1cftypisom" + b"\x00" * 4992  # 5000 bytes simulados
    boto3.client("s3", region_name="us-east-1").put_object(
        Bucket="test-media", Key=clave, Body=datos_video, ContentType="video/mp4")

    # ── Paso 6: Confirmar que el video se subió ───────────────────────
    resp = reportes.main(evento("POST", "/reportes/{id}/media/{mid}/confirmar",
                                path={"id": rid, "mid": mid}, usuario=uid), None)
    assert resp["statusCode"] == 200, f"Confirmar video falló: {resp['body']}"
    confirmado = cuerpo(resp)
    assert confirmado["clase"] == "video"

    # Verificar en DynamoDB que el reporte tiene el video
    meta = tabla.get_item(Key={"PK": f"REP#{rid}", "SK": "META"})["Item"]
    assert int(meta["media_count"]) == 1
    assert meta["tiene_video"] is True

    # ── Paso 7: Ver el video en el feed público de /videos ────────────
    resp = reportes.main(evento("GET", "/videos"), None)
    assert resp["statusCode"] == 200
    feed = cuerpo(resp)
    assert feed["total"] >= 1
    video_en_feed = next((v for v in feed["videos"] if v["rid"] == rid), None)
    assert video_en_feed is not None, "El video no apareció en el feed"
    assert video_en_feed["barrio"] == "El Rodadero"
    assert video_en_feed["subtipo_nombre"] == "Calle inundada"
    assert "url" in video_en_feed

    # ── Paso 8: Ver el reporte con su video en el detalle ─────────────
    resp = reportes.main(evento("GET", "/reportes/{id}", path={"id": rid}), None)
    assert resp["statusCode"] == 200
    detalle = cuerpo(resp)
    assert len(detalle["media"]) == 1
    assert detalle["media"][0]["clase"] == "video"
    assert detalle["media"][0]["url"].startswith("http")

    # ── Paso 9: Ver el reporte en "mis reportes" ──────────────────────
    resp = usuarios.main(evento("GET", "/usuarios/{id}/reportes", path={"id": uid}, usuario=uid), None)
    assert resp["statusCode"] == 200
    mis = cuerpo(resp)
    assert mis["total"] >= 1
    assert any(r["id"] == rid for r in mis["reportes"])


# ── 2. FLUJO COMPLETO: REGISTRO → REPORTE → CONFIRMACIONES ─────────

def test_flujo_confirmacion_vecinal(redis_fake, tabla):
    """Un reporte recibe confirmaciones de vecinos hasta cambiar a estado 'confirmado'."""

    # Registrar al autor
    resp = usuarios.main(evento("POST", "/usuarios", body={
        "nombre": "Pedro López", "email": "pedro@correo.com",
        "telefono": "3001112233", "barrio": "Gaira", "acepta_politica": True,
    }), None)
    autor = cuerpo(resp)["id"]

    # Crear reporte
    resp = reportes.main(evento("POST", "/reportes", body={
        "categoria": "servicios", "subtipo": "tuberia_rota",
        "lat": 11.1930, "lng": -74.2240, "barrio": "Gaira",
        "comuna": "Comuna 8", "direccion": "Cra 4 #22-10",
        "referencia": "frente al colegio",
        "descripcion": "Tubería rota inundando la calle desde hace 2 horas",
        "ubic_reportante": {"lat": 11.1931, "lng": -74.2241},
    }, usuario=autor), None)
    rid = cuerpo(resp)["id"]

    # El reporte tiene TTL (se borra si nadie confirma)
    meta = tabla.get_item(Key={"PK": f"REP#{rid}", "SK": "META"})["Item"]
    assert "ttl" in meta

    # Registrar 3 vecinos y que confirmen
    vecinos = []
    for i in range(3):
        resp = usuarios.main(evento("POST", "/usuarios", body={
            "nombre": f"Vecino {i+1}", "email": f"vecino{i+1}@correo.com",
            "acepta_politica": True,
        }), None)
        vecinos.append(cuerpo(resp)["id"])

    # El autor no puede confirmar su propio reporte
    resp = reportes.main(evento("POST", "/reportes/{id}/confirmaciones",
                                path={"id": rid}, usuario=autor), None)
    assert resp["statusCode"] == 400

    # Primera confirmación: quita el TTL
    resp = reportes.main(evento("POST", "/reportes/{id}/confirmaciones",
                                path={"id": rid}, usuario=vecinos[0]), None)
    assert resp["statusCode"] == 201
    meta = tabla.get_item(Key={"PK": f"REP#{rid}", "SK": "META"})["Item"]
    assert "ttl" not in meta

    # No puede confirmar dos veces
    resp = reportes.main(evento("POST", "/reportes/{id}/confirmaciones",
                                path={"id": rid}, usuario=vecinos[0]), None)
    assert resp["statusCode"] == 409

    # Segunda y tercera confirmación → cambia a "confirmado"
    reportes.main(evento("POST", "/reportes/{id}/confirmaciones",
                         path={"id": rid}, usuario=vecinos[1]), None)
    resp = reportes.main(evento("POST", "/reportes/{id}/confirmaciones",
                                path={"id": rid}, usuario=vecinos[2]), None)
    assert resp["statusCode"] == 201
    resultado = cuerpo(resp)
    assert resultado["estado"] == "confirmado"
    assert resultado["confirmaciones"] == 3


# ── 3. FLUJO COMPLETO: REGISTRO DUPLICADO ───────────────────────────

def test_flujo_registro_duplicado(redis_fake, tabla):
    """Intentar registrarse con un correo que ya existe devuelve 409."""

    # Primer registro: exitoso
    resp = usuarios.main(evento("POST", "/usuarios", body={
        "nombre": "Laura Martínez", "email": "laura@correo.com", "acepta_politica": True,
    }), None)
    assert resp["statusCode"] == 201

    # Segundo registro con el mismo correo: rechazado
    resp = usuarios.main(evento("POST", "/usuarios", body={
        "nombre": "Laura Otra", "email": "laura@correo.com", "acepta_politica": True,
    }), None)
    assert resp["statusCode"] == 409
    assert "Ya existe" in cuerpo(resp)["error"]


# ── 4. FLUJO: REGISTRO SIN CONSENTIMIENTO ───────────────────────────

def test_flujo_registro_sin_consentimiento(redis_fake, tabla):
    """El registro requiere aceptar la política de datos (Ley 1581)."""
    resp = usuarios.main(evento("POST", "/usuarios", body={
        "nombre": "Sin Política", "email": "sinpolitica@correo.com",
    }), None)
    assert resp["statusCode"] == 400
    assert "1581" in cuerpo(resp)["error"]


# ── 5. FLUJO: PRIVACIDAD EN REPORTES DE SEGURIDAD ──────────────────

def test_flujo_reporte_seguridad_oculta_datos(redis_fake, tabla):
    """Los reportes de seguridad ocultan dirección, referencia y nombre del autor."""

    # Registrar usuario
    resp = usuarios.main(evento("POST", "/usuarios", body={
        "nombre": "Ana Ruiz", "email": "ana.ruiz@correo.com",
        "telefono": "3005551234", "barrio": "Centro Histórico", "acepta_politica": True,
    }), None)
    uid = cuerpo(resp)["id"]

    # Crear reporte de seguridad (robo)
    resp = reportes.main(evento("POST", "/reportes", body={
        "categoria": "seguridad", "subtipo": "robo",
        "lat": 11.2421, "lng": -74.2110,
        "barrio": "Centro Histórico", "comuna": "Comuna 1",
        "direccion": "Calle 18 #3-45", "referencia": "al lado del banco",
        "descripcion": "Acaban de atracar a una persona en esta esquina",
        "ubic_reportante": {"lat": 11.2422, "lng": -74.2111},
    }, usuario=uid), None)
    rid = cuerpo(resp)["id"]

    # Consultar como público: sin dirección, sin referencia, coordenadas aproximadas
    resp = reportes.main(evento("GET", "/reportes/{id}", path={"id": rid}), None)
    pub = cuerpo(resp)
    assert pub["ubicacion_aproximada"] is True
    assert (pub["lat"], pub["lng"]) != (11.2421, -74.2110)
    assert "direccion" not in pub
    assert "referencia" not in pub
    assert pub["autor"] == "Usuario verificado"

    # No se puede subir foto a un reporte de seguridad
    resp = reportes.main(evento("POST", "/reportes/{id}/media", path={"id": rid}, usuario=uid,
                                body={"content_type": "image/jpeg", "tamano": 1000}), None)
    assert resp["statusCode"] == 400


# ── 6. FLUJO: SUBIR FOTO Y VIDEO AL MISMO REPORTE ──────────────────

def test_flujo_multiples_medios(redis_fake, tabla):
    """Un usuario sube una foto y un video al mismo reporte."""

    # Registrar
    resp = usuarios.main(evento("POST", "/usuarios", body={
        "nombre": "Carlos Vega", "email": "carlos.vega@correo.com", "acepta_politica": True,
    }), None)
    uid = cuerpo(resp)["id"]

    # Crear reporte
    resp = reportes.main(evento("POST", "/reportes", body={
        "categoria": "vias", "subtipo": "hueco",
        "lat": 11.2300, "lng": -74.2000, "barrio": "Mamatoco",
        "comuna": "Comuna 5", "direccion": "Troncal del Caribe km 3",
        "referencia": "a la altura de la Y", "descripcion": "Hueco enorme que ocupa medio carril",
        "ubic_reportante": {"lat": 11.2301, "lng": -74.2001},
    }, usuario=uid), None)
    rid = cuerpo(resp)["id"]

    s3_client = boto3.client("s3", region_name="us-east-1")

    # Subir una foto
    resp = reportes.main(evento("POST", "/reportes/{id}/media", path={"id": rid}, usuario=uid,
                                body={"content_type": "image/jpeg", "tamano": 2000}), None)
    assert resp["statusCode"] == 201
    foto_id = cuerpo(resp)["id"]
    s3_client.put_object(Bucket="test-media", Key=f"reportes/{rid}/{foto_id}.jpg",
                         Body=b"\xff\xd8\xff\xe0" + b"\x00" * 1996, ContentType="image/jpeg")
    resp = reportes.main(evento("POST", "/reportes/{id}/media/{mid}/confirmar",
                                path={"id": rid, "mid": foto_id}, usuario=uid), None)
    assert resp["statusCode"] == 200
    assert cuerpo(resp)["clase"] == "foto"

    # Subir un video
    resp = reportes.main(evento("POST", "/reportes/{id}/media", path={"id": rid}, usuario=uid,
                                body={"content_type": "video/mp4", "tamano": 3000}), None)
    assert resp["statusCode"] == 201
    video_id = cuerpo(resp)["id"]
    s3_client.put_object(Bucket="test-media", Key=f"reportes/{rid}/{video_id}.mp4",
                         Body=b"\x00" * 3000, ContentType="video/mp4")
    resp = reportes.main(evento("POST", "/reportes/{id}/media/{mid}/confirmar",
                                path={"id": rid, "mid": video_id}, usuario=uid), None)
    assert resp["statusCode"] == 200
    assert cuerpo(resp)["clase"] == "video"

    # Verificar que el detalle muestra ambos medios
    resp = reportes.main(evento("GET", "/reportes/{id}", path={"id": rid}), None)
    medios = cuerpo(resp)["media"]
    assert len(medios) == 2
    clases = {m["clase"] for m in medios}
    assert clases == {"foto", "video"}

    # El video aparece en /videos
    resp = reportes.main(evento("GET", "/videos"), None)
    feed = cuerpo(resp)
    assert any(v["rid"] == rid for v in feed["videos"])


# ── 7. FLUJO: ACCESO NO AUTORIZADO ─────────────────────────────────

def test_flujo_acceso_no_autorizado(redis_fake, tabla):
    """Verificar restricciones de acceso: sin sesión, perfil ajeno, etc."""

    # Registrar dos usuarios
    resp = usuarios.main(evento("POST", "/usuarios", body={
        "nombre": "Usuario A", "email": "a@correo.com", "acepta_politica": True,
    }), None)
    uid_a = cuerpo(resp)["id"]

    resp = usuarios.main(evento("POST", "/usuarios", body={
        "nombre": "Usuario B", "email": "b@correo.com", "acepta_politica": True,
    }), None)
    uid_b = cuerpo(resp)["id"]

    # No se puede ver el perfil de otro
    resp = usuarios.main(evento("GET", "/usuarios/{id}", path={"id": uid_a}, usuario=uid_b), None)
    assert resp["statusCode"] == 403

    # No se puede ver perfil sin sesión
    resp = usuarios.main(evento("GET", "/usuarios/{id}", path={"id": uid_a}), None)
    assert resp["statusCode"] == 401

    # No se puede crear reporte sin sesión
    resp = reportes.main(evento("POST", "/reportes", body={
        "categoria": "vias", "subtipo": "hueco", "lat": 11.23, "lng": -74.20,
        "barrio": "Gaira", "comuna": "C8", "direccion": "Cra 1",
        "referencia": "x", "descripcion": "Hueco en la vía principal",
        "ubic_reportante": {"lat": 11.23, "lng": -74.20},
    }), None)
    assert resp["statusCode"] == 401

    # No se puede subir media a un reporte ajeno
    resp = reportes.main(evento("POST", "/reportes", body={
        "categoria": "vias", "subtipo": "hueco", "lat": 11.23, "lng": -74.20,
        "barrio": "Gaira", "comuna": "C8", "direccion": "Cra 1",
        "referencia": "x", "descripcion": "Hueco en la vía principal de Gaira",
        "ubic_reportante": {"lat": 11.23, "lng": -74.20},
    }, usuario=uid_a), None)
    rid = cuerpo(resp)["id"]

    resp = reportes.main(evento("POST", "/reportes/{id}/media", path={"id": rid}, usuario=uid_b,
                                body={"content_type": "video/mp4", "tamano": 1000}), None)
    assert resp["statusCode"] == 403
