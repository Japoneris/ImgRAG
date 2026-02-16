"""
Image Database - Streamlit App

Main application with navigation.
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Image Database",
    page_icon="🖼️",
    layout="wide"
)

# Sidebar with cache reload button
st.sidebar.markdown("---")
st.sidebar.subheader("Cache Management")
st.sidebar.markdown("Reload cached data after CLI updates or index rebuilds.")
if st.sidebar.button("🔄 Reload Cache", type="secondary", use_container_width=True):
    st.cache_resource.clear()
    st.cache_data.clear()
    st.sidebar.success("Cache cleared! Reloading...")
    st.rerun()

# Navigation with organized sections
pg = st.navigation({
    "Main": [
        st.Page("pages/00_Home.py", title="Home", icon="🏠"),
    ],
    "Search & Browse": [
        st.Page("pages/1_Upload.py", title="Upload Images", icon="⬆️"),
        st.Page("pages/2_Search.py", title="Search Images", icon="🔍"),
        st.Page("pages/3_Hash_Search.py", title="Hash Search", icon="#️⃣"),
    ],
    "Database Management": [
        st.Page("pages/4_Index_Management.py", title="Management Hub", icon="⚙️"),
        st.Page("pages/5_Ingest_Images.py", title="Ingest Images", icon="📂"),
        st.Page("pages/6_Rebuild_Index.py", title="Rebuild Index", icon="🔄"),
        st.Page("pages/7_Database_Status.py", title="Database Status", icon="📊"),
        st.Page("pages/8_Remove_Images.py", title="Remove Images", icon="🗑️"),
    ],
})

pg.run()
