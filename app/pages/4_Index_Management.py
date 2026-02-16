"""
Index Management - Navigation Page

Navigate to different database management functions.
"""
import streamlit as st

st.set_page_config(page_title="Index Management", page_icon="⚙️", layout="wide")

st.title("⚙️ Index Management")

st.markdown("""
This section provides tools for managing your image database, embeddings, and index.
Use the sidebar to navigate to specific management pages, or use the quick links below.
""")

st.divider()

# Create columns for organized navigation
col1, col2 = st.columns(2)

with col1:
    st.header("Data Ingestion")

    st.subheader("📂 Ingest Images")
    st.markdown("""
    Scan directories or use YAML configs to add images to the database.
    - **Single Folder**: Scan one directory with recursive support
    - **From Config**: Batch process multiple directories using YAML files
    - Automatic metadata extraction
    - Optional embedding computation
    """)
    st.page_link("pages/5_Ingest_Images.py", label="Go to Ingest Images →", icon="📂")

    st.divider()

    st.subheader("🔄 Rebuild Index")
    st.markdown("""
    Rebuild the hash→filepath mapping index for quick file location.
    - Full directory scanning
    - Relative or absolute paths
    - Index statistics
    """)
    st.page_link("pages/6_Rebuild_Index.py", label="Go to Rebuild Index →", icon="🔄")

with col2:
    st.header("Database Management")

    st.subheader("📊 Database Status")
    st.markdown("""
    View comprehensive statistics and analyze database coverage.
    - Metadata and embedding counts
    - Index coverage analysis
    - Missing image detection
    - Export functionality
    """)
    st.page_link("pages/7_Database_Status.py", label="Go to Database Status →", icon="📊")

    st.divider()

    st.subheader("🗑️ Remove Images")
    st.markdown("""
    Selectively remove images from databases.
    - Search by hash prefix
    - Bulk selection
    - Visual preview
    - Safe removal with confirmation
    """)
    st.page_link("pages/8_Remove_Images.py", label="Go to Remove Images →", icon="🗑️")

st.divider()

st.info("""
💡 **Tip:** Use the sidebar to quickly navigate between all pages. Each management function
is now on its own dedicated page for better performance and usability.
""")
