"""
Index Management Page

Manage the image database: ingest folders, rebuild index, and view statistics.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import yaml
from tqdm import tqdm

from src.storage.database import ImageDatabase
from src.storage.embedding_db import EmbeddingDatabase
from src.core.scanner import ImageScanner
from src.api.embedding_api import EmbeddingAPI, EmbeddingAPIError

# Configuration
DB_PATH = Path(__file__).parent.parent.parent / "data" / "images.db"
EMBEDDING_DB_PATH = Path(__file__).parent.parent.parent / "data" / "embeddings"
INDEX_PATH = Path(__file__).parent.parent.parent / "data" / "index.json"
CONFIGS_DIR = Path(__file__).parent.parent.parent / "configs"

st.set_page_config(page_title="Index Management", page_icon="⚙️", layout="wide")

st.title("Index Management")

# Sidebar settings
st.sidebar.header("Settings")
api_url = st.sidebar.text_input(
    "Embedding API URL",
    value=os.environ.get("EMBEDDING_API_URL", "http://localhost:8000"),
)
api_key = st.sidebar.text_input(
    "API Key (optional)",
    value=os.environ.get("EMBEDDING_API_KEY", ""),
    type="password",
)
available_models = [
    m.strip()
    for m in os.environ.get("EMBEDDING_MODELS", "dinov2-small,default").split(",")
    if m.strip()
]
model_name = st.sidebar.selectbox("Model", options=available_models)


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


def ingest_single_file(
    filepath: Path,
    scanner: ImageScanner,
    db: ImageDatabase,
    embed_db: EmbeddingDatabase,
    api: EmbeddingAPI,
    model: str,
    force_embed: bool,
) -> tuple[str, str]:
    """
    Ingest a single image file.

    Returns:
        tuple of (status, message) where status is 'added', 'skipped', or 'error'
    """
    try:
        file_hash = scanner.compute_hash(filepath)

        # Check metadata
        is_new = False
        if db.get_by_hash(file_hash):
            pass  # metadata already present
        else:
            record = scanner.extract_metadata(filepath)
            db.add_record(record)
            is_new = True

        # Check embedding
        embed_ok = False
        embed_msg = ""
        if api is not None and embed_db is not None:
            existing = embed_db.get_embedding(file_hash, model)
            if existing and not force_embed:
                embed_ok = True
                embed_msg = "embedding exists"
            else:
                try:
                    embedding = api.get_embedding(filepath, model=model)
                    metadata = {
                        "filepath": str(filepath.absolute()),
                        "dimensions": len(embedding),
                    }
                    embed_db.add_embedding(file_hash, embedding, model, metadata)
                    embed_ok = True
                    embed_msg = "embedding computed"
                except EmbeddingAPIError as e:
                    embed_msg = f"embedding failed: {e}"

        if is_new:
            return "added", embed_msg
        else:
            return "skipped", embed_msg

    except Exception as e:
        return "error", str(e)


# Create tabs for different operations
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📂 Ingest Folder",
    "📋 Ingest from Config",
    "🔄 Rebuild Index",
    "📊 Database Status",
    "🗑️ Remove Images"
])

# ============================================================================
# TAB 1: Ingest Folder
# ============================================================================
with tab1:
    st.header("Ingest Images from Folder")
    st.markdown("""
    Scan a directory for images and add them to the database.
    This will extract metadata and compute embeddings for all images.
    """)

    folder_path = st.text_input(
        "Folder Path",
        value="test_images",
        help="Path to the folder containing images",
    )

    col1, col2 = st.columns(2)
    with col1:
        recursive = st.checkbox("Recursive (include subdirectories)", value=True)
    with col2:
        force_embed = st.checkbox("Force re-compute embeddings", value=False)

    compute_embeddings = st.checkbox("Compute embeddings", value=True)

    if st.button("Start Ingestion", type="primary"):
        path = Path(folder_path)

        if not path.exists():
            st.error(f"Path does not exist: {path}")
        elif not path.is_dir():
            st.error(f"Path is not a directory: {path}")
        else:
            db, emb_db = get_databases()
            scanner = ImageScanner()

            # Check API if embeddings requested
            api = None
            if compute_embeddings:
                try:
                    api = get_embedding_api()
                    if not api.health_check():
                        st.error("Embedding API is not available. Proceeding without embeddings.")
                        api = None
                except Exception as e:
                    st.error(f"Could not connect to embedding API: {e}")
                    api = None

            # Find all images
            with st.spinner("Scanning directory..."):
                if recursive:
                    images = [f for f in path.rglob("*") if f.is_file() and scanner.is_image(f)]
                else:
                    images = [f for f in path.glob("*") if f.is_file() and scanner.is_image(f)]

            st.info(f"Found {len(images)} images in {path}")

            if images:
                # Process images
                progress_bar = st.progress(0)
                status_text = st.empty()

                added = 0
                skipped = 0
                errors = 0

                results_placeholder = st.empty()

                for i, filepath in enumerate(images):
                    status_text.text(f"Processing {filepath.name}...")

                    status, message = ingest_single_file(
                        filepath, scanner, db, emb_db, api, model_name, force_embed
                    )

                    if status == "added":
                        added += 1
                    elif status == "skipped":
                        skipped += 1
                    else:
                        errors += 1

                    progress_bar.progress((i + 1) / len(images))

                    # Update live stats
                    results_placeholder.metric(
                        "Progress",
                        f"{i + 1} / {len(images)}",
                        f"✅ {added} added, ⏭️ {skipped} skipped, ❌ {errors} errors"
                    )

                status_text.text("Done!")

                # Final summary
                st.success("Ingestion complete!")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Added", added)
                with col2:
                    st.metric("Skipped (duplicates)", skipped)
                with col3:
                    st.metric("Errors", errors)

                st.info(f"Total in metadata DB: {db.count()}")
                if api and emb_db:
                    st.info(f"Total embeddings ({model_name}): {emb_db.count(model_name)}")

# ============================================================================
# TAB 2: Ingest from Config
# ============================================================================
with tab2:
    st.header("Ingest from YAML Config")
    st.markdown("""
    Use a YAML configuration file to ingest multiple directories at once.
    This is useful for batch processing and monitoring workflows.
    """)

    # List available configs
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    config_files = list(CONFIGS_DIR.glob("*.yaml")) + list(CONFIGS_DIR.glob("*.yml"))

    if config_files:
        config_names = [f.name for f in config_files]
        selected_config = st.selectbox("Select Config File", config_names)
        config_path = CONFIGS_DIR / selected_config

        # Show config contents
        with st.expander("View Config Contents"):
            try:
                with open(config_path) as f:
                    config_data = yaml.safe_load(f)
                st.code(yaml.dump(config_data, default_flow_style=False), language="yaml")
            except Exception as e:
                st.error(f"Error reading config: {e}")
    else:
        st.info("No config files found in configs/")
        config_path = None

    # Config format help
    with st.expander("Config File Format"):
        st.markdown("""
        ```yaml
        # List of directories to scan
        paths:
          - /path/to/images1
          - /path/to/images2

        # Whether to scan subdirectories (default: true)
        recursive: true
        ```
        """)

    # Or provide custom path
    st.markdown("**Or provide a custom config path:**")
    custom_config = st.text_input("Custom Config Path", placeholder="configs/my-config.yaml")

    col1, col2 = st.columns(2)
    with col1:
        force_embed_config = st.checkbox("Force re-compute embeddings", value=False, key="force_config")
    with col2:
        compute_embeddings_config = st.checkbox("Compute embeddings", value=True, key="embed_config")

    if st.button("Start Config Ingestion", type="primary"):
        # Determine which config to use
        final_config_path = None
        if custom_config:
            final_config_path = Path(custom_config)
        elif config_path:
            final_config_path = config_path

        if not final_config_path:
            st.error("Please select or provide a config file")
        elif not final_config_path.exists():
            st.error(f"Config file not found: {final_config_path}")
        else:
            try:
                with open(final_config_path) as f:
                    config = yaml.safe_load(f)

                if not config or "paths" not in config:
                    st.error("Invalid config: must contain 'paths' key")
                else:
                    db, emb_db = get_databases()
                    scanner = ImageScanner()

                    # Check API if embeddings requested
                    api = None
                    if compute_embeddings_config:
                        try:
                            api = get_embedding_api()
                            if not api.health_check():
                                st.warning("Embedding API is not available. Proceeding without embeddings.")
                                api = None
                        except Exception as e:
                            st.warning(f"Could not connect to embedding API: {e}")
                            api = None

                    paths = [Path(p) for p in config.get("paths", [])]
                    recursive = config.get("recursive", True)

                    total_added = 0
                    total_skipped = 0
                    total_errors = 0

                    for dirpath in paths:
                        if not dirpath.exists():
                            st.warning(f"Path does not exist: {dirpath}")
                            continue

                        st.subheader(f"Processing: {dirpath}")

                        # Find images
                        with st.spinner(f"Scanning {dirpath}..."):
                            if dirpath.is_file():
                                images = [dirpath] if scanner.is_image(dirpath) else []
                            elif recursive:
                                images = [f for f in dirpath.rglob("*") if f.is_file() and scanner.is_image(f)]
                            else:
                                images = [f for f in dirpath.glob("*") if f.is_file() and scanner.is_image(f)]

                        st.info(f"Found {len(images)} images in {dirpath}")

                        if images:
                            progress_bar = st.progress(0)
                            status_text = st.empty()

                            added = 0
                            skipped = 0
                            errors = 0

                            for i, filepath in enumerate(images):
                                status_text.text(f"Processing {filepath.name}...")

                                status, message = ingest_single_file(
                                    filepath, scanner, db, emb_db, api, model_name, force_embed_config
                                )

                                if status == "added":
                                    added += 1
                                elif status == "skipped":
                                    skipped += 1
                                else:
                                    errors += 1

                                progress_bar.progress((i + 1) / len(images))

                            status_text.text(f"Done with {dirpath}")

                            total_added += added
                            total_skipped += skipped
                            total_errors += errors

                            st.write(f"✅ {added} added, ⏭️ {skipped} skipped, ❌ {errors} errors")

                    st.success("Config ingestion complete!")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Total Added", total_added)
                    with col2:
                        st.metric("Total Skipped", total_skipped)
                    with col3:
                        st.metric("Total Errors", total_errors)

                    st.info(f"Total in metadata DB: {db.count()}")
                    if api and emb_db:
                        st.info(f"Total embeddings ({model_name}): {emb_db.count(model_name)}")

            except Exception as e:
                st.error(f"Error processing config: {e}")

# ============================================================================
# TAB 3: Rebuild Index
# ============================================================================
with tab3:
    st.header("Rebuild Hash Index")
    st.markdown("""
    Rebuild the hash→filepath mapping index. This index allows the system to
    quickly locate image files by their hash without scanning the filesystem.

    Run this after moving files or if the index becomes out of sync.
    """)

    index_folder_path = st.text_input(
        "Folder to Index",
        value="test_images",
        help="Root directory to scan for images",
        key="index_folder",
    )

    col1, col2 = st.columns(2)
    with col1:
        index_recursive = st.checkbox("Recursive", value=True, key="index_recursive")
    with col2:
        index_relative = st.checkbox(
            "Store relative paths",
            value=True,
            help="Store paths relative to the scanned folder",
            key="index_relative"
        )

    output_path = st.text_input(
        "Output Index Path",
        value=str(INDEX_PATH),
        help="Where to save the index JSON file",
    )

    if st.button("Rebuild Index", type="primary"):
        path = Path(index_folder_path)

        if not path.exists():
            st.error(f"Path does not exist: {path}")
        elif not path.is_dir():
            st.error(f"Path is not a directory: {path}")
        else:
            scanner = ImageScanner()

            with st.spinner(f"Scanning {path} and building index..."):
                try:
                    index = scanner.build_index(
                        path,
                        output=output_path,
                        relative=index_relative
                    )

                    st.success(f"Index rebuilt successfully!")
                    st.info(f"Indexed {len(index)} images")
                    st.info(f"Saved to: {output_path}")

                    # Show sample entries
                    with st.expander("Sample Index Entries (first 10)"):
                        sample = dict(list(index.items())[:10])
                        for hash_val, filepath in sample.items():
                            st.text(f"{hash_val[:16]}... → {filepath}")

                except Exception as e:
                    st.error(f"Error rebuilding index: {e}")

# ============================================================================
# TAB 4: Database Status
# ============================================================================
with tab4:
    st.header("Database Status")

    db, emb_db = get_databases()

    # Metadata database stats
    st.subheader("Metadata Database")
    col1, col2 = st.columns(2)

    with col1:
        st.metric("Total Images", db.count())
        st.info(f"Database: {DB_PATH}")

    with col2:
        # Show disk size
        if DB_PATH.exists():
            size_mb = DB_PATH.stat().st_size / (1024 * 1024)
            st.metric("Database Size", f"{size_mb:.2f} MB")

    # Embedding database stats
    st.subheader("Embedding Database")

    try:
        models = emb_db.list_models()
        if models:
            cols = st.columns(len(models))
            for i, model in enumerate(models):
                with cols[i]:
                    count = emb_db.count(model)
                    st.metric(f"Model: {model}", count)
        else:
            st.info("No embeddings stored yet")

        st.info(f"Database: {EMBEDDING_DB_PATH}")

    except Exception as e:
        st.error(f"Error accessing embedding database: {e}")

    # Index status
    st.subheader("Hash Index")

    if INDEX_PATH.exists():
        try:
            import json
            with open(INDEX_PATH) as f:
                index_data = json.load(f)

            images_count = len(index_data.get("images", {}))
            meta = index_data.get("_meta", {})

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Indexed Images", images_count)
            with col2:
                st.metric("Index Type", "Relative" if meta.get("relative") else "Absolute")

            if meta.get("base_path"):
                st.info(f"Base path: {meta['base_path']}")

            st.info(f"Index file: {INDEX_PATH}")

        except Exception as e:
            st.error(f"Error reading index: {e}")
    else:
        st.warning("Index file not found. Run 'Rebuild Index' to create it.")

    # Comparison
    st.subheader("Database Comparison")

    metadata_count = db.count()

    try:
        models = emb_db.list_models()
        if models:
            for model in models:
                embed_count = emb_db.count(model)

                if embed_count < metadata_count:
                    diff = metadata_count - embed_count
                    st.warning(
                        f"⚠️ Model '{model}': {diff} images have metadata but no embedding"
                    )
                elif embed_count > metadata_count:
                    diff = embed_count - metadata_count
                    st.warning(
                        f"⚠️ Model '{model}': {diff} embeddings have no metadata record"
                    )
                else:
                    st.success(f"✅ Model '{model}': All {metadata_count} images have embeddings")
    except Exception as e:
        st.error(f"Error comparing databases: {e}")

    # Refresh button
    if st.button("Refresh Status"):
        st.cache_resource.clear()
        st.rerun()

# ============================================================================
# TAB 5: Remove Images
# ============================================================================
with tab5:
    st.header("Remove Images from Database")
    st.markdown("""
    Selectively remove images from the metadata database and/or embedding database.
    You can search by hash prefix or view all images.
    """)

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
