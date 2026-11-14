#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Despliega Alerta Samaria en el emulador. Ejecutar dentro de cdk-dev:
#     bash scripts/deploy.sh
# Repetir después de cada reinicio del contenedor emulador
# (LocalStack Community no guarda estado).
# ─────────────────────────────────────────────────────────────────────
set -euo pipefail
cd /app

echo "▶ 1/3 Bootstrap del emulador..."
cdklocal bootstrap aws://000000000000/us-east-1 > /dev/null

echo "▶ 2/3 Desplegando el stack..."
cdklocal deploy --require-approval never --outputs-file outputs.json

echo "▶ 3/3 Configurando URLs..."
python scripts/post_deploy.py
