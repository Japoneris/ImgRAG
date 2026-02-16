"""Image embedding: model loading, image utilities, and inference."""
import base64
import io
import json
import os
import struct
import time
from pathlib import Path
from typing import Any, Optional

import requests
import torch
from PIL import Image


# ---------------------------------------------------------------------------
# Device configuration
# ---------------------------------------------------------------------------

def get_device() -> str:
    """Resolve device from DEVICE env var (auto/cpu/cuda/gpu)."""
    env = os.environ.get("DEVICE", "auto").lower()
    if env == "cpu":
        return "cpu"
    if env in ("cuda", "gpu"):
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA requested but not available")
        return "cuda"
    # auto
    return "cuda" if torch.cuda.is_available() else "cpu"


DEVICE = get_device()
print("DEVICE: ", DEVICE)


# ---------------------------------------------------------------------------
# Image loading
# ---------------------------------------------------------------------------

def load_image(input_data: str) -> Image.Image:
    """Load an image from URL, base64, or data URL."""
    if input_data.startswith(("http://", "https://")):
        response = requests.get(input_data, timeout=30)
        response.raise_for_status()
        return Image.open(io.BytesIO(response.content)).convert("RGB")
    if input_data.startswith("data:image"):
        _header, data = input_data.split(",", 1)
        image_bytes = base64.b64decode(data)
        return Image.open(io.BytesIO(image_bytes)).convert("RGB")
    # raw base64
    image_bytes = base64.b64decode(input_data)
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


# ---------------------------------------------------------------------------
# Model card
# ---------------------------------------------------------------------------

class ModelCard:
    """A model described by a JSON file in models/."""

    def __init__(self, cfg: dict):
        self.id: str = cfg["id"]
        self.name: str = cfg["name"]
        self.hf_model: str = cfg["hf_model"]
        self.task: str = cfg["task"]
        self.description: str = cfg.get("description", "")
        self.embedding_dim: Optional[int] = cfg.get("embedding_dim")
        self.size_mb: Optional[int] = cfg.get("size_mb")

        # runtime
        self.model: Any = None
        self.processor: Any = None

    @property
    def loaded(self) -> bool:
        return self.model is not None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "object": "model",
            "created": 0,
            "owned_by": "local",
            "name": self.name,
            "task": self.task,
            "description": self.description,
            "size_mb": self.size_mb,
            "loaded": self.loaded,
        }


# ---------------------------------------------------------------------------
# Registry (simplified – no eviction, no pinning)
# ---------------------------------------------------------------------------

class ModelRegistry:
    def __init__(self, models_dir: str = "models"):
        self.models_dir = Path(models_dir)
        self.models: dict[str, ModelCard] = {}

    def scan(self) -> None:
        self.models.clear()
        if not self.models_dir.exists():
            return
        for p in self.models_dir.glob("*.json"):
            try:
                with open(p) as f:
                    card = ModelCard(json.load(f))
                self.models[card.id] = card
            except Exception as e:
                print(f"Warning: skipping {p}: {e}")

    def get(self, model_id: str) -> Optional[ModelCard]:
        return self.models.get(model_id)

    def load(self, model_id: str) -> ModelCard:
        card = self.get(model_id)
        if card is None:
            raise ValueError(f"Model not found: {model_id}")
        if card.loaded:
            return card
        card.model, card.processor = _load_vision_model(card)
        return card

    def unload_all(self) -> None:
        for card in self.models.values():
            card.model = None
            card.processor = None


registry = ModelRegistry()


# ---------------------------------------------------------------------------
# Vision model loader
# ---------------------------------------------------------------------------

def _load_vision_model(card: ModelCard):
    from transformers import AutoImageProcessor, AutoModel

    processor = AutoImageProcessor.from_pretrained(card.hf_model)
    model = AutoModel.from_pretrained(card.hf_model).to(DEVICE)
    return model, processor


# ---------------------------------------------------------------------------
# Embedding computation
# ---------------------------------------------------------------------------

def encode_embedding(embedding: list[float], fmt: str) -> list[float] | str:
    if fmt == "base64":
        packed = struct.pack(f"{len(embedding)}f", *embedding)
        return base64.b64encode(packed).decode("utf-8")
    return embedding


def compute_embedding(card: ModelCard, image: Image.Image, encoding_format: str = "float") -> dict:
    """Run the model on a single image, return embedding + token count."""
    if not card.loaded:
        raise RuntimeError(f"Model {card.id} is not loaded")

    inputs = card.processor(images=image, return_tensors="pt")
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = card.model(**inputs)

    last_hidden = outputs.last_hidden_state
    cls_embedding = last_hidden[0, 0, :].tolist()

    return {
        "embedding": encode_embedding(cls_embedding, encoding_format),
        "tokens": last_hidden.shape[1],
    }
