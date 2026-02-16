"""
Database Status Page

View statistics and analyze database coverage.
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

st.set_page_config(page_title="Database Status", page_icon="📊", layout="wide")

# Sidebar with cache reload button
st.sidebar.markdown("---")

st.title("📊 Database Status")


@st.cache_resource
def get_databases():
    """Initialize database connections."""
    db = ImageDatabase(str(DB_PATH))
    emb_db = EmbeddingDatabase(str(EMBEDDING_DB_PATH))
    return db, emb_db


db, emb_db = get_databases()

# Metadata database stats
st.header("Metadata Database")
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
st.header("Embedding Database")

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
st.header("Hash Index")

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
st.header("Database Comparison")

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

# Index Coverage Analysis
st.header("Index Coverage Analysis")
st.markdown("""
Check which images in the database are not present in the index file.
Images not in the index may not be quickly locatable by file path.
""")

if INDEX_PATH.exists():
    try:
        import json
        with open(INDEX_PATH) as f:
            index_data = json.load(f)

        index_hashes = set(index_data.get("images", {}).keys())

        # Get all hashes from metadata DB
        all_records = db.list_all()
        metadata_hashes = set(record.hash for record in all_records)

        # Find hashes not in index
        missing_from_index = metadata_hashes - index_hashes

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("In Metadata DB", len(metadata_hashes))
        with col2:
            st.metric("In Index", len(index_hashes))
        with col3:
            if missing_from_index:
                st.metric("Not in Index", len(missing_from_index), delta=f"-{len(missing_from_index)}", delta_color="inverse")
            else:
                st.metric("Not in Index", 0, delta="✓")

        # Check for each embedding model
        try:
            models = emb_db.list_models()
            if models:
                st.markdown("**By Embedding Model:**")
                for model in models:
                    # Get all embeddings for this model efficiently
                    all_embeddings = emb_db.get_all_embeddings(model)
                    embedding_hashes = set(all_embeddings.keys())
                    missing_embeddings_from_index = embedding_hashes - index_hashes

                    if missing_embeddings_from_index:
                        st.warning(
                            f"⚠️ Model '{model}': {len(missing_embeddings_from_index)} embeddings not in index"
                        )
                    else:
                        st.success(f"✅ Model '{model}': All embeddings are indexed")
        except Exception as e:
            st.warning(f"Could not check embedding coverage: {e}")

        # Show details if requested
        if missing_from_index:
            with st.expander(f"📋 View {len(missing_from_index)} Missing Images", expanded=False):
                st.markdown("**Images in metadata database but not in index:**")

                # Create a dataframe for better display
                missing_records = [r for r in all_records if r.hash in missing_from_index]

                if missing_records:
                    st.markdown(f"Showing {len(missing_records)} records:")

                    # Display in a table format
                    for i, record in enumerate(missing_records[:100], 1):  # Limit to first 100
                        with st.container():
                            col1, col2 = st.columns([1, 3])
                            with col1:
                                st.code(f"{i}. {record.hash[:16]}...")
                            with col2:
                                # Check which models have embeddings
                                has_embeddings = []
                                try:
                                    for model in emb_db.list_models():
                                        if emb_db.get_embedding(record.hash, model):
                                            has_embeddings.append(model)
                                except Exception:
                                    pass

                                info_text = f"{record.width}x{record.height} | {record.size:,} bytes | {record.mimetype}"
                                if has_embeddings:
                                    info_text += f" | Embeddings: {', '.join(has_embeddings)}"
                                else:
                                    info_text += " | No embeddings"
                                st.text(info_text)

                    if len(missing_records) > 100:
                        st.info(f"Showing first 100 of {len(missing_records)} records")

                    # Export option
                    st.markdown("**Export missing hashes:**")
                    export_text = "\n".join(sorted(missing_from_index))
                    st.download_button(
                        label="Download Missing Hashes (TXT)",
                        data=export_text,
                        file_name="missing_from_index.txt",
                        mime="text/plain"
                    )
        else:
            st.success("✅ All metadata records are present in the index!")

    except Exception as e:
        st.error(f"Error analyzing index coverage: {e}")
else:
    st.info("Index file not found. Build the index first to see coverage analysis.")
