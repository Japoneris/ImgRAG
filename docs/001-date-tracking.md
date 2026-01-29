# Date Tracking for Images

## Overview

This feature adds two date fields to track when images were created and when they were added to the database.

## Fields

### `created_at`
- **Type:** datetime
- **Description:** The file creation or modification date of the image file
- **Source:** Extracted from file system metadata during ingestion
- **Note:** On Linux, true creation time (`st_birthtime`) is not available, so modification time (`st_mtime`) is used as fallback

### `ingested_at`
- **Type:** datetime
- **Description:** The timestamp when the image was added to the database
- **Source:** Set automatically at ingestion time

## Database Schema

```sql
CREATE TABLE images (
    hash TEXT PRIMARY KEY,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    size INTEGER NOT NULL,
    mimetype TEXT NOT NULL,
    created_at TEXT,      -- ISO 8601 format
    ingested_at TEXT      -- ISO 8601 format
);
```

## CLI Usage

### List Command

The `list` command displays dates in short format (YYYY-MM-DD):

```
$ python -m src.cli list

Hash                         Size   Dimensions Created      Ingested
--------------------------------------------------------------------------------
7931b067c8352f7726..       1274 B   100x100   2026-01-29   2026-01-29
```

### Search Command

The `search` command displays full timestamps:

```
$ python -m src.cli search 7931

Hash:     7931b067c8352f7726d667a9f716d928e907739ee1e27d94bb7ca5ee8811b1a3
  Size:     100x100
  Bytes:    1274
  Mimetype: image/jpeg
  Created:  2026-01-29 21:51:54
  Ingested: 2026-01-29 22:04:18
  Location: /path/to/image.jpg
```

## API Usage

### ImageRecord Model

```python
from src.models import ImageRecord
from datetime import datetime

record = ImageRecord(
    hash="abc123...",
    width=100,
    height=100,
    size=1024,
    mimetype="image/jpeg",
    created_at=datetime(2026, 1, 15, 10, 30, 0),
    ingested_at=datetime.now(),
)
```

### Scanner

The `ImageScanner.extract_metadata()` method automatically extracts `created_at` from the file:

```python
from src.scanner import ImageScanner

record = ImageScanner.extract_metadata("/path/to/image.jpg")
print(record.created_at)  # datetime object
```

## Files Modified

- `src/models.py` - Added `created_at` and `ingested_at` fields to `ImageRecord`
- `src/database.py` - Updated schema and queries for new columns
- `src/scanner.py` - Added `get_file_creation_date()` method
- `src/cli.py` - Updated `list` and `search` output formatting
