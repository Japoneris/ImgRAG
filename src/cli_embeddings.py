"""CLI for computing and storing image embeddings.

Environment variables:
    EMBEDDING_API_URL: Base URL of the embedding API server (required)
    EMBEDDING_MODEL: Model name to use (default: "default")
    EMBEDDING_API_KEY: Optional API key for authentication
"""

import argparse
import os
import sys
from pathlib import Path

from .api.embedding_api import EmbeddingAPI, EmbeddingAPIError
from .storage.embedding_db import EmbeddingDatabase
from .storage.database import ImageDatabase
from .core.scanner import ImageScanner


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


def embed_file(args):
    """Compute and store embedding for a single image file."""
    api = get_api_client()
    model = get_model_name()
    embed_db = EmbeddingDatabase(args.embeddings_db)

    filepath = Path(args.path)
    if not filepath.exists():
        print(f"Error: File not found: {filepath}")
        sys.exit(1)

    if not ImageScanner.is_image(filepath):
        print(f"Error: Not a recognized image file: {filepath}")
        sys.exit(1)

    # Compute hash
    image_hash = ImageScanner.compute_hash(filepath)
    print(f"Image hash: {image_hash[:16]}...")

    # Check if already exists
    existing = embed_db.get_embedding(image_hash, model)
    if existing and not args.force:
        print(f"Embedding already exists for this image (use --force to recompute)")
        return

    # Get embedding from API
    print(f"Computing embedding with model '{model}'...")
    try:
        embedding = api.get_embedding(filepath, model=model)
    except EmbeddingAPIError as e:
        print(f"Error: API call failed: {e}")
        sys.exit(1)

    # Store in database
    metadata = {
        "filepath": str(filepath.absolute()),
        "dimensions": len(embedding),
    }
    embed_db.add_embedding(image_hash, embedding, model, metadata)
    print(f"Stored embedding ({len(embedding)} dimensions)")


def embed_directory(args):
    """Compute and store embeddings for all images in a directory."""
    api = get_api_client()
    model = get_model_name()
    embed_db = EmbeddingDatabase(args.embeddings_db)

    dirpath = Path(args.path)
    if not dirpath.is_dir():
        print(f"Error: Not a directory: {dirpath}")
        sys.exit(1)

    # Find all images
    images = [f for f in dirpath.rglob("*") if f.is_file() and ImageScanner.is_image(f)]
    print(f"Found {len(images)} images in {dirpath}")

    processed = 0
    skipped = 0
    errors = 0

    for filepath in images:
        image_hash = ImageScanner.compute_hash(filepath)

        # Check if already exists
        existing = embed_db.get_embedding(image_hash, model)
        if existing and not args.force:
            skipped += 1
            continue

        # Get embedding from API
        try:
            embedding = api.get_embedding(filepath, model=model)
        except EmbeddingAPIError as e:
            print(f"Warning: Failed to process {filepath.name}: {e}")
            errors += 1
            continue

        # Store in database
        metadata = {
            "filepath": str(filepath.absolute()),
            "dimensions": len(embedding),
        }
        embed_db.add_embedding(image_hash, embedding, model, metadata)
        processed += 1
        print(f"Processed: {filepath.name} ({image_hash[:12]}...)")

    print(f"\nDone: {processed} processed, {skipped} skipped, {errors} errors")
    print(f"Total embeddings for model '{model}': {embed_db.count(model)}")


