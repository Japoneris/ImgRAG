# Embedding Database

## Overview

A ChromaDB-based vector database for storing and searching image embeddings. Each embedding model gets its own collection to ensure consistent vector dimensions.

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Image File    │────▶│  Embedding API  │────▶│  EmbeddingDB    │
│                 │     │  (external)     │     │  (ChromaDB)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │                        │
                              ▼                        ▼
                        [float, float, ...]      Collection per
                        embedding vector         embedding model
```

## Components

### EmbeddingDatabase (`src/embedding_db.py`)

Manages embeddings in ChromaDB with one collection per model.

**Key Methods:**

| Method | Description |
|--------|-------------|
| `add_embedding(hash, embedding, model)` | Store an embedding for an image |
| `get_embedding(hash, model)` | Retrieve embedding by image hash |
| `search_similar(embedding, model, n)` | Find similar images by vector |
| `search_by_hash(hash, model, n)` | Find similar images given a hash |
| `delete_embedding(hash, model)` | Remove an embedding |
| `list_models()` | List all models with stored embeddings |
| `count(model)` | Count embeddings for a model |

### EmbeddingAPI (`src/embedding_api.py`)

Client for external embedding APIs.

**Expected API Format:**
```
POST {base_url}/v1/embeddings
Request:  {"image": "<base64>", "model": "<model_name>"}
Response: {"embedding": [0.1, 0.2, ...], "model": "...", "dimensions": 512}
```

**Classes:**
- `EmbeddingAPI` - Real API client
- `MockEmbeddingAPI` - For testing (generates deterministic pseudo-embeddings)

## Usage

### Basic Usage

```python
from src.embedding_db import EmbeddingDatabase
from src.embedding_api import EmbeddingAPI

# Initialize
db = EmbeddingDatabase("data/embeddings")
api = EmbeddingAPI("http://localhost:8000")

# Add embedding
embedding = api.get_embedding("image.jpg", model="clip-vit-base")
db.add_embedding(
    image_hash="abc123...",
    embedding=embedding,
    model_name="clip-vit-base"
)

# Search similar
similar = db.search_similar(embedding, "clip-vit-base", n_results=10)
for image_hash, distance in similar:
    print(f"{image_hash}: {distance}")
```

### Using Mock API for Testing

```python
from src.embedding_api import MockEmbeddingAPI

api = MockEmbeddingAPI(dimensions=512)
embedding = api.get_embedding("test.jpg")  # Deterministic based on content
```

### Search by Image Hash

```python
# Find images similar to a known image
similar = db.search_by_hash(
    query_hash="abc123...",
    model_name="clip-vit-base",
    n_results=5
)
```

## Storage

ChromaDB stores data in `data/embeddings/` directory:
- Each model gets a separate collection
- Collections are named after the model (with `/` and `:` replaced by `_`)
- Data persists across restarts

## Multiple Models

You can store embeddings from different models simultaneously:

```python
# Store CLIP embedding
db.add_embedding(hash, clip_embedding, "clip-vit-base-32")

# Store different model embedding for same image
db.add_embedding(hash, resnet_embedding, "resnet-50")

# Search only within a specific model's embeddings
results = db.search_similar(query_emb, "clip-vit-base-32")
```

## Files

- `src/embedding_db.py` - ChromaDB database layer
- `src/embedding_api.py` - API client and mock for testing
- `data/embeddings/` - ChromaDB persistent storage (created automatically)

## Dependencies

- `chromadb` - Vector database
- `requests` - HTTP client for API calls
