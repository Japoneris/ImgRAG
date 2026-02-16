# Streamlit Index Management Page

**Date:** 2026-02-16

## Overview

Added a new comprehensive Index Management page to the Streamlit web app that provides a GUI for managing the image database index. This allows users to ingest folders, sync the index, and monitor database status without using the CLI.

## Implementation

### New File

- `app/pages/4_Index_Management.py` - Multi-tab interface for index management

### Features

The page is organized into 5 tabs:

#### 1. Ingest Folder

- Scan a directory for images and add them to the database
- Options:
  - Recursive scanning (include subdirectories)
  - Force re-compute embeddings
  - Toggle embedding computation on/off
- Live progress tracking with detailed statistics
- Shows added, skipped (duplicates), and error counts

#### 2. Ingest from Config

- Use YAML configuration files to ingest multiple directories at once
- Lists available config files from `configs/` directory
- Option to provide custom config path
- Displays config contents before ingestion
- Processes each configured path with progress tracking
- Same options as folder ingestion (recursive, force embeddings, etc.)

#### 3. Rebuild Index

- Rebuild the hash→filepath mapping index
- Options:
  - Recursive scanning
  - Store relative vs absolute paths
  - Custom output path
- Shows sample index entries after rebuild
- Useful after moving files or when index is out of sync

#### 4. Database Status

- View comprehensive database statistics:
  - Metadata database: total images, disk size
  - Embedding database: per-model counts
  - Hash index: indexed images, base path, type (relative/absolute)
- **Database Comparison**: Identifies discrepancies between metadata and embeddings
  - Shows warnings when counts don't match
  - Helps identify missing embeddings or orphaned records
- Refresh button to reload status

#### 5. Remove Images

- Selectively remove images from the database
- Search modes:
  - View all images in database
  - Search by hash prefix
- Features:
  - Visual preview of images before removal
  - Display full metadata and embedding information
  - Select individual images or use bulk selection (Select All/Deselect All)
  - Choose what to remove:
    - Metadata only
    - Embeddings only
    - Both metadata and embeddings
  - Safety confirmation required (type "DELETE N" to confirm)
  - Live progress tracking during removal
- Shows which models have embeddings for each image

## Usage

1. Navigate to the "Index Management" page in the Streamlit sidebar
2. Configure embedding API settings in the sidebar (URL, API key, model)
3. Select the appropriate tab for your task
4. For folder ingestion:
   - Enter folder path
   - Choose options
   - Click "Start Ingestion"
5. For config ingestion:
   - Select or provide a config file
   - Click "Start Config Ingestion"
6. For index rebuild:
   - Enter folder path to scan
   - Choose path storage type
   - Click "Rebuild Index"

## Benefits

- **No CLI Required**: All index management operations available through GUI
- **Live Progress**: Real-time feedback on ingestion progress
- **Batch Processing**: Config-based ingestion for multiple directories
- **Status Monitoring**: Easy visibility into database health and sync status
- **Error Handling**: Clear error messages and warnings for troubleshooting

## Configuration Changes

- **Default Model**: Changed default embedding model to `dinov2-small` (previously `default`)
  - Applied across all Streamlit pages: Upload, Search, and Index Management
  - Can be overridden via `EMBEDDING_MODELS` environment variable

## Technical Details

- Reuses existing core modules (`ImageScanner`, `ImageDatabase`, `EmbeddingDatabase`)
- Follows the same ingestion logic as `cli_full.py`
- Properly handles API availability (graceful degradation if API is unavailable)
- Uses Streamlit's progress bars and metrics for user feedback
- Caches database connections for performance
- Removal feature uses session state to track selections across reruns
- Implements safety confirmation to prevent accidental deletions
