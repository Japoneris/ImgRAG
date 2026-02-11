"""Pydantic schemas for API requests and responses."""
from typing import Optional
from pydantic import BaseModel


class ModelInfo(BaseModel):
    """Model information (OpenAI compatible)."""
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "local"
    name: Optional[str] = None
    task: Optional[str] = None
    description: Optional[str] = None
    size_mb: Optional[int] = None
    loaded: bool = False


class ModelListResponse(BaseModel):
    """Response for /v1/models."""
    object: str = "list"
    data: list[ModelInfo]


class EmbeddingRequest(BaseModel):
    """Request for /v1/embeddings (OpenAI compatible)."""
    model: str
    input: str | list[str]
    encoding_format: str = "float"  # "float" or "base64"


class EmbeddingData(BaseModel):
    """Single embedding result."""
    object: str = "embedding"
    embedding: list[float] | str
    index: int = 0


class EmbeddingResponse(BaseModel):
    """Response for /v1/embeddings (OpenAI compatible)."""
    object: str = "list"
    data: list[EmbeddingData]
    model: str
    usage: dict
