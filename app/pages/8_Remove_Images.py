"""
Remove Images Page

Selectively remove images from the metadata and embedding databases.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from src.storage.database import ImageDatabase
from src.storage.embedding_db import EmbeddingDatabase

# Configuration
DB_PATH = Path(__file__).parent.parent.parent / "data" / "images.db"
EMBEDDING_DB_PATH = Path(__file__).parent.parent.parent / "data" / "embeddings"
INDEX_PATH = Path(__file__).parent.parent.parent / "data" / "index.json"

st.set_page_config(page_title="Remove Images", page_icon="🗑️", layout="wide")

st.title("🗑️ Remove Images from Database")

st.markdown("""
Selectively remove images from the metadata database and/or embedding database.
You can search by hash prefix or view all images.
""")


@st.cache_resource
def get_databases():
    """Initialize database connections."""
    db = ImageDatabase(str(DB_PATH))
    emb_db = EmbeddingDatabase(str(EMBEDDING_DB_PATH))
    return db, emb_db


db, emb_db = get_databases()

# Load index for displaying file paths
import json
index = {}
base_path = ""
if INDEX_PATH.exists():
    try:
        with open(INDEX_PATH) as f:
            index_data = json.load(f)
            index = index_data.get("images", {})
            meta = index_data.get("_meta", {})
            base_path = meta.get("base_path", "")
    except Exception:
        pass

# Search method
search_mode = st.radio(
    "Search Mode",
    ["View All", "Search by Hash Prefix"],
    horizontal=True,
)

records_to_display = []

if search_mode == "View All":
    with st.spinner("Loading all records..."):
        records_to_display = db.list_all()
    st.info(f"Found {len(records_to_display)} images in database")

else:  # Search by Hash Prefix
    hash_prefix = st.text_input(
        "Enter hash prefix",
        placeholder="e.g., abc123...",
        help="Enter the beginning of the image hash"
    )

    if hash_prefix:
        records_to_display = db.search_by_prefix(hash_prefix.strip().lower())
        if records_to_display:
            st.success(f"Found {len(records_to_display)} matching image(s)")
        else:
            st.warning("No images found matching this prefix")

# Display records and allow selection
if records_to_display:
    st.divider()
    st.subheader("Select Images to Remove")

    # Create a table with checkboxes
    selected_hashes = []

    # Use session state to track selections
    if 'selected_for_removal' not in st.session_state:
        st.session_state.selected_for_removal = set()

    # Display as cards with selection
    for i, record in enumerate(records_to_display):
        # Get filepath
        filepath = index.get(record.hash, "Path not in index")
        if filepath != "Path not in index" and base_path:
            filepath = str(Path(base_path) / filepath)

        # Create expandable card for each image
        with st.expander(
            f"{'✓ ' if record.hash in st.session_state.selected_for_removal else ''}Hash: {record.hash[:16]}... | {record.width}x{record.height} | {filepath[:50]}{'...' if len(str(filepath)) > 50 else ''}",
            expanded=False
        ):
            col1, col2 = st.columns([1, 2])

            with col1:
                # Try to display thumbnail
                if filepath != "Path not in index" and Path(filepath).exists():
                    try:
                        from PIL import Image
                        img = Image.open(filepath)
                        st.image(img, width=200)
                    except Exception:
                        st.text("[Image unavailable]")
                else:
                    st.text("[Image not found on disk]")

            with col2:
                st.markdown(f"**Hash:** `{record.hash}`")
                st.markdown(f"**Dimensions:** {record.width} x {record.height}")
                st.markdown(f"**Size:** {record.size:,} bytes")
                st.markdown(f"**MIME Type:** {record.mimetype}")
                st.markdown(f"**Created:** {record.created_at or 'Unknown'}")
                st.markdown(f"**Ingested:** {record.ingested_at or 'Unknown'}")
                st.markdown(f"**Path:** {filepath}")

                # Check if embeddings exist
                models_with_embeddings = []
                try:
                    all_models = emb_db.list_models()
                    for model in all_models:
                        if emb_db.get_embedding(record.hash, model):
                            models_with_embeddings.append(model)
                    if models_with_embeddings:
                        st.markdown(f"**Embeddings:** {', '.join(models_with_embeddings)}")
                    else:
                        st.markdown("**Embeddings:** None")
                except Exception:
                    st.markdown("**Embeddings:** Unknown")

            # Selection checkbox
            is_selected = st.checkbox(
                "Select for removal",
                value=record.hash in st.session_state.selected_for_removal,
                key=f"remove_checkbox_{record.hash}"
            )

            if is_selected:
                st.session_state.selected_for_removal.add(record.hash)
            else:
                st.session_state.selected_for_removal.discard(record.hash)

    # Show selection summary
    if st.session_state.selected_for_removal:
        st.divider()
        st.subheader("Removal Options")

        st.warning(f"⚠️ {len(st.session_state.selected_for_removal)} image(s) selected for removal")

        # Options for what to remove
        col1, col2 = st.columns(2)
        with col1:
            remove_metadata = st.checkbox("Remove from metadata database", value=True)
        with col2:
            remove_embeddings = st.checkbox("Remove from embedding database", value=True)

        if not remove_metadata and not remove_embeddings:
            st.info("Select at least one option to proceed with removal")
        else:
            # Show what will be removed
            st.markdown("**Will remove:**")
            removal_summary = []
            if remove_metadata:
                removal_summary.append("- Metadata records (image info, dimensions, timestamps)")
            if remove_embeddings:
                removal_summary.append("- All embeddings for selected images (all models)")
            for item in removal_summary:
                st.markdown(item)

            st.error("⚠️ **Warning:** This action cannot be undone!")

            # Confirmation
            confirm = st.text_input(
                f"Type 'DELETE {len(st.session_state.selected_for_removal)}' to confirm removal",
                placeholder=f"DELETE {len(st.session_state.selected_for_removal)}"
            )

            if st.button("🗑️ Remove Selected Images", type="primary", disabled=confirm != f"DELETE {len(st.session_state.selected_for_removal)}"):
                progress_bar = st.progress(0)
                status_text = st.empty()

                removed_metadata = 0
                removed_embeddings = 0
                errors = 0

                hashes_to_remove = list(st.session_state.selected_for_removal)

                for i, image_hash in enumerate(hashes_to_remove):
                    status_text.text(f"Removing {image_hash[:16]}...")

                    try:
                        # Remove metadata
                        if remove_metadata:
                            if db.delete_by_hash(image_hash):
                                removed_metadata += 1

                        # Remove embeddings
                        if remove_embeddings:
                            try:
                                all_models = emb_db.list_models()
                                for model in all_models:
                                    emb_db.delete_embedding(image_hash, model)
                                removed_embeddings += 1
                            except Exception:
                                pass  # Embedding might not exist

                    except Exception as e:
                        st.error(f"Error removing {image_hash[:16]}: {e}")
                        errors += 1

                    progress_bar.progress((i + 1) / len(hashes_to_remove))

                status_text.text("Removal complete!")

                # Clear selection
                st.session_state.selected_for_removal.clear()

                # Show results
                st.success("✅ Removal complete!")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Metadata Removed", removed_metadata if remove_metadata else "N/A")
                with col2:
                    st.metric("Embeddings Removed", removed_embeddings if remove_embeddings else "N/A")
                with col3:
                    st.metric("Errors", errors)

                # Refresh the page
                st.cache_resource.clear()
                st.rerun()

    # Bulk selection helpers
    if records_to_display and len(records_to_display) > 1:
        st.divider()
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Select All"):
                for record in records_to_display:
                    st.session_state.selected_for_removal.add(record.hash)
                st.rerun()
        with col2:
            if st.button("Deselect All"):
                st.session_state.selected_for_removal.clear()
                st.rerun()
        with col3:
            st.info(f"{len(st.session_state.selected_for_removal)} selected")
