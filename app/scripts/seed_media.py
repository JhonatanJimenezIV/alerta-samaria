"""
seed_media.py — Agrega solo los videos de ejemplo y las noticias a un despliegue que ya tiene datos.

    python scripts/seed_media.py      (dentro de cdk-dev, después de seed.py)

Se puede correr varias veces: no repite videos en un reporte que ya tiene uno ni noticias ya cargadas.
Los videos son clips con licencia libre de Wikimedia Commons (NO son de Santa Marta) y quedan
marcados como ejemplo con su crédito. Se adjuntan por el mismo flujo de la app:
pedir URL prefirmada → subir a S3 → confirmar.
"""
import hashlib
import json
import os
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.config import Config

sys.path.insert(0, os.path.dirname(__file__))
from comun_scripts import outputs, url_interna  # noqa: E402

o = outputs()
BASE = url_interna(o["ApiId"])
tabla = boto3.resource("dynamodb").Table(o["TableName"])
bucket = o.get("MediaBucketName")
s3 = boto3.client("s3", endpoint_url=os.environ.get("AWS_ENDPOINT_URL", "http://emulador:4566"),
                  config=Config(s3={"addressing_style": "path"}))

VIDEOS = [
    # (subtipo del reporte, archivo en Commons, autor, licencia)
    ("calle_inundada", "Presidente Getúlio Vargas alagada em chuva fortes.webm", "Vitorperrut555", "CC BY-SA 4.0"),
    ("arroyo", "Flood on the street.webm", "Amuzujoe", "CC BY-SA 4.0"),
    ("incendio_forestal", "Požar na italijanski strani.webm", "Bojan Marušič", "CC BY-SA 4.0"),
    ("trancon", "Ayalon trafic congestion time lapse.webm", "Saifunny", "CC BY-SA 4.0"),
    ("semaforo_danado", "Tirana traffic lights.webm", "Lan G.", "CC BY 4.0"),
    ("via_cerrada", "Temporary traffic signal at Colonel By Drive.webm", "137a", "CC0"),
    ("tuberia_rota", "Heavy rainfall in Bengaluru, 30May2013.webm", "Subhashish Panigrahi", "CC BY-SA 3.0"),
]

NOTICIAS = [
    "https://www.facebook.com/SantaMartaAD/posts/pfbid0RnK1mfL396i7idzdwZn5XKWya8xqXXtVhQuczKTvsB8v6PvpZYvXDxkWGFLvirxNl",
    "https://www.facebook.com/reel/2306879336814814/",
    "https://www.facebook.com/reel/1108482025553474/",
    "https://www.facebook.com/SantaMartaAD/posts/pfbid0HdegRkUYzr4TegfMP7CWzn31PrfSwuXxjHN9vNeqejRT6PwzDsjcH1j7oGtBpSGgl",
    "https://www.facebook.com/reel/1280256047855161/",
    "https://www.facebook.com/reel/1724472399394918/",
    "https://www.facebook.com/SantaMartaAD/posts/pfbid01JMvYaGLUtR9y9Bb2WtTcqmwyBUJRvLm6Yf7VU7SuJ6J6xsTtZHaG4S6CVDwQCBGl",
    "https://www.facebook.com/reel/1352826823489271/",
    "https://www.facebook.com/reel/1111179775071148/",
    "https://www.facebook.com/reel/1673897664181144/",
]


def api(metodo: str, ruta: str, body: dict | None = None, usuario: str | None = None) -> dict:
    datos = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + ruta, data=datos, method=metodo)
    req.add_header("Content-Type", "application/json")
    if usuario:
        req.add_header("X-Usuario-Id", usuario)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def descargar(url: str, intentos: int = 4) -> bytes:
    """Wikimedia limita las descargas seguidas (HTTP 429): se espera y se reintenta."""
    for intento in range(1, intentos + 1):
        req = urllib.request.Request(url, headers={"User-Agent": "AlertaSamaria/1.0 (proyecto academico; Universidad del Magdalena)"})
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or intento == intentos:
                raise
            espera = int(e.headers.get("Retry-After") or 0) or 15 * intento
            print(f"     Wikimedia pidió esperar (429). Reintento {intento + 1} de {intentos} en {espera} s…", flush=True)
            time.sleep(espera)
    raise RuntimeError("sin respuesta")


def url_commons(nombre: str) -> str:
    n = nombre.replace(" ", "_")
    h = hashlib.md5(n.encode()).hexdigest()
    return f"https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[:2]}/{urllib.parse.quote(n)}"


def todos_los_items(**kwargs) -> list[dict]:
    items, inicio = [], None
    while True:
        if inicio:
            kwargs["ExclusiveStartKey"] = inicio
        r = tabla.scan(**kwargs)  # Scan aceptable aquí: es un script de carga, no un patrón de acceso de la app
        items += r.get("Items", [])
        inicio = r.get("LastEvaluatedKey")
        if not inicio:
            return items


