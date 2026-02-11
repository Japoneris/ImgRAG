"""Minimal FastAPI server for image embeddings."""
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from embedding import registry, DEVICE, load_image, compute_embedding
from schemas import (
    EmbeddingRequest,
    EmbeddingData,
    EmbeddingResponse,
    ModelInfo,
    ModelListResponse,
)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    models_dir = Path(__file__).parent / "models"
    registry.models_dir = models_dir
    registry.scan()

    print(f"Device: {DEVICE}")
    print(f"Pre-loading {len(registry.models)} model(s)...")
    for card in registry.models.values():
        print(f"  Loading {card.id} ({card.name}, dim={card.embedding_dim})...", flush=True)
        registry.load(card.id)
        print(f"  - {card.id}: ready")
    print("All models loaded.")

    yield

    registry.unload_all()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Image Embedding Micro-Server",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    data = [ModelInfo(**card.to_dict()) for card in registry.models.values()]
    return ModelListResponse(data=data)


@app.post("/v1/embeddings", response_model=EmbeddingResponse)
async def create_embedding(request: EmbeddingRequest):
    card = registry.get(request.model)
    if card is None:
        raise HTTPException(404, detail=f"Model not found: {request.model}")

    if not card.loaded:
        try:
            registry.load(request.model)
        except Exception as e:
            raise HTTPException(500, detail=f"Failed to load model: {e}")

    inputs = [request.input] if isinstance(request.input, str) else request.input

    results = []
    total_tokens = 0
    t0 = time.time()

    for i, input_data in enumerate(inputs):
        try:
            image = load_image(input_data)
        except Exception as e:
            raise HTTPException(400, detail=f"Failed to load image {i}: {e}")

        try:
            result = compute_embedding(card, image, request.encoding_format)
            results.append(EmbeddingData(embedding=result["embedding"], index=i))
            total_tokens += result["tokens"]
        except Exception as e:
            raise HTTPException(500, detail=f"Failed to compute embedding {i}: {e}")

    elapsed = time.time() - t0

    return EmbeddingResponse(
        data=results,
        model=request.model,
        usage={
            "prompt_tokens": total_tokens,
            "total_tokens": total_tokens,
            "elapsed_seconds": round(elapsed, 3),
        },
    )