def embed_from_db(args):
    """Compute embeddings for images already in the metadata database."""
    api = get_api_client()
    model = get_model_name()
    embed_db = EmbeddingDatabase(args.embeddings_db)
    image_db = ImageDatabase(args.database)

    # Load index to find file paths
    index_path = Path(args.index)
    if not index_path.exists():
        print(f"Error: Index file not found: {index_path}")
        print("Run 'python -m src.cli rebuild-index <path>' first")
        sys.exit(1)

    index, meta = ImageScanner.load_index(index_path)
    records = image_db.list_all()
    print(f"Found {len(records)} images in metadata database")

    processed = 0
    skipped = 0
    not_found = 0
    errors = 0

    for record in records:
        # Check if already has embedding
        existing = embed_db.get_embedding(record.hash, model)
        if existing and not args.force:
            skipped += 1
            continue

        # Find file path from index
        matches = ImageScanner.find_by_hash(record.hash, index, meta)
        if not matches:
            not_found += 1
            continue

        filepath = Path(matches[0][1])
        if not filepath.exists():
            not_found += 1
            continue

        # Get embedding from API
        try:
            embedding = api.get_embedding(filepath, model=model)
        except EmbeddingAPIError as e:
            print(f"Warning: Failed to process {record.hash[:12]}...: {e}")
            errors += 1
            continue

        # Store in database
        metadata = {
            "filepath": str(filepath),
            "width": record.width,
            "height": record.height,
            "dimensions": len(embedding),
        }
        embed_db.add_embedding(record.hash, embedding, model, metadata)
        processed += 1
        print(f"Processed: {filepath.name} ({record.hash[:12]}...)")

    print(f"\nDone: {processed} processed, {skipped} skipped, {not_found} not found, {errors} errors")
    print(f"Total embeddings for model '{model}': {embed_db.count(model)}")


def search_similar(args):
    """Search for similar images by hash."""
    model = get_model_name()
    embed_db = EmbeddingDatabase(args.embeddings_db)

    results = embed_db.search_by_hash(args.hash, model, n_results=args.limit)

    if not results:
        print(f"No similar images found (or hash not in database)")
        return

    print(f"Similar images to {args.hash[:16]}...:\n")
    for image_hash, distance in results:
        print(f"  {image_hash[:16]}...  (distance: {distance:.4f})")


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


def main():
    parser = argparse.ArgumentParser(
        description="Compute and store image embeddings using an external API",
        epilog="Environment variables: EMBEDDING_API_URL (required), EMBEDDING_MODEL, EMBEDDING_API_KEY"
    )
    parser.add_argument(
        "--embeddings-db", "-e",
        default="data/embeddings",
        help="Path to embeddings database (default: data/embeddings)"
    )
    parser.add_argument(
        "--database", "-d",
        default="data/images.db",
        help="Path to SQLite metadata database (default: data/images.db)"
    )
    parser.add_argument(
        "--index", "-i",
        default="data/index.json",
        help="Path to index JSON file (default: data/index.json)"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # embed-file command
    file_parser = subparsers.add_parser("embed-file", help="Compute embedding for a single image")
    file_parser.add_argument("path", help="Path to image file")
    file_parser.add_argument("--force", "-f", action="store_true", help="Recompute even if exists")
    file_parser.set_defaults(func=embed_file)

    # embed-dir command
    dir_parser = subparsers.add_parser("embed-dir", help="Compute embeddings for all images in directory")
    dir_parser.add_argument("path", help="Path to directory")
    dir_parser.add_argument("--force", "-f", action="store_true", help="Recompute even if exists")
    dir_parser.set_defaults(func=embed_directory)

    # embed-db command
    db_parser = subparsers.add_parser("embed-db", help="Compute embeddings for images in metadata database")
    db_parser.add_argument("--force", "-f", action="store_true", help="Recompute even if exists")
    db_parser.set_defaults(func=embed_from_db)

    # search command
    search_parser = subparsers.add_parser("search", help="Find similar images by hash")
    search_parser.add_argument("hash", help="Image hash to search for")
    search_parser.add_argument("--limit", "-n", type=int, default=10, help="Number of results (default: 10)")
    search_parser.set_defaults(func=search_similar)

    # list command
    list_parser = subparsers.add_parser("list", help="List stored embeddings")
    list_parser.add_argument("--show-hashes", "-s", action="store_true", help="Show image hashes")
    list_parser.add_argument("--limit", "-n", type=int, default=100, help="Max hashes to show (default: 100)")
    list_parser.set_defaults(func=list_embeddings)

    # health command
    health_parser = subparsers.add_parser("health", help="Check API connectivity")
    health_parser.set_defaults(func=health_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
