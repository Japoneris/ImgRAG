# How to Use - Image Embedding Storage

This guide walks you through the full workflow: from registering images to searching for similar ones.

## Prerequisites

**1. Activate the virtual environment and install the package:**

```bash
source img_env/bin/activate
pip install -e .
```

This gives you three commands: `imgdb`, `imgdb-embed`, and `imgdb-monitor`.

**2. Set up environment variables** (in `.env` or your shell):

```bash
export EMBEDDING_API_URL="http://localhost:8000"   # URL of the embedding API server
export EMBEDDING_MODEL="dinov2-small"              # Model to use (e.g. dinov2-small, dinov2-large)
```

**3. Make sure the embedding API server is running** before computing embeddings. You can check with:

```bash
imgdb-embed health
```

---

## Step-by-step workflow

### Step 1: Register images (compute hashes and store metadata)

Ingest your images into the SQLite metadata database. This computes the SHA-256 hash for each image and stores its metadata (dimensions, size, MIME type, dates).

```bash
# Ingest a single image
imgdb ingest /path/to/image.jpg

# Ingest a whole directory (recursive)
imgdb ingest /path/to/my-images/
```

Duplicates are automatically skipped.

### Step 2: Build the file index

The index maps each image hash to its file path on disk. This is needed so that the search tools can locate and display images.

```bash
imgdb rebuild-index /path/to/my-images/
```

This creates `data/index.json`. If your images are spread across multiple directories, run this on each directory (the index is additive).

Use `--relative` to store relative paths instead of absolute ones:

```bash
imgdb rebuild-index /path/to/my-images/ --relative
```

### Step 3: Compute embeddings

Now compute vector embeddings for all registered images. This sends each image to the embedding API and stores the resulting vectors in ChromaDB.

```bash
# Compute embeddings for all images in the metadata database
imgdb-embed embed-db
```

Already-embedded images are skipped. Use `--force` to recompute all:

```bash
imgdb-embed embed-db --force
```

**Alternative ways to compute embeddings:**

```bash
# Embed a single file directly
imgdb-embed embed-file /path/to/image.jpg

# Embed all images in a directory (no need to ingest first)
imgdb-embed embed-dir /path/to/my-images/

# Embed from a YAML config listing multiple directories
imgdb-embed embed-config configs/my-config.yaml
```

### Step 4: Search for similar images

#### Option A: CLI search

Search by image hash (full or prefix):

```bash
imgdb-embed search 7931b067c8 --limit 10
```

This returns the most similar images with their distance scores.

#### Option B: Streamlit web app

Launch the interactive web interface:

```bash
streamlit run app/app.py
```

Then open http://localhost:8501 in your browser. The app provides:

- **Upload page** - Upload new images (auto-ingests and computes embeddings)
- **Search page** - Upload an image or pick one from the database to find similar images
- **Hash Search page** - Look up an image by its hash

---

## Quick-start example

```bash
# Activate environment and install
source img_env/bin/activate
pip install -e .

# 1. Register images
imgdb ingest ~/Pictures/photos/

# 2. Build the index
imgdb rebuild-index ~/Pictures/photos/

# 3. Compute embeddings
imgdb-embed embed-db

# 4. Search (CLI)
imgdb-embed search <hash-prefix> --limit 10

# 4. Or search (web app)
streamlit run app/app.py
```

---

## Keeping things in sync with the monitor

If you regularly add or remove images from your directories, use the monitor to keep databases in sync.

**Create a config file:**

```bash
imgdb-monitor init configs/my-images.yaml
```

Edit it to list your image directories:

```yaml
paths:
  - /home/user/Pictures/photos
  - /mnt/external/images
recursive: true
```

**Check for inconsistencies** (read-only):

```bash
imgdb-monitor check configs/my-images.yaml
```

**Sync** (adds new images, removes deleted ones, computes missing embeddings):

```bash
# Preview changes first
imgdb-monitor sync configs/my-images.yaml --dry-run

# Apply changes
imgdb-monitor sync configs/my-images.yaml
```

---

## Other useful commands

```bash
# List all images in the metadata database
imgdb list

# Search metadata by hash
imgdb search 7931b0

# List stored embeddings
imgdb-embed list --show-hashes

# Check API status
imgdb-embed health
```

## Data storage

All data is stored locally in the `data/` directory:

| File | Description |
|------|-------------|
| `data/images.db` | SQLite database with image metadata |
| `data/index.json` | Hash-to-filepath mapping |
| `data/embeddings/` | ChromaDB vector database |
