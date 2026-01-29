"""External API integrations - embedding API client."""

from .embedding_api import (
    EmbeddingAPI,
    EmbeddingAPIError,
    MockEmbeddingAPI,
    convert_to_png_base64,
    downscale_image,
    format_image_data_url,
    DEFAULT_MAX_DIMENSION,
)

__all__ = [
    "EmbeddingAPI",
    "EmbeddingAPIError",
    "MockEmbeddingAPI",
    "convert_to_png_base64",
    "downscale_image",
    "format_image_data_url",
    "DEFAULT_MAX_DIMENSION",
]
