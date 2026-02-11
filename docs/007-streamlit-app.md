# Streamlit Web Application

## Overview

A web-based interface for the Image Database system built with Streamlit.

## Structure

```
app/
├── app.py           # Root page with system status
└── pages/
    ├── 1_Upload.py      # Image upload page
    ├── 2_Search.py      # Similarity search page
    └── 3_Hash_Search.py # Hash-based search page
```

## Running the App

```bash
# Activate virtual environment
source img_env/bin/activate

# Run the app
streamlit run app/app.py
```

## Pages

### Home (app.py)
- Displays system status
- Shows count of images in metadata DB
- Shows available embedding collections

### Upload (1_Upload.py)
- Upload single or multiple images
- Automatically computes hash and extracts metadata
- Stores records in ImageDatabase (SQLite)
- Optionally computes embeddings via external API
- Stores embeddings in EmbeddingDatabase (ChromaDB)

### Search (2_Search.py)
- Upload an image to search for similar ones
- Or select from existing database images
- Uses vector similarity search
- Displays matching images with distance scores and file paths

### Hash Search (3_Hash_Search.py)
- Search by exact SHA-256 hash or hash prefix
- Upload an image to compute and lookup its hash
- Or enter a hash/prefix directly
- Shows full metadata for matching images

## Configuration

Set these environment variables before running:

- `EMBEDDING_API_URL`: URL of embedding API (default: http://localhost:8000)
- `EMBEDDING_MODELS`: Comma-separated list of available models (e.g., `dinov2-large,dinov2-small,dinov2-base`)
- `EMBEDDING_API_KEY`: API key if required (optional)

Or configure via the sidebar in the app.

## Path Resolution

The app uses the `data/index.json` file to map image hashes to file paths. The index contains:
- `_meta.base_path`: Absolute path to the images directory
- `images`: Hash-to-relative-path mapping

Full paths are constructed by joining `base_path` with the relative path from the index. This ensures images are found regardless of where the Streamlit app is launched from.
