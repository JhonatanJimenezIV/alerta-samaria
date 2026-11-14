"""
media.py — Fotos y videos adjuntos a un reporte (AP21–AP23).

Flujo (el archivo nunca pasa por la Lambda ni por API Gateway):
  1. POST /reportes/{id}/media                → la Lambda valida y devuelve una URL prefirmada de S3 (PUT)
  2. El navegador sube el archivo directo a S3 con esa URL
  3. POST /reportes/{id}/media/{mid}/confirmar → se marca "listo" y, si es video, entra al feed de /videos

Modelo (misma partición del reporte, así el detalle sigue siendo un solo Query):
  PK=REP#<id>  SK=MEDIA#<mid>   tipo=MEDIA, clase=foto|video, clave S3, estado=subiendo|listo
  GSI4PK=MEDIA#<fecha>  GSI4SK=<fecha>#<mid>   (sobrecarga del GSI4: respaldo de /videos si Redis cae)

Redis:
  media:videos      Sorted Set  score = timestamp   → ids de videos recientes (AP23)
  media:{mid}       String JSON TTL 1 h             → datos del video para hidratar el feed
"""
import os
from typing import Any

import boto3
from botocore.config import Config

TIPOS = {
    "image/jpeg": ("foto", "jpg"), "image/png": ("foto", "png"), "image/webp": ("foto", "webp"),
    "video/mp4": ("video", "mp4"), "video/webm": ("video", "webm"), "video/quicktime": ("video", "mov"),
}
LIMITE_BYTES = {"foto": 8 * 1024 * 1024, "video": 50 * 1024 * 1024}
MAX_POR_REPORTE = 4
EXPIRA_SUBIDA = 900      # la URL de subida vale 15 min
EXPIRA_LECTURA = 3600    # las URLs de lectura valen 1 h (más que el TTL de la caché)

_s3_interno: Any = None
_s3_publico: Any = None


def bucket() -> str:
    return os.environ["MEDIA_BUCKET"]


def _cliente(endpoint: str | None) -> Any:
    return boto3.client("s3", endpoint_url=endpoint or None,
                        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}))


def s3() -> Any:
    """Cliente para operaciones de la Lambda (dentro de la red del emulador)."""
    global _s3_interno
    if _s3_interno is None:
        _s3_interno = _cliente(None)
    return _s3_interno


def s3_publico() -> Any:
    """
    Cliente solo para firmar URLs que usará el NAVEGADOR. En el emulador el navegador
    llega a S3 por http://localhost:4566 (PUBLIC_S3_ENDPOINT); en AWS real no se define.
    """
    global _s3_publico
    if _s3_publico is None:
        _s3_publico = _cliente(os.environ.get("PUBLIC_S3_ENDPOINT"))
    return _s3_publico


def reiniciar() -> None:
    global _s3_interno, _s3_publico
    _s3_interno = _s3_publico = None


def url_subida(clave: str, content_type: str) -> str:
    return s3_publico().generate_presigned_url(
        "put_object", Params={"Bucket": bucket(), "Key": clave, "ContentType": content_type},
        ExpiresIn=EXPIRA_SUBIDA)


def url_lectura(clave: str) -> str:
    return s3_publico().generate_presigned_url(
        "get_object", Params={"Bucket": bucket(), "Key": clave}, ExpiresIn=EXPIRA_LECTURA)


def tamano_subido(clave: str) -> int | None:
    """Verifica en S3 que el archivo realmente se subió (HeadObject)."""
    try:
        return int(s3().head_object(Bucket=bucket(), Key=clave)["ContentLength"])
    except Exception:  # noqa: BLE001
        return None


def publico(item: dict[str, Any]) -> dict[str, Any]:
    return {"id": item["mid"], "clase": item["clase"], "content_type": item["content_type"],
            "url": url_lectura(item["clave"]), "creado_en": item["creado_en"]}
