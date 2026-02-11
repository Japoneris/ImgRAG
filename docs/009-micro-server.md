# 009 - Image Embedding Micro-Server

Minimal FastAPI server for computing image embeddings.
Reimplemented from `../OpenAIServer`, keeping only the image embedding route.

## Structure

```
micro_server/
├── run.py              # Entry point (CLI args + uvicorn)
├── server.py           # FastAPI app + routes
├── embedding.py        # Model registry, image loading, inference
├── schemas.py          # Pydantic request/response models
├── requirements.txt
└── models/             # Model card JSONs
    ├── dinov2-small.json
    ├── dinov2-base.json
    └── dinov2-large.json
```

## Usage

```bash
cd micro_server
pip install -r requirements.txt
python run.py                        # default: 0.0.0.0:8000, auto device
python run.py --port 9000 --device cpu
```

## Endpoints

| Method | Path             | Description              |
|--------|------------------|--------------------------|
| GET    | `/health`        | Health check             |
| GET    | `/v1/models`     | List available models    |
| POST   | `/v1/embeddings` | Compute image embeddings |

## API contract

Fully compatible with the OpenAIServer `/v1/embeddings` endpoint.

**Request:**
```json
{
  "model": "dinov2-small",
  "input": "<url | base64 | data-url>",
  "encoding_format": "float"
}
```

**Response:**
```json
{
  "object": "list",
  "data": [{"object": "embedding", "embedding": [...], "index": 0}],
  "model": "dinov2-small",
  "usage": {"prompt_tokens": 257, "total_tokens": 257, "elapsed_seconds": 0.12}
}
```

## What was removed vs OpenAIServer

- Authentication middleware
- Text embedding, image generation, chat, completions, audio, segmentation routes
- LRU model eviction and memory limits
- All non-image-embedding model cards
