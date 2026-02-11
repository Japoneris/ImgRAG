"""
Hash Search Page

Search for images by their SHA-256 hash - either by uploading an image
to compute its hash, or by entering a hash directly.
"""
import sys
import os
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from PIL import Image

from src.storage.database import ImageDatabase
from src.core.scanner import ImageScanner

# Configuration
DB_PATH = Path(__file__).parent.parent.parent / "data" / "images.db"
INDEX_PATH = Path(__file__).parent.parent.parent / "data" / "index.json"

st.set_page_config(page_title="Hash Search", page_icon="#️⃣", layout="wide")

st.title("Search by Hash")

st.markdown("""
Search for images using their SHA-256 hash. You can either:
- **Upload an image** to compute its hash and check if it exists in the database
- **Enter a hash directly** (full hash or prefix) to search
""")


@st.cache_resource
def get_database():
    """Initialize database connection."""
    return ImageDatabase(str(DB_PATH))


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


def get_filepath_for_hash(image_hash: str, index: dict, base_path: str) -> str:
    """Get full filepath from hash using index and base path."""
    relative_path = index.get(image_hash)
    if relative_path is None:
        return "Path not in index"
    if base_path:
        return str(Path(base_path) / relative_path)
    return relative_path


def make_file_link(filepath: str) -> str:
    """Create a clickable file:// link for a local path."""
    if filepath == "Path not in index":
        return filepath
    abs_path = Path(filepath).resolve()
    return f"[{filepath}](file://{abs_path})"


def display_result(record, index):
    """Display a single search result."""
    filepath = get_filepath_for_hash(record.hash, index, base_path)

    col1, col2 = st.columns([1, 2])

    with col1:
        if filepath != "Path not in index" and Path(filepath).exists():
            try:
                img = Image.open(filepath)
                st.image(img, width="stretch")
                
            except Exception:
                st.text("[Image unavailable]")
        else:
            st.text("[Image not found]")

    with col2:
        st.markdown(f"**Hash:** `{record.hash}`")
        st.markdown(f"**Dimensions:** {record.width} x {record.height}")
        st.markdown(f"**Size:** {record.size:,} bytes")
        st.markdown(f"**MIME Type:** {record.mimetype}")
        st.markdown(f"**Created:** {record.created_at or 'Unknown'}")
        st.markdown(f"**Ingested:** {record.ingested_at or 'Unknown'}")
        st.markdown(f"**Path:** {make_file_link(filepath)}")


db = get_database()
index, base_path = load_index()

# Search method selection
search_method = st.radio(
    "Search Method",
    ["Upload Image", "Enter Hash"],
    horizontal=True,
)

query_hash = None

if search_method == "Upload Image":
    uploaded_file = st.file_uploader(
        "Upload an image to compute its hash",
        type=["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff"],
    )

    if uploaded_file:
        col1, col2 = st.columns([1, 2])

        with col1:
            st.image(uploaded_file, caption="Uploaded Image", width="stretch")

        with col2:
            # Compute hash
            scanner = ImageScanner()
            file_bytes = uploaded_file.getvalue()

            import hashlib
            query_hash = hashlib.sha256(file_bytes).hexdigest()

            st.markdown(f"**Computed Hash:**")
            st.code(query_hash)

            # Check if exists
            record = db.get_by_hash(query_hash)
            if record:
                st.success("This image EXISTS in the database!")
            else:
                st.warning("This image is NOT in the database.")

else:  # Enter Hash
    hash_input = st.text_input(
        "Enter hash (full or prefix)",
        placeholder="e.g., abc123... or full 64-character hash",
    )

    if hash_input:
        query_hash = hash_input.strip().lower()

# Search and display results
if query_hash:
    st.divider()
    st.header("Search Results")

    # Try exact match first
    exact_match = db.get_by_hash(query_hash)

    if exact_match:
        st.subheader("Exact Match Found")
        display_result(exact_match, index)
    else:
        # Try prefix search
        prefix_matches = db.search_by_prefix(query_hash)

        if prefix_matches:
            st.subheader(f"Found {len(prefix_matches)} image(s) matching prefix")

            for i, record in enumerate(prefix_matches):
                with st.expander(f"Result {i+1}: {record.hash[:16]}...", expanded=(i == 0)):
                    display_result(record, index)
        else:
            st.info("No images found matching this hash or prefix.")
