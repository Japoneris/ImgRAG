"""
Search Images Page

Allows users to search for similar images using vector similarity.
"""
import sys
import os
from pathlib import Path
import json
from dotenv import load_dotenv

load_dotenv()
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
INDEX_PATH = Path(__file__).parent.parent.parent / "data" / "index.json"

st.set_page_config(page_title="Search Images", page_icon="🔍", layout="wide")

st.title("Search Images")

# Embedding API configuration
st.sidebar.header("Search Settings")
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
n_results = st.sidebar.slider("Number of results", min_value=1, max_value=50, value=10)


@st.cache_resource
def get_databases():
    """Initialize database connections."""
    db = ImageDatabase(str(DB_PATH))
    emb_db = EmbeddingDatabase(str(EMBEDDING_DB_PATH))
    return db, emb_db


@st.cache_data
def load_index():
    """Load hash-to-filepath index and base path."""
    if INDEX_PATH.exists():
        with open(INDEX_PATH, "r") as f:
            data = json.load(f)
            images = data.get("images", {})
            meta = data.get("_meta", {})
            base_path = meta.get("base_path", "")
            return images, base_path
    return {}, ""


def get_embedding_api():
    """Create embedding API client."""
    return EmbeddingAPI(
        base_url=api_url,
        api_key=api_key if api_key else None,
    )


def get_filepath_for_hash(image_hash: str, index: dict, base_path: str) -> str:
    """Get full filepath from hash using index and base path."""
    relative_path = index.get(image_hash)
    if relative_path is None:
        return "Path not in index"
    if base_path:
        return str(Path(base_path) / relative_path)
    return relative_path


def make_file_link(filepath: str) -> str:
    """Create a clickable file:// markdown link for a local path."""
    if filepath == "Path not in index":
        return filepath
    abs_path = Path(filepath).resolve()
    return f"[{filepath}](file://{abs_path})"


def make_file_url(filepath: str) -> str:
    """Create a file:// URL for a local path."""
    if filepath == "Path not in index":
        return ""
    abs_path = Path(filepath).resolve()
    return f"file://{abs_path}"


# Search methods
search_method = st.radio(
    "Search Method",
    ["Upload Image", "Select from Database"],
    horizontal=True,
)

db, emb_db = get_databases()
index, base_path = load_index()

query_embedding = None
query_image = None

if search_method == "Upload Image":
    uploaded_file = st.file_uploader(
        "Upload an image to search",
        type=["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff"],
    )

    if uploaded_file:
        query_image = Image.open(uploaded_file)
        st.image(query_image, caption="Query Image", width=300)

        # Compute embedding
        try:
            api = get_embedding_api()
            if not api.health_check():
                st.error("Embedding API is not available.")
            else:
                file_bytes = uploaded_file.getvalue()
                with st.spinner("Computing embedding..."):
                    query_embedding = api.get_embedding_from_bytes(file_bytes, model_name)
                st.success("Embedding computed!")
        except Exception as e:
            st.error(f"Error computing embedding: {e}")

else:  # Select from Database
    # Get all records
    records = db.list_all()

    if not records:
        st.warning("No images in database. Upload some images first.")
    else:
        # Create selection options
        options = {}
        for record in records:
            filepath = get_filepath_for_hash(record.hash, index, base_path)
            label = f"{record.hash[:12]}... ({record.width}x{record.height}) - {filepath}"
            options[label] = record.hash

        selected = st.selectbox("Select an image", options.keys())

        if selected:
            selected_hash = options[selected]

            # Try to load and display the image
            filepath = get_filepath_for_hash(selected_hash, index, base_path)
            if filepath != "Path not in index" and Path(filepath).exists():
                query_image = Image.open(filepath)
                st.image(query_image, caption=f"Query: {selected_hash[:12]}...", width=300)

            # Get existing embedding
            existing_embedding = emb_db.get_embedding(selected_hash, model_name)
            if existing_embedding:
                query_embedding = existing_embedding
                st.success("Using stored embedding")
            else:
                st.warning(f"No embedding found for model '{model_name}'")

                # Option to compute embedding
                if filepath != "Path not in index" and Path(filepath).exists():
                    if st.button("Compute Embedding"):
                        try:
                            api = get_embedding_api()
                            with st.spinner("Computing embedding..."):
                                query_embedding = api.get_embedding(filepath, model_name)
                            st.success("Embedding computed!")
                        except Exception as e:
                            st.error(f"Error computing embedding: {e}")

# Search and display results
if query_embedding:
    st.header("Search Results")
    print("Model", model_name)
    print("n", n_results)
    print("query", query_embedding)
    with st.spinner("Searching..."):
        results = emb_db.search_similar(query_embedding, model_name, n_results)

    if not results:
        st.info("No similar images found.")
    else:
        # Display results in a grid
        for i in range(0, len(results), 4):
            cols = st.columns(4)
            for j, col in enumerate(cols):
                if i + j < len(results):
                    image_hash, distance = results[i + j]
                    filepath = get_filepath_for_hash(image_hash, index, base_path)

                    with col:
                        # Try to display image
                        if filepath != "Path not in index" and Path(filepath).exists():
                            try:
                                img = Image.open(filepath)
                                st.image(img, width="stretch")
                            except Exception:
                                st.text("[Image unavailable]")
                        else:
                            st.text("[Image not found]")

                        st.caption(f"Hash: {image_hash[:12]}...")
                        st.caption(f"Distance: {distance:.4f}")
                        st.markdown(f"Path: {make_file_link(filepath)}", unsafe_allow_html=False)

        # Also show as table
        st.subheader("Results Table")
        table_data = []
        for image_hash, distance in results:
            record = db.get_by_hash(image_hash)
            filepath = get_filepath_for_hash(image_hash, index, base_path)
            table_data.append({
                "Hash": image_hash[:16] + "...",
                "Distance": f"{distance:.4f}",
                "Dimensions": f"{record.width}x{record.height}" if record else "-",
                "Size": record.size if record else "-",
                "Path": filepath,
                "Open": make_file_url(filepath),
            })

        st.dataframe(
            table_data,
            width="stretch",
            column_config={
                "Open": st.column_config.LinkColumn("Open", display_text="Open"),
            },
        )
