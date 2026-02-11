"""
Image Database - Streamlit App

Root page providing navigation and system status.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st
from src.storage.database import ImageDatabase
from src.storage.embedding_db import EmbeddingDatabase

# Configuration
DB_PATH = Path(__file__).parent.parent / "data" / "images.db"
EMBEDDING_DB_PATH = Path(__file__).parent.parent / "data" / "embeddings"

st.set_page_config(
    page_title="Image Database",
    page_icon="🖼️",
    layout="wide"
)

st.title("Image Database System")

st.markdown("""
Welcome to the Image Database System. This application allows you to:

- **Upload Images**: Add new images to the database with automatic embedding generation
- **Search Images**: Find similar images using vector similarity search

Use the sidebar to navigate between pages.
""")

# Display system status
st.header("System Status")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Metadata Database")
    try:
        db = ImageDatabase(str(DB_PATH))
        records = db.list_all()
        st.metric("Total Images", len(records))
        st.success(f"Connected: {DB_PATH}")
    except Exception as e:
        st.error(f"Error connecting to database: {e}")

with col2:
    st.subheader("Embedding Database")
    try:
        emb_db = EmbeddingDatabase(str(EMBEDDING_DB_PATH))
        models = emb_db.list_models()
        st.metric("Models", len(models))
        if models:
            st.info(f"Models: {', '.join(models)}")
        st.success(f"Connected: {EMBEDDING_DB_PATH}")
    except Exception as e:
        st.error(f"Error connecting to embedding database: {e}")

# Configuration info
st.header("Configuration")
st.markdown("""
**Environment Variables:**
- `EMBEDDING_API_URL`: URL of the embedding API server
- `EMBEDDING_MODEL`: Model to use for embeddings
- `EMBEDDING_API_KEY`: API key (optional)
""")
