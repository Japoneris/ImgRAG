"""Unified CLI for image database: ingest, embed, search, and manage.

Merges the functionality of `imgdb` (hash+metadata) and `imgdb-embed` (embeddings)
into a single tool. The `ingest` command now stores metadata AND computes embeddings
in one step.

Environment variables:
    EMBEDDING_API_URL: Base URL of the embedding API server (required for ingest/embed)
    EMBEDDING_MODEL: Model name to use (default: "default")
    EMBEDDING_API_KEY: Optional API key for authentication
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from tqdm import tqdm
import yaml

from .api.embedding_api import EmbeddingAPI, EmbeddingAPIError
from .storage.embedding_db import EmbeddingDatabase
from .storage.database import ImageDatabase
from .core.scanner import ImageScanner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    with open(path) as f:
        config = yaml.safe_load(f)

    if not config:
        print(f"Error: Empty config file: {config_path}")
        sys.exit(1)

    if "paths" not in config:
        print(f"Error: Config file must contain 'paths' key")
        sys.exit(1)

    if not config["paths"]:
        print(f"Error: 'paths' list is empty")
        sys.exit(1)

    return config


def get_api_client() -> EmbeddingAPI:
    """Create API client from environment variables."""
    base_url = os.environ.get("EMBEDDING_API_URL")
    if not base_url:
        print("Error: EMBEDDING_API_URL environment variable is required")
        sys.exit(1)

    api_key = os.environ.get("EMBEDDING_API_KEY")
    return EmbeddingAPI(base_url=base_url, api_key=api_key)


def get_model_name() -> str:
    """Get model name from environment variable."""
    return os.environ.get("EMBEDDING_MODEL", "default")


def _try_get_api_client() -> "EmbeddingAPI | None":
    """Return an API client if EMBEDDING_API_URL is set, else None."""
    base_url = os.environ.get("EMBEDDING_API_URL")
    if not base_url:
        return None
    api_key = os.environ.get("EMBEDDING_API_KEY")
    return EmbeddingAPI(base_url=base_url, api_key=api_key)


def _ingest_single_file(
    filepath: Path,
    scanner: ImageScanner,
    db: ImageDatabase,
    embed_db: EmbeddingDatabase | None,
    api: "EmbeddingAPI | None",
    model: str,
    force_embed: bool,
) -> str:
    """Ingest a single image file. Returns 'added', 'skipped', or 'error'.

    Stores metadata in SQLite and (when API is available) computes + stores
    the embedding in ChromaDB.
    """
    file_hash = scanner.compute_hash(filepath)

    # -- metadata --
    is_new = False
    if db.get_by_hash(file_hash):
        pass  # metadata already present
    else:
        record = scanner.extract_metadata(filepath)
        db.add_record(record)
        is_new = True

    # -- embedding --
    embed_ok = False
    if api is not None and embed_db is not None:
        existing = embed_db.get_embedding(file_hash, model)
        if existing and not force_embed:
            embed_ok = True  # already done
        else:
            try:
                embedding = api.get_embedding(filepath, model=model)
                metadata = {
                    "filepath": str(filepath.absolute()),
                    "dimensions": len(embedding),
                }
                embed_db.add_embedding(file_hash, embedding, model, metadata)
                embed_ok = True
            except EmbeddingAPIError as e:
                tqdm.write(f"Warning: Embedding failed for {filepath.name}: {e}")

    if is_new:
        return "added"
    return "skipped"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def ingest(args):
    """Ingest images: store metadata + compute embeddings in one pass."""
    db = ImageDatabase(args.database)
    scanner = ImageScanner()

    # Embedding is optional – works without API but prints a warning
    api = _try_get_api_client()
    model = get_model_name()
    embed_db = None
    if api is not None:
        embed_db = EmbeddingDatabase(args.embeddings_db)
    else:
        if not args.no_embed:
            print("Warning: EMBEDDING_API_URL not set – skipping embeddings (metadata only)")
            print("  Set the variable or pass --no-embed to silence this warning.\n")

    path = Path(args.path)
    added = 0
    skipped = 0
    errors = 0

    if path.is_file():
        if not scanner.is_image(path):
            print(f"Error: {path} is not a recognized image file")
            sys.exit(1)

        result = _ingest_single_file(
            path, scanner, db, embed_db, api, model, args.force,
        )
        if result == "added":
            print(f"Added: {path}")
            added = 1
        else:
            print(f"Skipped (duplicate): {path}")
            skipped = 1

    elif path.is_dir():
        images = [f for f in path.rglob("*") if f.is_file() and scanner.is_image(f)]
        for filepath in tqdm(images, desc="Ingesting"):
            try:
                result = _ingest_single_file(
                    filepath, scanner, db, embed_db, api, model, args.force,
                )
                if result == "added":
                    added += 1
                else:
                    skipped += 1
            except Exception as e:
                tqdm.write(f"Warning: Could not process {filepath}: {e}")
                errors += 1
    else:
        print(f"Error: {path} does not exist")
        sys.exit(1)

    print(f"\nIngested {added} image(s), skipped {skipped} duplicate(s), {errors} error(s).")
    print(f"Total in metadata DB: {db.count()}")
    if embed_db is not None:
        print(f"Total embeddings ({model}): {embed_db.count(model)}")


def ingest_config(args):
    """Ingest images from a YAML config file (same format as imgdb-monitor)."""
    config = load_config(args.config)
    db = ImageDatabase(args.database)
    scanner = ImageScanner()

    api = _try_get_api_client()
    model = get_model_name()
    embed_db = None
    if api is not None:
        embed_db = EmbeddingDatabase(args.embeddings_db)
    else:
        if not args.no_embed:
            print("Warning: EMBEDDING_API_URL not set – skipping embeddings (metadata only)\n")

    paths = [Path(p) for p in config.get("paths", [])]
    recursive = config.get("recursive", True)

    for p in paths:
        if not p.exists():
            print(f"Warning: Configured path does not exist: {p}")

    total_added = 0
    total_skipped = 0
    total_errors = 0

    for dirpath in paths:
        if not dirpath.exists():
            continue

        if dirpath.is_file():
            images = [dirpath] if scanner.is_image(dirpath) else []
        elif recursive:
            images = [f for f in dirpath.rglob("*") if f.is_file() and scanner.is_image(f)]
        else:
            images = [f for f in dirpath.glob("*") if f.is_file() and scanner.is_image(f)]

        print(f"Found {len(images)} images in {dirpath}")

        for filepath in tqdm(images, desc=str(dirpath), leave=False):
            try:
                result = _ingest_single_file(
                    filepath, scanner, db, embed_db, api, model, args.force,
                )
                if result == "added":
                    total_added += 1
                else:
                    total_skipped += 1
            except Exception as e:
                tqdm.write(f"Warning: Could not process {filepath}: {e}")
                total_errors += 1

    print(f"\nDone: {total_added} added, {total_skipped} skipped, {total_errors} errors")
    print(f"Total in metadata DB: {db.count()}")
    if embed_db is not None:
        print(f"Total embeddings ({model}): {embed_db.count(model)}")


def search(args):
    """Search for an image by hash prefix (metadata + embedding similarity)."""
    db = ImageDatabase(args.database)
    hash_prefix = args.hash

    records = db.search_by_prefix(hash_prefix)
    if not records:
        print(f"No images found matching prefix: {hash_prefix}")
        return

    if len(records) > 1:
        print(f"Found {len(records)} matches for prefix '{hash_prefix}':\n")

    # Load index if available
    index = {}
    meta = {}
    index_path = Path(args.index)
    if index_path.exists():
        index, meta = ImageScanner.load_index(index_path)

    for record in records:
        print(f"Hash:     {record.hash}")
        print(f"  Size:     {record.width}x{record.height}")
        print(f"  Bytes:    {record.size}")
        print(f"  Mimetype: {record.mimetype}")
        if record.created_at:
            print(f"  Created:  {record.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if record.ingested_at:
            print(f"  Ingested: {record.ingested_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if index:
            matches = ImageScanner.find_by_hash(record.hash, index, meta)
            if matches:
                print(f"  Location: {matches[0][1]}")
            else:
                print(f"  Location: Not found in index (try rebuild-index)")
        else:
            print(f"  Location: Index not found at {index_path}")
        print()


def search_similar(args):
    """Find visually similar images by embedding distance."""
    model = get_model_name()
    embed_db = EmbeddingDatabase(args.embeddings_db)

    results = embed_db.search_by_hash(args.hash, model, n_results=args.limit)
    if not results:
        print(f"No similar images found (or hash not in database)")
        return

    print(f"Similar images to {args.hash[:16]}...:\n")
    for image_hash, distance in results:
        print(f"  {image_hash[:16]}...  (distance: {distance:.4f})")


def rebuild_index(args):
    """Rebuild the hash->filepath index."""
    path = Path(args.path)
    if not path.is_dir():
        print(f"Error: {path} is not a directory")
        sys.exit(1)

    mode = "relative" if args.relative else "absolute"
    print(f"Scanning {path} ({mode} paths)...")
    index = ImageScanner.build_index(path, args.output, relative=args.relative)
    print(f"Index rebuilt: {len(index)} images saved to {args.output}")


def list_records(args):
    """List all records in the metadata database."""
    db = ImageDatabase(args.database)
    records = db.list_all()

    if not records:
        print("Database is empty")
        return

    print(f"{'Hash':<20} {'Size':>12} {'Dimensions':>12} {'Created':<12} {'Ingested':<12}")
    print("-" * 80)
    for r in records:
        created = r.created_at.strftime('%Y-%m-%d') if r.created_at else 'N/A'
        ingested = r.ingested_at.strftime('%Y-%m-%d') if r.ingested_at else 'N/A'
        print(f"{r.hash[:18]}.. {r.size:>10} B {r.width:>5}x{r.height:<5} {created:<12} {ingested:<12}")
    print(f"\nTotal: {len(records)} record(s)")


def list_embeddings(args):
    """List stored embeddings."""
    model = get_model_name()
    embed_db = EmbeddingDatabase(args.embeddings_db)

    count = embed_db.count(model)
    print(f"Model: {model}")
    print(f"Total embeddings: {count}\n")

    if args.show_hashes:
        hashes = embed_db.list_hashes(model, limit=args.limit)
        for h in hashes:
            print(f"  {h[:20]}...")


def health_check(args):
    """Check if the embedding API is available."""
    api = get_api_client()
    model = get_model_name()

    print(f"API URL: {os.environ.get('EMBEDDING_API_URL')}")
    print(f"Model: {model}")

    if api.health_check():
        print("Status: OK")
        models = api.list_models()
        if models:
            print(f"Available models: {', '.join(models)}")
    else:
        print("Status: UNREACHABLE")
        sys.exit(1)


def analyze(args):
    """Run dimensionality reduction on embeddings and save results."""
    from .analysis.embedding_analyzer import build_analysis_data, save_analysis

    model = get_model_name()
    embed_db = EmbeddingDatabase(args.embeddings_db)
    img_db = ImageDatabase(args.database)

    data = build_analysis_data(
        embed_db=embed_db,
        img_db=img_db,
        index_path=args.index,
        model_name=model,
        method=args.method,
    )

    if data["count"] == 0:
        print("No embeddings found. Run 'ingest' first.")
        sys.exit(1)

    save_analysis(data, args.output)


def visualize(args):
    """Launch interactive visualization of analysis results."""
    data_path = Path(args.data_path)
    if not data_path.exists():
        print(f"Error: Analysis file not found: {data_path}")
        print("Run 'analyze' first to generate the analysis data.")
        sys.exit(1)

    if args.static:
        from .analysis.viewer import generate_static_html
        generate_static_html(data_path, args.static)
    else:
        from .analysis.visualizer import run_server
        run_server(data_path, port=args.port)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Image Database - ingest, embed, search, and manage images",
        epilog="Environment variables: EMBEDDING_API_URL, EMBEDDING_MODEL, EMBEDDING_API_KEY",
    )
    parser.add_argument(
        "--database", "-d",
        default="data/images.db",
        help="Path to SQLite metadata database (default: data/images.db)",
    )
    parser.add_argument(
        "--embeddings-db", "-e",
        default="data/embeddings",
        help="Path to embeddings database (default: data/embeddings)",
    )
    parser.add_argument(
        "--index", "-i",
        default="data/index.json",
        help="Path to index JSON file (default: data/index.json)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- ingest ---
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Add images to DB and compute embeddings in one step",
    )
    ingest_parser.add_argument("path", help="Image file or directory to ingest")
    ingest_parser.add_argument("--force", "-f", action="store_true", help="Recompute embeddings even if they exist")
    ingest_parser.add_argument("--no-embed", action="store_true", help="Skip embedding computation (metadata only)")
    ingest_parser.set_defaults(func=ingest)

    # --- ingest-config ---
    config_parser = subparsers.add_parser(
        "ingest-config",
        help="Ingest images from a YAML config file",
    )
    config_parser.add_argument("config", help="Path to YAML config file")
    config_parser.add_argument("--force", "-f", action="store_true", help="Recompute embeddings even if they exist")
    config_parser.add_argument("--no-embed", action="store_true", help="Skip embedding computation (metadata only)")
    config_parser.set_defaults(func=ingest_config)

    # --- search (metadata) ---
    search_parser = subparsers.add_parser(
        "search",
        help="Search for an image by hash prefix",
    )
    search_parser.add_argument("hash", help="Full or partial SHA-256 hash prefix")
    search_parser.set_defaults(func=search)

    # --- similar (embedding) ---
    similar_parser = subparsers.add_parser(
        "similar",
        help="Find visually similar images by embedding distance",
    )
    similar_parser.add_argument("hash", help="Image hash to search for")
    similar_parser.add_argument("--limit", "-n", type=int, default=10, help="Number of results (default: 10)")
    similar_parser.set_defaults(func=search_similar)

    # --- rebuild-index ---
    index_parser = subparsers.add_parser(
        "rebuild-index",
        help="Rebuild the hash->filepath index",
    )
    index_parser.add_argument("path", help="Directory to scan")
    index_parser.add_argument("--output", "-o", default="data/index.json", help="Output JSON file (default: data/index.json)")
    index_parser.add_argument("--relative", "-r", action="store_true", help="Store relative paths instead of absolute")
    index_parser.set_defaults(func=rebuild_index)

    # --- list ---
    list_parser = subparsers.add_parser(
        "list",
        help="List all records in the metadata database",
    )
    list_parser.set_defaults(func=list_records)

    # --- list-embeddings ---
    embed_list_parser = subparsers.add_parser(
        "list-embeddings",
        help="List stored embeddings",
    )
    embed_list_parser.add_argument("--show-hashes", "-s", action="store_true", help="Show image hashes")
    embed_list_parser.add_argument("--limit", "-n", type=int, default=100, help="Max hashes to show (default: 100)")
    embed_list_parser.set_defaults(func=list_embeddings)

    # --- health ---
    health_parser = subparsers.add_parser(
        "health",
        help="Check embedding API connectivity",
    )
    health_parser.set_defaults(func=health_check)

    # --- analyze ---
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Run dimensionality reduction (t-SNE/UMAP) on embeddings",
    )
    analyze_parser.add_argument(
        "--method", "-m",
        choices=["tsne", "umap"],
        default="tsne",
        help="Reduction method (default: tsne)",
    )
    analyze_parser.add_argument(
        "--output", "-o",
        default="data/analysis.json",
        help="Output JSON file (default: data/analysis.json)",
    )
    analyze_parser.set_defaults(func=analyze)

    # --- visualize ---
    viz_parser = subparsers.add_parser(
        "visualize",
        help="Visualize analysis results (Bokeh server or static HTML)",
    )
    viz_parser.add_argument("data_path", help="Path to analysis JSON file")
    viz_parser.add_argument(
        "--static", "-s",
        metavar="OUTPUT_HTML",
        help="Generate a static HTML file instead of launching a server",
    )
    viz_parser.add_argument(
        "--port", "-p",
        type=int,
        default=5006,
        help="Bokeh server port (default: 5006)",
    )
    viz_parser.set_defaults(func=visualize)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
