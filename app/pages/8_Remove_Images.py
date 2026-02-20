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

PAGE_SIZE = 25

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

# Session state init
if 'selected_for_removal' not in st.session_state:
    st.session_state.selected_for_removal = set()
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
# Track last search context to reset page on change
if 'last_search_context' not in st.session_state:
    st.session_state.last_search_context = None

# Search method
tab_all, tab_hash, tab_path = st.tabs(["View All", "Search by Hash Prefix", "Search by Path"])

all_records = []
search_context = "none"

with tab_all:
    if st.button("Load all records"):
        with st.spinner("Loading all records..."):
            all_records = db.list_all()
        st.session_state["_all_records_cache"] = all_records
    elif "_all_records_cache" in st.session_state:
        all_records = st.session_state["_all_records_cache"]
    if all_records:
        st.info(f"Found {len(all_records)} images in database")
        search_context = "all"

with tab_hash:
    hash_prefix = st.text_input(
        "Enter hash prefix",
        placeholder="e.g., abc123...",
        help="Enter the beginning of the image hash",
    )
    hash_find_btn = st.button("Find", key="hash_find")
    search_context = f"prefix:{hash_prefix}:find={hash_find_btn}"
    if hash_find_btn:
        if not hash_prefix:
            st.warning("Enter a hash prefix first")
        else:
            all_records = db.search_by_prefix(hash_prefix.strip().lower())
            if all_records:
                st.success(f"Found {len(all_records)} matching image(s)")
            else:
                st.warning("No images found matching this prefix")

with tab_path:
    path_query = st.text_input(
        "Enter path substring",
        placeholder="e.g., /photos/2024 or vacation",
        help="Any part of the file path (case-insensitive)",
    )
    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        find_btn = st.button("Find", width="stretch")
        no_path_btn = st.button("Show images with no path", width="stretch")

    search_context = f"path:{path_query}:find={find_btn}:nopath={no_path_btn}"
    if no_path_btn:
        with st.spinner("Searching..."):
            candidates = db.list_all()
        all_records = [r for r in candidates if not index.get(r.hash, "")]
        if all_records:
            st.success(f"Found {len(all_records)} image(s) with no path")
        else:
            st.warning("All images have a path")
    elif find_btn:
        if not path_query:
            st.warning("Enter a path substring first")
        else:
            q = path_query.strip().lower()
            with st.spinner("Searching..."):
                candidates = db.list_all()
            all_records = [
                r for r in candidates
                if (rel := index.get(r.hash, ""))
                and (q in rel.lower() or (base_path and q in str(Path(base_path) / rel).lower()))
            ]
            if all_records:
                st.success(f"Found {len(all_records)} matching image(s)")
            else:
                st.warning("No images found matching this path")

# Reset to page 0 when search context changes
if search_context != st.session_state.last_search_context:
    st.session_state.current_page = 0
    st.session_state.last_search_context = search_context

# Display records and allow selection
if all_records:
    st.divider()

    st.header("Search results")

    # Sort controls
    sort_col1, sort_col2 = st.columns([2, 1])
    with sort_col1:
        sort_by = st.selectbox(
            "Sort by",
            ["Insertion order", "Hash", "Date (created)", "Date (ingested)", "Size", "Path"],
            key="sort_by",
        )
    with sort_col2:
        sort_asc = st.radio("Order", ["Ascending", "Descending"], horizontal=True, key="sort_order") == "Ascending"

    def record_sort_key(r):
        if sort_by == "Hash":
            return r.hash or ""
        elif sort_by == "Date (created)":
            return r.created_at or ""
        elif sort_by == "Date (ingested)":
            return r.ingested_at or ""
        elif sort_by == "Size":
            return r.size or 0
        elif sort_by == "Path":
            fp = index.get(r.hash, "")
            return str(Path(base_path) / fp) if fp and base_path else fp
        return ""  # Insertion order: no sort

    if sort_by != "Insertion order":
        all_records = sorted(all_records, key=record_sort_key, reverse=not sort_asc)

    total_pages = max(1, (len(all_records) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = st.session_state.current_page

    st.subheader(f"Select Images to Remove — page {page + 1} / {total_pages}")

    # Pagination controls (top)
    col_prev, col_info, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("← Previous", disabled=page == 0, key="prev_top"):
            st.session_state.current_page -= 1
            st.rerun()
    with col_info:
        start = page * PAGE_SIZE + 1
        end = min((page + 1) * PAGE_SIZE, len(all_records))
        st.caption(f"Showing records {start}–{end} of {len(all_records)}")
    with col_next:
        if st.button("Next →", disabled=page >= total_pages - 1, key="next_top"):
            st.session_state.current_page += 1
            st.rerun()

    # Slice records for current page
    page_records = all_records[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    # Bulk selection helpers — must be ABOVE the records loop so checkbox
    # widget state is set before the checkboxes are instantiated
    if len(page_records) > 1:
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Select page"):
                for record in page_records:
                    st.session_state.selected_for_removal.add(record.hash)
                    st.session_state[f"remove_checkbox_{record.hash}"] = True
                st.rerun()
        with col2:
            if st.button("Deselect page"):
                for record in page_records:
                    st.session_state.selected_for_removal.discard(record.hash)
                    st.session_state[f"remove_checkbox_{record.hash}"] = False
                st.rerun()
        with col3:
            st.info(f"{len(st.session_state.selected_for_removal)} selected total")

    # Display as cards with selection
    for i, record in enumerate(page_records):
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
                show_key = f"show_thumb_{record.hash}"
                if st.button("Show thumbnail", key=f"btn_thumb_{record.hash}"):
                    st.session_state[show_key] = True
                if st.session_state.get(show_key):
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

    # Pagination controls (bottom)
    st.divider()
    col_prev, col_info, col_next = st.columns([1, 3, 1])
    with col_prev:
        if st.button("← Previous", disabled=page == 0, key="prev_bottom"):
            st.session_state.current_page -= 1
            st.rerun()
    with col_info:
        st.caption(f"Page {page + 1} of {total_pages}")
    with col_next:
        if st.button("Next →", disabled=page >= total_pages - 1, key="next_bottom"):
            st.session_state.current_page += 1
            st.rerun()

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

                # Clear selection, reset page and cached record list
                st.session_state.selected_for_removal.clear()
                st.session_state.current_page = 0
                st.session_state.pop("_all_records_cache", None)

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
