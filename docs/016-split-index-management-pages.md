# Split Index Management into Sub-Pages

## Overview

Refactored the Index Management page (page 4) by splitting its 5 tabs into separate, dedicated pages for better usability and performance.

## Motivation

The original Index Management page had become too complex with 5 different tabs:
1. Ingest Folder
2. Ingest from Config
3. Rebuild Index
4. Database Status
5. Remove Images

This made the page difficult to interact with, slow to load, and hard to navigate.

## New Structure

### Page 4: Index Management (Navigation)
- Now serves as a navigation hub
- Provides overview of all sub-pages
- Quick links to each management function
- Organized into "Data Ingestion" and "Database Management" sections

### Page 5: Ingest Folder (📂)
- Scan directories for images
- Extract metadata and compute embeddings
- Recursive scanning support
- Progress tracking with live statistics

### Page 6: Ingest from Config (📋)
- Batch ingestion using YAML configuration files
- Support for multiple directories
- Config file management and viewing
- Useful for monitoring workflows

### Page 7: Rebuild Index (🔄)
- Rebuild hash→filepath mapping index
- Support for relative or absolute paths
- Index statistics and sample entries
- Run after moving files or reorganizing

### Page 8: Database Status (📊)
- View metadata and embedding database stats
- Index status and coverage analysis
- Identify images not in the index
- Export missing hashes
- Database comparison metrics

### Page 9: Remove Images (🗑️)
- Selectively remove images from databases
- Search by hash prefix or view all
- Visual preview with thumbnails
- Bulk selection support
- Safe removal with confirmation

## Benefits

1. **Performance**: Each page loads only what it needs
2. **Usability**: Focused interface for each task
3. **Navigation**: Easier to find specific functions
4. **Maintainability**: Cleaner code separation
5. **Scalability**: Easy to add new management functions

## Technical Details

- Each page is a standalone Python file in `app/pages/`
- Shared functionality (database initialization, API client) duplicated per page for independence
- Navigation page uses `st.page_link()` for internal links
- Preserved all original functionality from the tabbed interface

## Migration Notes

- All original functionality preserved
- No database schema changes
- No API changes
- Users can navigate via sidebar or quick links on page 4
