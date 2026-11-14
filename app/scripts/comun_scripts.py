"""Utilidades compartidas por los scripts (leen outputs.json que genera deploy.sh)."""
import json
import os
import sys

RUTA_OUTPUTS = os.path.join(os.path.dirname(__file__), "..", "outputs.json")


def outputs() -> dict:
    if not os.path.exists(RUTA_OUTPUTS):
        sys.exit("No existe outputs.json: ejecuta primero  bash scripts/deploy.sh")
    with open(RUTA_OUTPUTS, encoding="utf-8") as f:
        return json.load(f)["AlertaSamariaStack"]


def url_interna(api_id: str) -> str:
    """Desde cdk-dev: *.localhost.localstack.cloud resolvería a 127.0.0.1 (el propio contenedor),
    por eso se usa el nombre del servicio 'emulador' con la forma _user_request_."""
    return f"http://emulador:4566/restapis/{api_id}/prod/_user_request_"


def url_host(api_id: str) -> str:
    """Desde tu navegador / Postman (no depende de DNS)."""
    return f"http://localhost:4566/restapis/{api_id}/prod/_user_request_"
