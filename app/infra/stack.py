"""
AlertaSamariaStack
──────────────────
Infraestructura serverless de Alerta Samaria:

- Tabla DynamoDB única (Single Table Design) con PK/SK, 4 GSI y TTL
- 4 Lambdas Python 3.11 que comparten el mismo paquete de código:
    reportes  → endpoints públicos y del ciudadano sobre reportes
    usuarios  → registro, perfil y "mis reportes"
    entidad   → panel de entidades (pendientes, estado, estadísticas, riesgo)
    health    → verificación de DynamoDB y Redis
- API Gateway (REST) con CORS para el frontend en React

Basado en el stack del proyecto base del curso (gitlab.com/caov_unimag/bd_no_sql).
"""
import os
import shutil
import subprocess
import sys
from typing import Any

import aws_cdk as cdk
import jsii
from aws_cdk import (
    Stack,
    aws_dynamodb as ddb,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    RemovalPolicy,
    CfnOutput,
)
from constructs import Construct

RUNTIME: _lambda.Runtime = _lambda.Runtime.PYTHON_3_11
DIR_CODIGO: str = "lambdas/src"
DIR_LAYER: str = "layers/dependencias"
REQUIREMENTS_LAYER: str = os.path.join(DIR_LAYER, "requirements.txt")

# LocalStack Community acepta Lambda Layers pero no las monta al ejecutar.
# En el emulador las dependencias se empaquetan dentro del código.
ES_LOCAL: bool = "AWS_ENDPOINT_URL" in os.environ


def _pip_install(requirements: str, destino: str) -> None:
    """Instala dependencias con wheels para el runtime de Lambda (Linux x86_64, Py 3.11)."""
    subprocess.run(
        [
            sys.executable, "-m", "pip", "install", "--quiet",
            "--requirement", requirements, "--target", destino,
            "--platform", "manylinux2014_x86_64", "--implementation", "cp",
            "--python-version", "3.11", "--only-binary=:all:", "--no-compile",
        ],
        check=True,
    )


