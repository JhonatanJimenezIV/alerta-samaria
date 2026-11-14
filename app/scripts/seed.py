"""
seed.py — Carga datos de demostración en el emulador.

    python scripts/seed.py          (dentro de cdk-dev, después de deploy.sh)

1. Guarda el catálogo de categorías en DynamoDB (PK=CONFIG, SK=CATEGORIAS).
2. Crea 4 entidades demo directamente en la tabla (rol entidad: lo asignaría un administrador).
3. Registra 6 ciudadanos y crea ~18 reportes en barrios reales de Santa Marta USANDO EL API,
   así se ejecuta el flujo completo (DynamoDB + Write-Through a Redis).
4. Agrega confirmaciones y cambia el estado de algunos reportes como lo haría una entidad.

Los ids de los usuarios demo quedan en scripts/usuarios_demo.json (para el frontend/Postman).
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

import boto3

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambdas", "src"))
from comun.catalogo import CATALOGO_INICIAL  # noqa: E402
from comun_scripts import outputs, url_interna  # noqa: E402

o = outputs()
BASE = url_interna(o["ApiId"])
tabla = boto3.resource("dynamodb").Table(o["TableName"])


def api(metodo: str, ruta: str, body: dict | None = None, usuario: str | None = None) -> dict:
    datos = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + ruta, data=datos, method=metodo)
    req.add_header("Content-Type", "application/json")
    if usuario:
        req.add_header("X-Usuario-Id", usuario)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"   ⚠ {metodo} {ruta} → {e.code}: {e.read().decode()[:150]}")
        return {}


# ── 1. Catálogo ──────────────────────────────────────────────────────
print("▶ Catálogo de categorías")
tabla.put_item(Item={"PK": "CONFIG", "SK": "CATEGORIAS", "tipo": "CONFIG", **CATALOGO_INICIAL})

# ── 2. Entidades demo ────────────────────────────────────────────────
print("▶ Entidades demo")
ENTIDADES = [
    ("ENT-SERVICIOS", "Servicios Públicos (demo)", ["servicios", "emergencias"]),
    ("ENT-MOVILIDAD", "Secretaría de Movilidad (demo)", ["vias", "transito"]),
    ("ENT-SEGURIDAD", "Seguridad y Convivencia (demo)", ["seguridad", "emergencias"]),
    ("ENT-AMBIENTE", "Ambiente y Espacio Público (demo)", ["ambiente", "animales", "playas", "otro"]),
]
for uid, nombre, cats in ENTIDADES:
    tabla.put_item(Item={"PK": f"USR#{uid}", "SK": "PERFIL", "tipo": "USUARIO", "id": uid, "nombre": nombre,
                         "email": f"{uid.lower()}@demo.alertasamaria.co", "rol": "entidad",
                         "entidad": nombre, "categorias_atendidas": cats})

# ── 3. Ciudadanos ────────────────────────────────────────────────────
print("▶ Ciudadanos demo")
sufijo = str(int(time.time()))[-5:]
CIUDADANOS = [("María Fernández", "Gaira"), ("Andrés Pertuz", "El Rodadero"), ("Luisa Ospino", "Taganga"),
              ("Jorge Barros", "Bastidas"), ("Camila Rojas", "Mamatoco"), ("Daniel Cantillo", "Centro Histórico")]
ciudadanos = []
for nombre, barrio in CIUDADANOS:
    email = f"{nombre.split()[0].lower()}.{sufijo}@correo.com"
    r = api("POST", "/usuarios", {"nombre": nombre, "email": email, "telefono": "300" + sufijo + "00",
                                  "barrio": barrio, "acepta_politica": True})
    if r.get("id"):
        ciudadanos.append(r["id"])
if len(ciudadanos) < 6:
    sys.exit("No se pudieron crear los ciudadanos; revisa que el API responda (curl .../health)")

# ── 4. Reportes (coordenadas aproximadas de cada barrio) ────────────
print("▶ Reportes")
B = {
    "Centro Histórico": (11.2420, -74.2110, "Comuna 2"), "El Rodadero": (11.2050, -74.2270, "Comuna 8"),
    "Gaira": (11.1930, -74.2240, "Comuna 8"), "Taganga": (11.2670, -74.1900, "Corregimiento Taganga"),
    "Mamatoco": (11.2280, -74.1650, "Comuna 6"), "Bastidas": (11.2530, -74.1980, "Comuna 1"),
    "Pescaíto": (11.2480, -74.2050, "Comuna 1"), "Los Almendros": (11.2230, -74.1880, "Comuna 5"),
    "Pozos Colorados": (11.1650, -74.2250, "Comuna 8"), "Bonda": (11.2350, -74.1300, "Corregimiento Bonda"),
}
REPORTES = [
    # (autor, categoria, subtipo, barrio, descripción, referencia, contacto)
    (0, "servicios", "tuberia_rota", "Gaira", "Tubo roto desde la mañana, el agua corre por toda la calle", "Frente al colegio", True),
    (0, "vias", "calle_inundada", "Gaira", "Con el aguacero la calle quedó intransitable para motos", "Calle 22 con carrera 5", False),
    (1, "transito", "semaforo_danado", "El Rodadero", "El semáforo está apagado y hay mucho tráfico", "Entrada al Rodadero", False),
    (1, "playas", "playa_contaminada", "El Rodadero", "Vertimiento de aguas residuales en la playa", "Cerca al acuario", False),
    (2, "emergencias", "incendio_forestal", "Taganga", "Se ve humo y fuego en el cerro", "Cerro del lado del mirador", True),
    (2, "ambiente", "basura", "Taganga", "Basura acumulada hace tres días", "Bajando a la playa", False),
    (3, "seguridad", "robo", "Bastidas", "Robaron un celular a una persona en la esquina", "", False),
    (3, "servicios", "alumbrado_danado", "Bastidas", "Toda la cuadra sin alumbrado público hace una semana", "Parque principal", True),
    (3, "seguridad", "zona_oscura", "Bastidas", "La calle queda muy sola y oscura en la noche", "", False),
    (4, "servicios", "sin_agua", "Mamatoco", "Dos días sin agua en el sector", "Cerca a la iglesia", True),
    (4, "vias", "tapa_alcantarilla", "Mamatoco", "Se robaron la tapa de la alcantarilla, es peligroso", "Frente a la tienda", False),
    (5, "transito", "trancon", "Centro Histórico", "Trancón fuerte por carro varado", "Carrera 5", False),
    (5, "animales", "perro_agresivo", "Centro Histórico", "Perro suelto que persigue a la gente", "Parque de los Novios", False),
    (5, "seguridad", "rina_disturbio", "Pescaíto", "Riña en la calle con varias personas", "", False),
    (0, "vias", "hueco", "Pozos Colorados", "Hueco grande en el carril derecho", "Vía al aeropuerto", False),
    (1, "ambiente", "aguas_estancadas", "Los Almendros", "Agua estancada con zancudos, riesgo de dengue", "Lote baldío", False),
    (2, "servicios", "sin_luz", "Bonda", "Sin energía en todo el corregimiento", "", True),
    (4, "seguridad", "robo", "Bastidas", "Atracaron a un domiciliario", "", False),
]
creados = []
for i, (autor, cat, sub, barrio, desc, ref, contacto) in enumerate(REPORTES):
    lat, lng, comuna = B[barrio]
    lat, lng = lat + (i % 3) * 0.0012, lng - (i % 4) * 0.0010   # separa un poco los pines
    r = api("POST", "/reportes", {
        "categoria": cat, "subtipo": sub, "barrio": barrio, "comuna": comuna, "lat": lat, "lng": lng,
        "descripcion": desc, "referencia": ref, "direccion": "", "contacto_autorizado": contacto,
        "anonimo": cat == "seguridad", "ubic_reportante": {"lat": lat + 0.0005, "lng": lng + 0.0005},
    }, usuario=ciudadanos[autor])
    if r.get("id"):
        creados.append((r["id"], autor, cat, sub))
        print(f"   ✔ {cat}/{sub} en {barrio}")

# ── 5. Confirmaciones y cambios de estado ────────────────────────────
print("▶ Confirmaciones")
def confirmar(indice: int, cuantos: int) -> None:
    rid, autor, *_ = creados[indice]
    otros = [u for n, u in enumerate(ciudadanos) if n != autor][:cuantos]
    for u in otros:
        api("POST", f"/reportes/{rid}/confirmaciones", usuario=u)

confirmar(0, 3)   # tubería rota → confirmado
confirmar(4, 4)   # incendio forestal → confirmado
confirmar(7, 2)   # alumbrado (queda pendiente con 2)
confirmar(1, 1)

print("▶ Entidades atendiendo reportes")
api("PATCH", f"/entidad/reportes/{creados[0][0]}/estado",
    {"estado": "en_atencion", "nota": "Cuadrilla de acueducto asignada"}, usuario="ENT-SERVICIOS")
api("PATCH", f"/entidad/reportes/{creados[2][0]}/estado",
    {"estado": "resuelto", "nota": "Semáforo reparado"}, usuario="ENT-MOVILIDAD")

demo = {"ciudadanos": dict(zip([c[0] for c in CIUDADANOS], ciudadanos)),
        "entidades": {nombre: uid for uid, nombre, _ in ENTIDADES}}
with open(os.path.join(os.path.dirname(__file__), "usuarios_demo.json"), "w", encoding="utf-8") as f:
    json.dump(demo, f, ensure_ascii=False, indent=2)
if os.path.isdir("/frontend"):  # el frontend los muestra en la pantalla "Ingresar"
    os.makedirs("/frontend/public", exist_ok=True)
    with open("/frontend/public/usuarios_demo.json", "w", encoding="utf-8") as f:
        json.dump(demo, f, ensure_ascii=False, indent=2)

print(f"""
✔ Listo: {len(creados)} reportes, {len(ciudadanos)} ciudadanos y {len(ENTIDADES)} entidades.
  Ids de usuarios demo en scripts/usuarios_demo.json (úsalos en el header X-Usuario-Id).
  Revisa Redis desde tu máquina:  docker compose exec redis redis-cli ZREVRANGE feed:ciudad 0 -1
""")
