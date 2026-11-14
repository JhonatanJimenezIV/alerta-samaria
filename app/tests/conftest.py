"""
conftest.py — Fixtures compartidos.
moto simula DynamoDB (con los 4 GSI) y fakeredis simula Redis, así los tests
corren sin el emulador ni el contenedor de Redis.
"""
import json
import os
import sys
from typing import Any

import boto3
import fakeredis
import pytest
from moto import mock_aws

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../lambdas/src"))

# Dentro de cdk-dev AWS_ENDPOINT_URL apunta al emulador: si se deja, boto3 ignora moto
os.environ.pop("AWS_ENDPOINT_URL", None)
os.environ.pop("AWS_ENDPOINT_URL_S3", None)
os.environ.update({
    "AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test", "AWS_DEFAULT_REGION": "us-east-1",
    "TABLE_NAME": "test-tabla", "REDIS_HOST": "localhost", "REDIS_PORT": "6379",
    "RATE_REPORTES_HORA": "5", "RATE_LECTURAS_MINUTO": "1000", "CONFIRMACIONES_REQUERIDAS": "3",
})

from comun import cache, db  # noqa: E402


def _crear_tabla() -> Any:
    recurso = boto3.resource("dynamodb", region_name="us-east-1")
    atributos = [{"AttributeName": "PK", "AttributeType": "S"}, {"AttributeName": "SK", "AttributeType": "S"}]
    gsis = []
    for n in (1, 2, 3, 4):
        atributos += [{"AttributeName": f"GSI{n}PK", "AttributeType": "S"},
                      {"AttributeName": f"GSI{n}SK", "AttributeType": "S"}]
        gsis.append({"IndexName": f"GSI{n}",
                     "KeySchema": [{"AttributeName": f"GSI{n}PK", "KeyType": "HASH"},
                                   {"AttributeName": f"GSI{n}SK", "KeyType": "RANGE"}],
                     "Projection": {"ProjectionType": "ALL"}})
    tabla = recurso.create_table(
        TableName="test-tabla",
        KeySchema=[{"AttributeName": "PK", "KeyType": "HASH"}, {"AttributeName": "SK", "KeyType": "RANGE"}],
        AttributeDefinitions=atributos, GlobalSecondaryIndexes=gsis, BillingMode="PAY_PER_REQUEST")
    tabla.wait_until_exists()
    return tabla


@pytest.fixture
def tabla():
    with mock_aws():
        db.reiniciar()
        t = _crear_tabla()
        yield t
        db.reiniciar()


@pytest.fixture
def redis_fake(tabla):
    servidor = fakeredis.FakeServer()
    cliente = fakeredis.FakeRedis(server=servidor, decode_responses=True)
    cache.usar_cliente(cliente)
    yield cliente
    cache.usar_cliente(None)


@pytest.fixture
def redis_caido(tabla):
    """Redis que no responde: para probar el modo degradado."""
    servidor = fakeredis.FakeServer()
    servidor.connected = False
    cache.usar_cliente(fakeredis.FakeRedis(server=servidor, decode_responses=True))
    yield
    cache.usar_cliente(None)


# ── Helpers ──────────────────────────────────────────────────────────

def evento(metodo: str, recurso: str, path: dict | None = None, body: dict | None = None,
           usuario: str | None = None, qs: dict | None = None) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if usuario:
        headers["X-Usuario-Id"] = usuario
    return {"httpMethod": metodo, "resource": recurso, "pathParameters": path,
            "queryStringParameters": qs, "headers": headers,
            "body": json.dumps(body) if body is not None else None,
            "requestContext": {"identity": {"sourceIp": "127.0.0.1"}}}


def cuerpo(resp: dict[str, Any]) -> Any:
    return json.loads(resp["body"])


def crear_ciudadano(nombre: str = "Ana Pérez", email: str | None = None) -> str:
    import usuarios
    resp = usuarios.main(evento("POST", "/usuarios", body={
        "nombre": nombre, "email": email or f"{nombre.split()[0].lower()}{os.urandom(3).hex()}@correo.com",
        "telefono": "3001234567", "barrio": "Gaira", "acepta_politica": True}), None)
    assert resp["statusCode"] == 201, resp["body"]
    return cuerpo(resp)["id"]


def crear_entidad(categorias: list[str], nombre: str = "Entidad demo") -> str:
    uid = db.ulid()
    db.tabla().put_item(Item={"PK": f"USR#{uid}", "SK": "PERFIL", "tipo": "USUARIO", "id": uid,
                              "nombre": nombre, "email": f"{uid}@entidad.gov.co", "rol": "entidad",
                              "entidad": nombre, "categorias_atendidas": categorias})
    return uid


REPORTE_BASE = {"categoria": "servicios", "subtipo": "tuberia_rota", "lat": 11.1930, "lng": -74.2240,
                "barrio": "Gaira", "comuna": "Comuna 8", "direccion": "Cra 4 #22-10",
                "referencia": "frente al colegio", "descripcion": "Tubería rota inundando la calle",
                "ubic_reportante": {"lat": 11.1931, "lng": -74.2241}}


def crear_reporte(usuario: str, **cambios: Any) -> dict[str, Any]:
    import reportes
    resp = reportes.main(evento("POST", "/reportes", body={**REPORTE_BASE, **cambios}, usuario=usuario), None)
    assert resp["statusCode"] == 201, resp["body"]
    return cuerpo(resp)