@jsii.implements(cdk.ILocalBundling)
class _PipLocal:
    """Empaqueta con el pip del contenedor cdk-dev, sin necesitar Docker."""

    def __init__(self, requirements: str, subdir: str = "", copiar_desde: str | None = None) -> None:
        self.requirements = requirements
        self.subdir = subdir
        self.copiar_desde = copiar_desde

    def try_bundle(self, output_dir: str, *args: Any, **kwargs: Any) -> bool:
        if self.copiar_desde:
            shutil.copytree(self.copiar_desde, output_dir, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
        _pip_install(self.requirements, os.path.join(output_dir, self.subdir))
        return True


def _codigo_lambdas() -> _lambda.Code:
    """Paquete de código común a todas las Lambdas."""
    if not ES_LOCAL:
        return _lambda.Code.from_asset(DIR_CODIGO)
    return _lambda.Code.from_asset(
        DIR_CODIGO,
        asset_hash_type=cdk.AssetHashType.OUTPUT,
        bundling=cdk.BundlingOptions(
            image=RUNTIME.bundling_image,
            command=["bash", "-c", "echo 'Requiere bundling local con pip' && exit 1"],
            local=_PipLocal(REQUIREMENTS_LAYER, copiar_desde=DIR_CODIGO),
        ),
    )


class AlertaSamariaStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ── 1. TABLA ÚNICA ─────────────────────────────────────────────
        tabla = ddb.Table(
            self, "AlertaSamariaTable",
            partition_key=ddb.Attribute(name="PK", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="SK", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",          # AP19: reportes sin confirmar en 48 h
            removal_policy=RemovalPolicy.DESTROY,  # en producción: RETAIN
        )
        # GSI1: mis reportes (AP11) · GSI2: reportes por barrio (AP4)
        # GSI3: panel de entidad por categoría+estado (AP13)
        # GSI4: feed por día — respaldo de Redis y reconstrucción (AP1, AP2, AP20)
        for n in (1, 2, 3, 4):
            tabla.add_global_secondary_index(
                index_name=f"GSI{n}",
                partition_key=ddb.Attribute(name=f"GSI{n}PK", type=ddb.AttributeType.STRING),
                sort_key=ddb.Attribute(name=f"GSI{n}SK", type=ddb.AttributeType.STRING),
                projection_type=ddb.ProjectionType.ALL,
            )

        # ── 2. LAYER (solo en AWS real) ────────────────────────────────
        layers: list[_lambda.ILayerVersion] = []
        if not ES_LOCAL:
            layers.append(_lambda.LayerVersion(
                self, "DependenciasLayer",
                code=_lambda.Code.from_asset(
                    DIR_LAYER,
                    bundling=cdk.BundlingOptions(
                        image=RUNTIME.bundling_image,
                        command=["bash", "-c", "pip install -r requirements.txt -t /asset-output/python"],
                        local=_PipLocal(REQUIREMENTS_LAYER, subdir="python"),
                    ),
                ),
                compatible_runtimes=[RUNTIME],
                description="boto3, botocore y redis",
            ))

        env_comun: dict[str, str] = {
            "TABLE_NAME": tabla.table_name,
            "REDIS_HOST": os.environ.get("REDIS_HOST", "redis"),
            "REDIS_PORT": os.environ.get("REDIS_PORT", "6379"),
            "RATE_REPORTES_HORA": "5",
            "RATE_LECTURAS_MINUTO": "120",
            "CONFIRMACIONES_REQUERIDAS": "3",
        }
        codigo = _codigo_lambdas()

        def funcion(nombre: str, handler: str, timeout: int = 10) -> _lambda.Function:
            return _lambda.Function(
                self, nombre, runtime=RUNTIME, handler=handler, code=codigo,
                layers=layers, environment=env_comun, memory_size=256,
                timeout=cdk.Duration.seconds(timeout),
            )

        fn_reportes = funcion("ReportesHandler", "reportes.main")
        fn_usuarios = funcion("UsuariosHandler", "usuarios.main")
        fn_entidad = funcion("EntidadHandler", "entidad.main")
        fn_health = funcion("HealthHandler", "health.main", timeout=5)

        # Mínimo privilegio por Lambda
        tabla.grant_read_write_data(fn_reportes)
        tabla.grant_read_write_data(fn_usuarios)
        tabla.grant_read_write_data(fn_entidad)
        tabla.grant_read_data(fn_health)

        # ── 3. API GATEWAY ─────────────────────────────────────────────
        api = apigw.RestApi(
            self, "Api",
            rest_api_name="AlertaSamaria-API",
            description="Alerta Samaria — reportes ciudadanos de Santa Marta",
            deploy_options=apigw.StageOptions(stage_name="prod"),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS,
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Usuario-Id"],
            ),
        )
        i_rep = apigw.LambdaIntegration(fn_reportes)
        i_usr = apigw.LambdaIntegration(fn_usuarios)
        i_ent = apigw.LambdaIntegration(fn_entidad)

        # Público y ciudadano — Lambda reportes
        reportes = api.root.add_resource("reportes")
        reportes.add_method("POST", i_rep)                                    # AP9
        reportes.add_resource("feed").add_method("GET", i_rep)                # AP1
        reportes.add_resource("cerca").add_method("GET", i_rep)               # AP2
        reporte = reportes.add_resource("{id}")
        reporte.add_method("GET", i_rep)                                      # AP3 + AP12
        reporte.add_resource("confirmaciones").add_method("POST", i_rep)      # AP10
        (api.root.add_resource("barrios").add_resource("{barrio}")
            .add_resource("reportes").add_method("GET", i_rep))               # AP4
        api.root.add_resource("ranking").add_resource("barrios").add_method("GET", i_rep)  # AP5
        api.root.add_resource("categorias").add_method("GET", i_rep)          # AP6

        # Usuarios — Lambda usuarios
        usuarios = api.root.add_resource("usuarios")
        usuarios.add_method("POST", i_usr)                                    # AP7
        usuario = usuarios.add_resource("{id}")
        usuario.add_method("GET", i_usr)                                      # AP8
        usuario.add_resource("reportes").add_method("GET", i_usr)             # AP11

        # Entidad — Lambda entidad
        entidad = api.root.add_resource("entidad")
        ent_reportes = entidad.add_resource("reportes")
        ent_reportes.add_method("GET", i_ent)                                 # AP13
        ent_reporte = ent_reportes.add_resource("{id}")
        ent_reporte.add_method("GET", i_ent)                                  # AP14
        ent_reporte.add_resource("estado").add_method("PATCH", i_ent)         # AP15
        entidad.add_resource("estadisticas").add_method("GET", i_ent)         # AP16
        entidad.add_resource("riesgo").add_resource("{barrio}").add_method("GET", i_ent)  # AP17

        api.root.add_resource("health").add_method("GET", apigw.LambdaIntegration(fn_health))

        # ── 4. OUTPUTS ─────────────────────────────────────────────────
        CfnOutput(self, "ApiUrl", value=api.url, description="URL base del API Gateway")
        CfnOutput(self, "ApiId", value=api.rest_api_id, description="api-id (cambia en cada reinicio)")
        CfnOutput(self, "TableName", value=tabla.table_name, description="Tabla DynamoDB")
