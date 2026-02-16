"""
Rebuild Index Page

Rebuild the hash→filepath mapping index.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from src.core.scanner import ImageScanner

# Configuration
INDEX_PATH = Path(__file__).parent.parent.parent / "data" / "index.json"

st.set_page_config(page_title="Rebuild Index", page_icon="🔄", layout="wide")

st.title("🔄 Rebuild Hash Index")

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

                # Auto-reload cache to refresh index.json across all pages
                st.info("🔄 Reloading cache to update app state...")
                st.cache_resource.clear()
                st.cache_data.clear()

            except Exception as e:
                st.error(f"Error rebuilding index: {e}")
