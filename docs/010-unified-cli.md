# 010 – Unified CLI (`imgdb-full`)

Merges `imgdb` (hash + metadata) and `imgdb-embed` (embeddings) into a single
tool so that storing images no longer requires running two separate scripts.

The two original CLIs are kept for legacy use.

## Entry point

```
imgdb-full
```

## Commands

| Command            | Description |
|--------------------|-------------|
| `ingest <path>`    | Add images to the metadata DB **and** compute embeddings in one pass. Works with a single file or a directory. |
| `ingest-config <yaml>` | Same as `ingest`, but reads paths from a YAML config file. |
| `search <hash>`    | Search metadata by hash prefix. |
| `similar <hash>`   | Find visually similar images via embedding distance. |
| `rebuild-index <dir>` | Rebuild the hash→filepath JSON index. |
| `list`             | List all metadata records. |
| `list-embeddings`  | List stored embeddings. |
| `health`           | Check embedding API connectivity. |

## Key flags

- `--no-embed` – skip embedding computation (metadata only, no API needed).
- `--force / -f` – recompute embeddings even if they already exist.

## Embedding API

If `EMBEDDING_API_URL` is **not** set, `ingest` gracefully degrades to
metadata-only mode (same behavior as the old `imgdb ingest`).

## Databases

Uses the same databases as the existing tools:

- `data/images.db` (SQLite – metadata)
- `data/embeddings/` (ChromaDB – vectors)
- `data/index.json` (hash→filepath index)
