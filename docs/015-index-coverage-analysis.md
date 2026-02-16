# Index Coverage Analysis

## Overview

Added a new section in the Index Management page (Database Status tab) to analyze which images exist in the metadata/embedding databases but are not present in the hash index file.

## Feature Description

The Index Coverage Analysis helps identify images that have been added to the database but may not be quickly locatable by file path because they're missing from the index.

## What It Shows

1. **Summary Metrics**:
   - Total images in metadata database
   - Total images in index file
   - Count of images not in index

2. **Per-Model Analysis**:
   - For each embedding model, shows how many embeddings exist but are not in the index
   - Warning indicators for models with missing index entries

3. **Detailed View** (on demand):
   - List of up to 100 missing images with their metadata:
     - Hash (first 16 characters)
     - Dimensions (width x height)
     - File size
     - MIME type
     - Which embedding models have computed embeddings for this image
   - Full count if more than 100 images are missing

4. **Export Functionality**:
   - Download button to export all missing hashes as a text file
   - One hash per line for easy processing

## Use Cases

- **Post-Migration**: After moving files or reorganizing directories, identify which images need to be re-indexed
- **Troubleshooting**: Find images that exist in the database but can't be located on disk
- **Database Maintenance**: Ensure index and database stay synchronized
- **Batch Processing**: Export missing hashes to re-ingest or rebuild specific parts of the index

## Location

App → Index Management page → Database Status tab → Index Coverage Analysis section

## Technical Details

- Uses `ImageDatabase.list_all()` to get all metadata records
- Uses `EmbeddingDatabase.get_all_embeddings(model)` for embedding coverage
- Compares hashes against the index JSON file (`data/index.json`)
- Efficient set operations for large datasets
