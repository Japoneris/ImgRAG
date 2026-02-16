# Merge Ingest Pages

**Date:** 2026-02-16

## Overview

Merged the two separate ingestion pages ("Ingest Folder" and "Ingest from Config") into a single unified "Ingest Images" page with tabs for better organization and reduced navigation complexity.

## Changes

### Before
- `app/pages/5_Ingest_Folder.py`: Single folder ingestion
- `app/pages/6_Ingest_Config.py`: Config-based batch ingestion
- Pages 7, 8, 9 for other functions

### After
- `app/pages/5_Ingest_Images.py`: Combined ingestion page with two tabs:
  - **📁 Single Folder**: Scan one directory (previously Ingest Folder)
  - **📋 From Config**: Batch process using YAML files (previously Ingest from Config)
- Pages renumbered: 6 (Rebuild Index), 7 (Database Status), 8 (Remove Images)

## Implementation

The merged page uses Streamlit tabs to organize the two ingestion modes:

```python
tab1, tab2 = st.tabs(["📁 Single Folder", "📋 From Config"])

with tab1:
    # Single folder ingestion UI
    ...

with tab2:
    # Config-based ingestion UI
    ...
```

Both tabs share:
- Common sidebar settings (API URL, API key, model selection)
- Same database connection caching
- Same file ingestion function (`ingest_single_file`)
- Auto-reload cache after completion

## Benefits

1. **Better Organization**: Related functionality grouped together
2. **Reduced Navigation**: One less page to navigate through
3. **Shared Settings**: API settings apply to both modes without switching pages
4. **Consistent Experience**: Both modes use the same visual style and workflow
5. **Easier Maintenance**: Shared code reduces duplication

## Files Modified

- ✨ Created: `app/pages/5_Ingest_Images.py` (merged page)
- 🗑️ Deleted: `app/pages/5_Ingest_Folder.py`
- 🗑️ Deleted: `app/pages/6_Ingest_Config.py`
- 🔄 Renamed: `app/pages/7_Rebuild_Index.py` → `app/pages/6_Rebuild_Index.py`
- 🔄 Renamed: `app/pages/8_Database_Status.py` → `app/pages/7_Database_Status.py`
- 🔄 Renamed: `app/pages/9_Remove_Images.py` → `app/pages/8_Remove_Images.py`
- ✏️ Updated: `app/app.py` (main page description)
- ✏️ Updated: `app/pages/4_Index_Management.py` (navigation links)

## Usage

### Single Folder Mode
1. Navigate to "Ingest Images" page
2. Stay on the "📁 Single Folder" tab
3. Enter folder path
4. Configure options (recursive, force embed, compute embeddings)
5. Click "Start Ingestion"

### Config Mode
1. Navigate to "Ingest Images" page
2. Switch to "📋 From Config" tab
3. Select a config file from the dropdown or enter custom path
4. Configure options (force embed, compute embeddings)
5. Click "Start Config Ingestion"

Both modes will auto-reload the cache after completion to update the app state.
