"""Command-line interface for image database."""

import argparse
import sys
from pathlib import Path

from .storage.database import ImageDatabase
from .core.scanner import ImageScanner


def ingest(args):
    """Ingest images into the database."""
    db = ImageDatabase(args.database)
    scanner = ImageScanner()

    path = Path(args.path)
    added = 0
    skipped = 0

    if path.is_file():
        if scanner.is_image(path):
            file_hash = scanner.compute_hash(path)
            if db.get_by_hash(file_hash):
                print(f"Skipped (duplicate): {path}")
                skipped = 1
            else:
                record = scanner.extract_metadata(path)
                db.add_record(record)
                print(f"Added: {path} (hash: {record.hash[:16]}...)")
                added = 1
        else:
            print(f"Error: {path} is not a recognized image file")
            sys.exit(1)
    elif path.is_dir():
        for filepath in path.rglob("*"):
            if filepath.is_file() and scanner.is_image(filepath):
                try:
                    file_hash = scanner.compute_hash(filepath)
                    if db.get_by_hash(file_hash):
                        print(f"Skipped (duplicate): {filepath.name}")
                        skipped += 1
                    else:
                        record = scanner.extract_metadata(filepath)
                        db.add_record(record)
                        print(f"Added: {filepath.name} ({record.width}x{record.height})")
                        added += 1
                except Exception as e:
                    print(f"Warning: Could not process {filepath}: {e}")
    else:
        print(f"Error: {path} does not exist")
        sys.exit(1)

    print(f"\nIngested {added} image(s), skipped {skipped} duplicate(s). Total in database: {db.count()}")


def search(args):
    """Search for an image by hash (supports partial hash prefix)."""
    db = ImageDatabase(args.database)
    hash_prefix = args.hash

    # Search database by prefix
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

        # Find location from index
        if index:
            matches = ImageScanner.find_by_hash(record.hash, index, meta)
            if matches:
                print(f"  Location: {matches[0][1]}")
            else:
                print(f"  Location: Not found in index (try rebuild-index)")
        else:
            print(f"  Location: Index not found at {index_path}")
        print()


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
    """List all records in the database."""
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


def main():
    parser = argparse.ArgumentParser(
        description="Image Database - Store and retrieve images by content hash"
    )
    parser.add_argument(
        "--database", "-d",
        default="data/images.db",
        help="Path to SQLite database (default: data/images.db)"
    )
    parser.add_argument(
        "--index", "-i",
        default="data/index.json",
        help="Path to index JSON file (default: data/index.json)"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Ingest command
    ingest_parser = subparsers.add_parser("ingest", help="Add images to the database")
    ingest_parser.add_argument("path", help="Image file or directory to ingest")
    ingest_parser.set_defaults(func=ingest)

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for an image by hash")
    search_parser.add_argument("hash", help="Full or partial SHA-256 hash prefix")
    search_parser.set_defaults(func=search)

    # Rebuild index command
    index_parser = subparsers.add_parser("rebuild-index", help="Rebuild the hash->filepath index")
    index_parser.add_argument("path", help="Directory to scan")
    index_parser.add_argument(
        "--output", "-o",
        default="data/index.json",
        help="Output JSON file (default: data/index.json)"
    )
    index_parser.add_argument(
        "--relative", "-r",
        action="store_true",
        help="Store relative paths instead of absolute paths"
    )
    index_parser.set_defaults(func=rebuild_index)

    # List command
    list_parser = subparsers.add_parser("list", help="List all records in the database")
    list_parser.set_defaults(func=list_records)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
