"""Muestra las URLs del API y escribe frontend/.env.local para el frontend en React."""
import os

import redis

from comun_scripts import outputs, url_host

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
