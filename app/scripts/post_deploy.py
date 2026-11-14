"""Muestra las URLs del API y escribe frontend/.env.local para el frontend en React."""
import os

from comun_scripts import outputs, url_host

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
