"""
Ingest Images Page

Scan directories or use config files to add images to the database.
"""
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import yaml

from src.storage.database import ImageDatabase
from src.storage.embedding_db import EmbeddingDatabase
from src.core.scanner import ImageScanner
from src.api.embedding_api import EmbeddingAPI, EmbeddingAPIError

# Configuration
DB_PATH = Path(__file__).parent.parent.parent / "data" / "images.db"
EMBEDDING_DB_PATH = Path(__file__).parent.parent.parent / "data" / "embeddings"
CONFIGS_DIR = Path(__file__).parent.parent.parent / "configs"

st.set_page_config(page_title="Ingest Images", page_icon="📂", layout="wide")

st.title("📂 Ingest Images")

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


# Main content - Tabs for different ingestion modes
tab1, tab2 = st.tabs(["📁 Single Folder", "📋 From Config"])

# ===== TAB 1: SINGLE FOLDER =====
with tab1:
    st.markdown("""
    Scan a directory for images and add them to the database.
    This will extract metadata and compute embeddings for all images.
    """)

    folder_path = st.text_input(
        "Folder Path",
        value="test_images",
        help="Path to the folder containing images",
        key="single_folder_path"
    )

    col1, col2 = st.columns(2)
    with col1:
        recursive = st.checkbox("Recursive (include subdirectories)", value=True, key="single_recursive")
    with col2:
        force_embed = st.checkbox("Force re-compute embeddings", value=False, key="single_force")

    compute_embeddings = st.checkbox("Compute embeddings", value=True, key="single_compute")

    if st.button("Start Ingestion", type="primary", key="single_start"):
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

                # Auto-reload cache to refresh index.json and database stats
                st.info("🔄 Reloading cache to update app state...")
                st.cache_resource.clear()
                st.cache_data.clear()


# ===== TAB 2: FROM CONFIG =====
with tab2:
    st.markdown("""
    Use a YAML configuration file to ingest multiple directories at once.
    This is useful for batch processing and monitoring workflows.
    """)

    # List available configs
    CONFIGS_DIR.mkdir(parents=True, exist_ok=True)
    config_files = list(CONFIGS_DIR.glob("*.yaml")) + list(CONFIGS_DIR.glob("*.yml"))

    if config_files:
        config_names = [f.name for f in config_files]
        selected_config = st.selectbox("Select Config File", config_names, key="config_select")
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
    custom_config = st.text_input("Custom Config Path", placeholder="configs/my-config.yaml", key="custom_config")

    col1, col2 = st.columns(2)
    with col1:
        force_embed_config = st.checkbox("Force re-compute embeddings", value=False, key="config_force")
    with col2:
        compute_embeddings_config = st.checkbox("Compute embeddings", value=True, key="config_compute")

    if st.button("Start Config Ingestion", type="primary", key="config_start"):
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
                    recursive_config = config.get("recursive", True)

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
                            elif recursive_config:
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

                    # Auto-reload cache to refresh index.json and database stats
                    st.info("🔄 Reloading cache to update app state...")
                    st.cache_resource.clear()
                    st.cache_data.clear()

            except Exception as e:
                st.error(f"Error processing config: {e}")