# ── Videos ───────────────────────────────────────────────────────────
print("▶ Videos de ejemplo (Wikimedia Commons)")
if not bucket:
    sys.exit("  ✖ outputs.json no tiene MediaBucketName: vuelve a correr bash scripts/deploy.sh")
reportes = todos_los_items(FilterExpression=Attr("tipo").eq("REPORTE"))
por_subtipo: dict[str, dict] = {}
for r in sorted(reportes, key=lambda x: x["creado_en"], reverse=True):
    por_subtipo.setdefault(r["subtipo"], r)

subidos = 0
for sub, archivo, autor_v, licencia in VIDEOS:
    rep = por_subtipo.get(sub)
    if not rep:
        print(f"   · Sin reporte de '{sub}', se omite {archivo}")
        continue
    rid, autor = rep["id"], rep["autor_id"]
    ya = tabla.query(KeyConditionExpression=Key("PK").eq(f"REP#{rid}") & Key("SK").begins_with("MEDIA#"), Select="COUNT")["Count"]
    if ya:
        print(f"   · El reporte de '{sub}' ya tiene adjuntos, se omite")
        continue
    try:
        print(f"   ↓ Descargando {archivo}…", flush=True)
        datos = descargar(url_commons(archivo))
        pedido = api("POST", f"/reportes/{rid}/media", {"content_type": "video/webm", "tamano": len(datos)}, usuario=autor)
        clave = f"reportes/{rid}/{pedido['id']}.webm"
        s3.put_object(Bucket=bucket, Key=clave, Body=datos, ContentType="video/webm")
        tabla.update_item(
            Key={"PK": f"REP#{rid}", "SK": f"MEDIA#{pedido['id']}"}, UpdateExpression="SET credito = :c",
            ExpressionAttributeValues={":c": {
                "ejemplo": True, "titulo": archivo.rsplit(".", 1)[0], "autor": autor_v, "licencia": licencia,
                "fuente": "Wikimedia Commons",
                "url": "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(archivo.replace(" ", "_"))}})
        api("POST", f"/reportes/{rid}/media/{pedido['id']}/confirmar", {}, usuario=autor)
        subidos += 1
        print(f"   ✔ {len(datos) / 1e6:.1f} MB adjuntado al reporte de '{sub}' ({rep['barrio']})")
        time.sleep(5)  # pausa entre descargas para no disparar el límite de Wikimedia
    except urllib.error.HTTPError as e:
        cuerpo = e.read().decode(errors="ignore")
        detalle = "límite de descargas de Wikimedia; vuelve a correr el script en unos minutos" if e.code == 429 else cuerpo[:160]
        print(f"   ⚠ {archivo}: HTTP {e.code} ({detalle})")
    except Exception as e:  # noqa: BLE001
        print(f"   ⚠ {archivo}: {type(e).__name__}: {e}")
        traceback.print_exc(limit=1)

# ── Noticias ─────────────────────────────────────────────────────────
print("▶ Noticias de Santa Marta Al Día")
existentes = {i["url"] for i in tabla.query(KeyConditionExpression=Key("PK").eq("NOTICIAS")).get("Items", [])}
nuevas = 0
for url in reversed(NOTICIAS):  # la primera de la lista queda como la más reciente
    if url in existentes:
        continue
    try:
        api("POST", "/noticias", {"url": url, "fuente": "Santa Marta Al Día"}, usuario="ENT-SERVICIOS")
        nuevas += 1
    except Exception as e:  # noqa: BLE001
        print(f"   ⚠ {url[:60]}…: {e}")

# ── Usuarios de demostración para la pantalla "Ingresar" ──────────────
# Se reconstruye desde DynamoDB por si seed.py se interrumpió antes de escribir el archivo.
usuarios = todos_los_items(FilterExpression=Attr("tipo").eq("USUARIO"))
demo = {"ciudadanos": {u["nombre"]: u["id"] for u in sorted(usuarios, key=lambda u: u.get("creado_en", "")) if u.get("rol") == "ciudadano"},
        "entidades": {u["nombre"]: u["id"] for u in usuarios if u.get("rol") == "entidad"}}
destinos = [os.path.join(os.path.dirname(__file__), "usuarios_demo.json")]
if os.path.isdir("/frontend"):
    os.makedirs("/frontend/public", exist_ok=True)
    destinos.append("/frontend/public/usuarios_demo.json")
for ruta in destinos:
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(demo, f, ensure_ascii=False, indent=2)
print(f"▶ Usuarios de demostración actualizados: {len(demo['ciudadanos'])} ciudadanos y {len(demo['entidades'])} entidades")

print(f"\n✔ Listo: {subidos} videos y {nuevas} noticias nuevas.")
