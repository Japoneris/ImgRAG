"""Image Database - Store and retrieve images by content hash.

Package structure:
    src/
    ├── cli.py              # Command-line interface
    ├── core/               # Core business logic
    │   ├── models.py       # Data models (ImageRecord)
    │   └── scanner.py      # Image scanning and metadata
    ├── storage/            # Data persistence
    │   ├── database.py     # SQLite metadata storage
    │   └── embedding_db.py # ChromaDB embedding storage
    └── api/                # External integrations
        └── embedding_api.py # Embedding API client
"""

from .core.models import ImageRecord
from .core.scanner import ImageScanner
from .storage.database import ImageDatabase
from .storage.embedding_db import EmbeddingDatabase
from .api.embedding_api import (
    EmbeddingAPI,
    EmbeddingAPIError,
    MockEmbeddingAPI,
    convert_to_png_base64,
    downscale_image,
    format_image_data_url,
    DEFAULT_MAX_DIMENSION,
)

__all__ = [
    # Core
    "ImageRecord",
    "ImageScanner",
    # Storage
    "ImageDatabase",
    "EmbeddingDatabase",
    # API
    "EmbeddingAPI",
    "EmbeddingAPIError",
    "MockEmbeddingAPI",
    "convert_to_png_base64",
    "downscale_image",
    "format_image_data_url",
    "DEFAULT_MAX_DIMENSION",
]
