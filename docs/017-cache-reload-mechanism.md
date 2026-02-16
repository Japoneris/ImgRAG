# Cache Reload Mechanism

**Date:** 2026-02-16

## Overview

Added a cache reload mechanism to the Streamlit app to ensure that cached data (especially `index.json`) is properly refreshed when data is updated either through the app or via command-line tools.

## Problem

The app uses `@st.cache_resource` and `@st.cache_data` decorators to cache database connections and the `index.json` file for performance. However, when:
- The index is rebuilt (via CLI or app)
- Folders are ingested and new images are added
- Data is updated through command-line tools

The cached data would not update automatically, causing the app to show stale information until manually restarted.

## Solution

### 1. Sidebar Reload Button

Added a "🔄 Reload Cache" button to the sidebar of the main app and key pages:
- `app/app.py` (main page - accessible from all pages)
- `app/pages/8_Database_Status.py`

When clicked, this button:
- Clears `st.cache_resource` (database connections)
- Clears `st.cache_data` (loaded index.json and other cached data)
- Triggers a rerun of the app

### 2. Auto-reload After Processing

Added automatic cache clearing after data modification operations:

- **Ingest Folder** (`app/pages/5_Ingest_Folder.py`): Auto-reloads after completing folder ingestion
- **Ingest Config** (`app/pages/6_Ingest_Config.py`): Auto-reloads after completing batch ingestion from YAML config
- **Rebuild Index** (`app/pages/7_Rebuild_Index.py`): Auto-reloads after rebuilding the hash→filepath index

## Implementation Details

The cache reload is implemented by:
```python
st.cache_resource.clear()  # Clear database connections
st.cache_data.clear()       # Clear cached data (index.json, etc.)
st.rerun()                  # Optional: force immediate rerun
```

## Benefits

1. **Consistency**: App data stays in sync with actual database/file state
2. **User Experience**: No need to manually restart the app after updates
3. **CLI Integration**: Changes made via command-line tools are visible after clicking the sidebar reload button
4. **Automatic Updates**: Most operations automatically reload, reducing manual intervention

## Usage

### Manual Reload (for CLI updates)
1. Make changes using CLI tools (e.g., `imgdb rebuild-index`)
2. In the Streamlit app, click "🔄 Reload Cache" in the sidebar
3. The app refreshes with the latest data

### Automatic Reload
When using these pages in the app, cache reloads automatically:
- After ingesting a folder
- After processing a YAML config
- After rebuilding the index

## Files Modified

- `app/app.py`: Added sidebar cache reload button
- `app/pages/5_Ingest_Folder.py`: Added auto-reload after ingestion
- `app/pages/6_Ingest_Config.py`: Added auto-reload after config processing
- `app/pages/7_Rebuild_Index.py`: Added auto-reload after index rebuild
- `app/pages/8_Database_Status.py`: Replaced standalone button with sidebar button for consistency
