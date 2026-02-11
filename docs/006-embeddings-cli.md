# Embeddings CLI

## Overview

The embeddings CLI (`cli_embeddings.py`) computes image embeddings via an external API server and stores them in ChromaDB for similarity search.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `EMBEDDING_API_URL` | Yes | Base URL of the embedding API server |
| `EMBEDDING_MODEL` | No | Model name to use (default: "default") |
| `EMBEDDING_API_KEY` | No | API key for authentication |

**Example:**
```bash
export EMBEDDING_API_URL="http://localhost:8000"
export EMBEDDING_MODEL="clip-vit-base"
export EMBEDDING_API_KEY="your-api-key"
```

## Commands

### health

Check API server connectivity and list available models.

```bash
python -m src.cli_embeddings health
```

**Output:**
```
API URL: http://localhost:8000
Model: clip-vit-base
Status: OK
Available models: clip-vit-base, clip-vit-large
```

### embed-file

Compute and store embedding for a single image.

```bash
python -m src.cli_embeddings embed-file <path>
python -m src.cli_embeddings embed-file image.jpg --force
```

**Options:**
- `--force, -f`: Recompute even if embedding already exists

### embed-dir

Compute embeddings for all images in a directory (recursive).

```bash
python -m src.cli_embeddings embed-dir <path>
python -m src.cli_embeddings embed-dir ./photos --force
```

**Options:**
- `--force, -f`: Recompute all embeddings

### embed-db

Compute embeddings for images already in the metadata database. Requires an index file to locate images on disk.

```bash
# First, build the index
python -m src.cli ingest ./photos
python -m src.cli rebuild-index ./photos

# Then compute embeddings
python -m src.cli_embeddings embed-db
python -m src.cli_embeddings embed-db --force
```

**Options:**
- `--force, -f`: Recompute all embeddings

### embed-config

Compute embeddings for images in multiple directories defined in a YAML config file.

```bash
python -m src.cli_embeddings embed-config config.yaml
python -m src.cli_embeddings embed-config config.yaml --force
```

**Config file format:**
```yaml
paths:
  - /path/to/images1
  - /path/to/images2
recursive: true  # optional, default true
```

**Options:**
- `--force, -f`: Recompute all embeddings

### search

Find similar images by hash (or hash prefix).

```bash
python -m src.cli_embeddings search <hash>
python -m src.cli_embeddings search abc123 --limit 5
```

**Options:**
- `--limit, -n`: Number of results (default: 10)

**Output:**
```
Similar images to abc123def456...:

  789xyz012345...  (distance: 0.1234)
  456uvw789abc...  (distance: 0.2345)
```

### list

List stored embeddings for the current model.

```bash
python -m src.cli_embeddings list
python -m src.cli_embeddings list --show-hashes
python -m src.cli_embeddings list --show-hashes --limit 50
```

**Options:**
- `--show-hashes, -s`: Display image hashes
- `--limit, -n`: Maximum hashes to show (default: 100)

## Global Options

All commands support these options:

| Option | Default | Description |
|--------|---------|-------------|
| `--embeddings-db, -e` | `data/embeddings` | ChromaDB storage directory |
| `--database, -d` | `data/images.db` | SQLite metadata database |
| `--index, -i` | `data/index.json` | Hash-to-filepath index |

## Workflow

### Basic: Embed images from a directory

```bash
export EMBEDDING_API_URL="http://localhost:8000"
export EMBEDDING_MODEL="clip-vit-base"

# Compute embeddings for all images
python -m src.cli_embeddings embed-dir ./my-photos

# Search for similar images
python -m src.cli_embeddings search abc123
```

### Advanced: Integrate with metadata database

```bash
export EMBEDDING_API_URL="http://localhost:8000"
export EMBEDDING_MODEL="clip-vit-base"

# Step 1: Ingest images into metadata database
python -m src.cli ingest ./my-photos

# Step 2: Build index for file paths
python -m src.cli rebuild-index ./my-photos

# Step 3: Compute embeddings for all indexed images
python -m src.cli_embeddings embed-db

# Step 4: Search by hash
python -m src.cli search abc123           # Get metadata
python -m src.cli_embeddings search abc123  # Find similar
```

## Image Processing

Before sending to the API:
1. Images are converted to PNG format
2. Large images are downscaled (max 1024px by default)
3. Images are base64-encoded as data URLs

See [004-image-downscaling.md](004-image-downscaling.md) for details.

## Storage

Embeddings are stored in ChromaDB with:
- **ID**: Image SHA-256 hash
- **Vector**: Embedding from the model
- **Metadata**: filepath, dimensions, image size (if from metadata DB)

Each model gets its own collection, allowing multiple models to coexist.

## Error Handling

- Skips images that already have embeddings (use `--force` to override)
- Continues processing on individual image failures
- Reports summary at end: processed, skipped, errors

## Files

- `src/cli_embeddings.py` - CLI implementation
- `src/api/embedding_api.py` - API client
- `src/storage/embedding_db.py` - ChromaDB storage
