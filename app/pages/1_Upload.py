"""
Upload Images Page

Allows users to upload images to the database with automatic embedding generation.
"""
import sys
import os
from pathlib import Path
from io import BytesIO
import tempfile

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from PIL import Image

from src.storage.database import ImageDatabase
from src.storage.embedding_db import EmbeddingDatabase
from src.core.scanner import ImageScanner
from src.api.embedding_api import EmbeddingAPI

# Configuration
DB_PATH = Path(__file__).parent.parent.parent / "data" / "images.db"
EMBEDDING_DB_PATH = Path(__file__).parent.parent.parent / "data" / "embeddings"

st.set_page_config(page_title="Upload Images", page_icon="📤", layout="wide")

st.title("Upload Images")

# Embedding API configuration
st.sidebar.header("Embedding API Settings")
api_url = st.sidebar.text_input(
    "API URL",
    value=os.environ.get("EMBEDDING_API_URL", "http://localhost:8000"),
)

# Parse available models from environment
available_models = [
    m.strip()
    for m in os.environ.get("EMBEDDING_MODELS", "default").split(",")
    if m.strip()
]
model_name = st.sidebar.selectbox(
    "Model",
    options=available_models,
)

api_key = st.sidebar.text_input(
    "API Key (optional)",
    value=os.environ.get("EMBEDDING_API_KEY", ""),
    type="password",
)


@st.cache_resource
def get_databases():
    """Initialize database connections."""
    db = ImageDatabase(str(DB_PATH))
    emb_db = EmbeddingDatabase(str(EMBEDDING_DB_PATH))
    return db, emb_db


def get_embedding_api():
    """Create embedding API client."""
    return EmbeddingAPI(
        base_url=api_url,
        api_key=api_key if api_key else None,
    )


# File uploader
uploaded_files = st.file_uploader(
    "Choose images to upload",
    type=["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff"],
    accept_multiple_files=True,
)

if uploaded_files:
    db, emb_db = get_databases()
    scanner = ImageScanner()

    # Check embedding API availability
    try:
        api = get_embedding_api()
        if not api.health_check():
            st.error("Embedding API is not available. Cannot upload images.")
            st.stop()
    except Exception as e:
        st.error(f"Could not connect to embedding API: {e}")
        st.stop()

    st.header("Upload Results")

    progress_bar = st.progress(0)
    status_text = st.empty()

    results = []

    for i, uploaded_file in enumerate(uploaded_files):
        status_text.text(f"Processing {uploaded_file.name}...")

        try:
            # Read file bytes
            file_bytes = uploaded_file.read()

            # Save to temporary file to use existing scanner
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=Path(uploaded_file.name).suffix
            ) as tmp_file:
                tmp_file.write(file_bytes)
                tmp_path = tmp_file.name

            try:
                # Extract metadata
                record = scanner.extract_metadata(tmp_path)

                # Check if already exists - skip if duplicate
                existing = db.get_by_hash(record.hash)
                if existing:
                    results.append({
                        "filename": uploaded_file.name,
                        "hash": record.hash[:16] + "...",
                        "dimensions": f"{record.width}x{record.height}",
                        "size": record.size,
                        "status": "skipped (duplicate)",
                        "embedding": "-",
                    })
                    continue

                # Add to metadata database
                db.add_record(record)

                # Compute embedding
                try:
                    embedding = api.get_embedding_from_bytes(file_bytes, model_name)
                    emb_db.add_embedding(
                        image_hash=record.hash,
                        embedding=embedding,
                        model_name=model_name,
                        metadata={
                            "width": record.width,
                            "height": record.height,
                        }
                    )
                    embedding_status = "computed"
                except Exception as e:
                    embedding_status = f"error: {e}"

                result = {
                    "filename": uploaded_file.name,
                    "hash": record.hash[:16] + "...",
                    "dimensions": f"{record.width}x{record.height}",
                    "size": record.size,
                    "status": "added",
                    "embedding": embedding_status,
                }

                results.append(result)

            finally:
                # Clean up temp file
                os.unlink(tmp_path)

        except Exception as e:
            results.append({
                "filename": uploaded_file.name,
                "hash": "-",
                "dimensions": "-",
                "size": "-",
                "status": f"error: {e}",
                "embedding": "-",
            })

        progress_bar.progress((i + 1) / len(uploaded_files))

    status_text.text("Done!")

    # Display results table
    st.dataframe(
        results,
        column_config={
            "filename": "Filename",
            "hash": st.column_config.TextColumn("Hash", width="medium"),
            "dimensions": "Dimensions",
            "size": st.column_config.NumberColumn("Size (bytes)", format="%d"),
            "status": "Status",
            "embedding": "Embedding",
        },
        width="stretch"
    )

    # Show preview of uploaded images
    st.header("Preview")
    cols = st.columns(4)
    for i, uploaded_file in enumerate(uploaded_files):
        uploaded_file.seek(0)  # Reset file pointer
        with cols[i % 4]:
            st.image(uploaded_file, caption=uploaded_file.name, width="stretch")
