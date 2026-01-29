# Source Code Reorganization

## Overview

The `src/` directory has been reorganized to improve discoverability and separation of concerns. The CLI entry point stays at the root, while library modules are grouped into logical subpackages.

## New Structure

```
src/
├── cli.py              # CLI entry point (executable)
├── __init__.py         # Package exports
├── core/               # Core business logic
│   ├── __init__.py
│   ├── models.py       # Data models (ImageRecord)
│   └── scanner.py      # Image scanning and metadata extraction
├── storage/            # Data persistence layers
│   ├── __init__.py
│   ├── database.py     # SQLite metadata storage (ImageDatabase)
│   └── embedding_db.py # ChromaDB embedding storage (EmbeddingDatabase)
└── api/                # External integrations
    ├── __init__.py
    └── embedding_api.py # Embedding API client (EmbeddingAPI)
```

## Package Organization

### Root (`src/`)
- `cli.py` - Command-line interface entry point
- Users can run `python -m src.cli` or import the CLI module directly

### Core (`src/core/`)
Business logic independent of storage or external services:
- `models.py` - `ImageRecord` dataclass for image metadata
- `scanner.py` - `ImageScanner` for file discovery and metadata extraction

### Storage (`src/storage/`)
Data persistence implementations:
- `database.py` - `ImageDatabase` for SQLite metadata storage
- `embedding_db.py` - `EmbeddingDatabase` for ChromaDB vector storage

### API (`src/api/`)
External service integrations:
- `embedding_api.py` - `EmbeddingAPI` client for remote embedding services

## Import Paths

All public classes and functions are re-exported from the package root for convenience:

```python
# Recommended: import from package root
from src import ImageRecord, ImageScanner, ImageDatabase, EmbeddingAPI

# Also works: import from subpackages
from src.core import ImageRecord, ImageScanner
from src.storage import ImageDatabase, EmbeddingDatabase
from src.api import EmbeddingAPI, MockEmbeddingAPI
```

## Migration from Old Structure

| Old Path | New Path |
|----------|----------|
| `src/models.py` | `src/core/models.py` |
| `src/scanner.py` | `src/core/scanner.py` |
| `src/database.py` | `src/storage/database.py` |
| `src/embedding_db.py` | `src/storage/embedding_db.py` |
| `src/embedding_api.py` | `src/api/embedding_api.py` |
| `src/cli.py` | `src/cli.py` (unchanged) |

## Benefits

1. **Clear entry point** - CLI at root makes it obvious how to run the tool
2. **Logical grouping** - Related modules are co-located
3. **Separation of concerns** - Core logic, storage, and API are independent
4. **Extensibility** - Easy to add new storage backends or API clients
5. **Testability** - Each layer can be tested in isolation

## Files Modified

- Created `src/core/` with models and scanner
- Created `src/storage/` with database modules
- Created `src/api/` with embedding API client
- Updated `src/__init__.py` with new import paths
- Updated `src/cli.py` import statements
