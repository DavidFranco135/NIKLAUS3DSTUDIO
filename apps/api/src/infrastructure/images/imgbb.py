"""Thin wrapper around ImgBB's upload API (https://api.imgbb.com) - the

product photo feature stores images there instead of R2/S3 so it doesn't
need its own bucket/CDN wiring; this is the one place that knows ImgBB's
request/response shape.
"""
import base64

import requests

from src.config import get_settings
from src.domain.shared.exceptions import (
    ImageTooLargeError,
    ProviderNotConfiguredError,
    UnsupportedFileKindError,
)

_UPLOAD_URL = "https://api.imgbb.com/1/upload"
_MAX_BYTES = 10 * 1024 * 1024
_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def upload_image(image_bytes: bytes, content_type: str) -> str:
    settings = get_settings()
    if not settings.imgbb_api_key:
        raise ProviderNotConfiguredError("IMGBB_API_KEY não configurada.")
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise UnsupportedFileKindError(f"Tipo de imagem não suportado: {content_type!r}.")
    if len(image_bytes) > _MAX_BYTES:
        raise ImageTooLargeError("Imagem maior que 10MB.")

    response = requests.post(
        _UPLOAD_URL,
        data={
            "key": settings.imgbb_api_key,
            "image": base64.b64encode(image_bytes).decode("ascii"),
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    return payload["data"]["url"]
