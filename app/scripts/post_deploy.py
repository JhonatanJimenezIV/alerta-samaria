"""Muestra las URLs del API y escribe frontend/.env.local para el frontend en React."""
import os

import redis

import sys
import urllib.error
import urllib.request

from comun_scripts import outputs, url_host, url_interna

# Tras reiniciar el emulador, DynamoDB queda vacía pero Redis (con persistencia AOF) conserva
# el feed, el ranking y los detalles viejos. Redis es solo caché: se vacía para que no muestre
# datos que ya no existen en la fuente de verdad.
try:
    redis.Redis(host=os.environ.get("REDIS_HOST", "redis"), port=int(os.environ.get("REDIS_PORT", 6379))).flushdb()
    print("  ✔ Caché de Redis vaciada (la fuente de verdad es DynamoDB)")
except redis.RedisError as e:
    print(f"  ⚠ No se pudo vaciar Redis: {e}")

o = outputs()
api_id = o["ApiId"]
base = url_host(api_id)

# Verifica que el API realmente responda. En LocalStack, actualizar un stack que ya existía
# a veces reemplaza el API Gateway y lo deja sin desplegar; en ese caso hay que partir de cero.
try:
    with urllib.request.urlopen(url_interna(api_id) + "/health", timeout=20) as r:
        r.read()
    print("  ✔ El API responde en /health")
except urllib.error.HTTPError as e:
    if e.code in (404, 403):
        sys.exit(f"""
  ✖ El despliegue terminó, pero el API {api_id} no responde ({e.code}).
    Pasa cuando LocalStack actualiza un stack viejo. Empieza desde cero:
      1. En tu máquina (fuera del contenedor):  docker compose restart emulador
      2. Dentro de cdk-dev:                      bash scripts/deploy.sh
""")
    print(f"  ⚠ /health respondió {e.code}; revisa los logs del emulador")
except Exception as e:  # noqa: BLE001
    print(f"  ⚠ No se pudo verificar el API: {e}")

ruta_env = "/frontend/.env.local"
if os.path.isdir("/frontend"):
    with open(ruta_env, "w", encoding="utf-8") as f:
        f.write(f"VITE_API_URL={base}\n")
    escrito = f"  ✔ frontend/.env.local actualizado (VITE_API_URL)"
else:
    escrito = "  (no se encontró /frontend; agrega la URL manualmente)"

print(f"""
════════════════════════════════════════════════════════════════
  Alerta Samaria desplegado
════════════════════════════════════════════════════════════════
  api-id ........ {api_id}
  Tabla ......... {o['TableName']}

  URL base (navegador / Postman):
    {base}

  Prueba rápida desde tu máquina:
    curl {base}/health
{escrito}

  Siguiente paso (datos de prueba):  python scripts/seed.py
════════════════════════════════════════════════════════════════
""")
