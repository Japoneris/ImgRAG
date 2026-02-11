# Monitor Script

The monitor script (`cli_monitor.py`) keeps configured image directories in sync with both the hash database (SQLite) and embedding database (ChromaDB).

## Configuration

Create a YAML config file:

```yaml
paths:
  - /path/to/images1
  - /path/to/images2
recursive: true  # optional, default true
```

Generate a sample config:
```bash
python -m src.cli_monitor init config.yaml
```

## Environment Variables

- `EMBEDDING_API_URL` (required): Base URL of the embedding API server
- `EMBEDDING_MODEL` (optional): Model name to use (default: "default")
- `EMBEDDING_API_KEY` (optional): API key for authentication

## Commands

### sync

Performs full synchronization:
1. Scans configured directories for images
2. Adds new images to hash DB and computes embeddings
3. Reports removed images and prompts for deletion confirmation
4. Auto-fixes consistency issues (missing embeddings, orphan embeddings)

```bash
# Full sync
python -m src.cli_monitor sync config.yaml

# Dry-run (show what would happen)
python -m src.cli_monitor sync config.yaml --dry-run

# Skip deletion confirmation
python -m src.cli_monitor sync config.yaml --yes
```

### check

Read-only consistency check. Reports:
- Images on disk not in hash DB
- Images in hash DB missing from disk
- Images in hash DB without embeddings
- Embeddings without corresponding hash DB entry

```bash
python -m src.cli_monitor check config.yaml
```

### init

Generate a sample configuration file:

```bash
python -m src.cli_monitor init config.yaml
python -m src.cli_monitor init config.yaml --force  # overwrite existing
```

## Database Paths

Default paths:
- Hash DB: `data/images.db`
- Embeddings DB: `data/embeddings`

Override with flags:
```bash
python -m src.cli_monitor sync config.yaml -d custom/images.db -e custom/embeddings
```
