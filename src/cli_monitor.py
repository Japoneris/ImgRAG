"""CLI for monitoring image directories and keeping databases in sync.

Environment variables:
    EMBEDDING_API_URL: Base URL of the embedding API server (required for sync)
    EMBEDDING_MODEL: Model name to use (default: "default")
    EMBEDDING_API_KEY: Optional API key for authentication
"""

import argparse
import os
import sys
from pathlib import Path

import yaml

from .api.embedding_api import EmbeddingAPI
from .core.monitor import ImageMonitor, ConsistencyReport, SyncReport
from .storage.database import ImageDatabase
from .storage.embedding_db import EmbeddingDatabase


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


def confirm_deletion(removed_hashes: list[str]) -> bool:
    """Prompt user to confirm deletion of removed images."""
    print(f"\nThe following {len(removed_hashes)} images will be removed from databases:")
    for h in removed_hashes[:10]:
        print(f"  {h[:16]}...")
    if len(removed_hashes) > 10:
        print(f"  ... and {len(removed_hashes) - 10} more")

    while True:
        response = input("\nProceed with deletion? [y/N] ").strip().lower()
        if response in ("y", "yes"):
            return True
        if response in ("n", "no", ""):
            return False
        print("Please enter 'y' or 'n'")


def cmd_sync(args):
    """Perform full synchronization."""
    config = load_config(args.config)
    api = get_api_client()
    model = get_model_name()
    db = ImageDatabase(args.database)
    embed_db = EmbeddingDatabase(args.embeddings_db)

    monitor = ImageMonitor(config, db, embed_db, api, model)

    # Validate configured paths
    for path in monitor.paths:
        if not path.exists():
            print(f"Warning: Configured path does not exist: {path}")

    if args.dry_run:
        print("=== DRY RUN (no changes will be made) ===\n")

    print(f"Scanning {len(monitor.paths)} configured path(s)...")
    print(f"Model: {model}")
    print()

    def confirm_callback(removed_hashes: list[str]) -> bool:
        if args.yes:
            return True
        return confirm_deletion(removed_hashes)

    report = monitor.sync(
        dry_run=args.dry_run,
        auto_confirm=args.yes,
        confirm_callback=confirm_callback,
    )

    print("\n=== Sync Report ===")
    print(report)

    if report.new_images:
        print("\nNew images:")
        for h in report.new_images[:10]:
            print(f"  {h[:16]}...")
        if len(report.new_images) > 10:
            print(f"  ... and {len(report.new_images) - 10} more")

    if report.errors:
        print("\nErrors:")
        for err in report.errors:
            print(f"  {err}")


def cmd_check(args):
    """Perform read-only consistency check."""
    config = load_config(args.config)
    model = get_model_name()
    db = ImageDatabase(args.database)
    embed_db = EmbeddingDatabase(args.embeddings_db)

    # Create monitor without API (not needed for check)
    monitor = ImageMonitor(config, db, embed_db, api=None, model=model)

    print(f"Checking consistency for {len(monitor.paths)} configured path(s)...")
    print(f"Model: {model}")
    print()

    report = monitor.check_consistency()

    print("=== Consistency Report ===")
    print(report)

    if report.images_not_in_db:
        print("\nImages on disk not in hash DB:")
        for h, path in list(report.images_not_in_db.items())[:10]:
            print(f"  {h[:12]}... -> {path}")
        if len(report.images_not_in_db) > 10:
            print(f"  ... and {len(report.images_not_in_db) - 10} more")

    if report.images_missing_from_disk:
        print("\nImages in hash DB missing from disk:")
        for h in report.images_missing_from_disk[:10]:
            print(f"  {h[:16]}...")
        if len(report.images_missing_from_disk) > 10:
            print(f"  ... and {len(report.images_missing_from_disk) - 10} more")

    if report.missing_embeddings:
        print("\nImages in hash DB without embeddings:")
        for h in report.missing_embeddings[:10]:
            print(f"  {h[:16]}...")
        if len(report.missing_embeddings) > 10:
            print(f"  ... and {len(report.missing_embeddings) - 10} more")

    if report.orphan_embeddings:
        print("\nEmbeddings without corresponding hash DB entry:")
        for h in report.orphan_embeddings[:10]:
            print(f"  {h[:16]}...")
        if len(report.orphan_embeddings) > 10:
            print(f"  ... and {len(report.orphan_embeddings) - 10} more")

    if report.has_issues():
        print("\nRun 'sync' command to fix these issues.")
        sys.exit(1)


def cmd_init(args):
    """Generate sample configuration file."""
    config_path = Path(args.config)

    if config_path.exists() and not args.force:
        print(f"Error: File already exists: {config_path}")
        print("Use --force to overwrite")
        sys.exit(1)

    sample_config = """# Image monitor configuration
# List directories to monitor for images

paths:
  - /path/to/images
  - /another/path/to/images

# Whether to scan subdirectories (default: true)
recursive: true
"""

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        f.write(sample_config)

    print(f"Created sample config: {config_path}")
    print("Edit the 'paths' list to add your image directories.")


def main():
    parser = argparse.ArgumentParser(
        description="Monitor image directories and keep databases in sync",
        epilog="Environment variables: EMBEDDING_API_URL (required), EMBEDDING_MODEL, EMBEDDING_API_KEY",
    )
    parser.add_argument(
        "--database",
        "-d",
        default="data/images.db",
        help="Path to SQLite metadata database (default: data/images.db)",
    )
    parser.add_argument(
        "--embeddings-db",
        "-e",
        default="data/embeddings",
        help="Path to embeddings database (default: data/embeddings)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # sync command
    sync_parser = subparsers.add_parser(
        "sync", help="Sync configured directories with databases"
    )
    sync_parser.add_argument("config", help="Path to YAML config file")
    sync_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes",
    )
    sync_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip deletion confirmation prompt",
    )
    sync_parser.set_defaults(func=cmd_sync)

    # check command
    check_parser = subparsers.add_parser(
        "check", help="Read-only consistency check"
    )
    check_parser.add_argument("config", help="Path to YAML config file")
    check_parser.set_defaults(func=cmd_check)

    # init command
    init_parser = subparsers.add_parser(
        "init", help="Generate sample config file"
    )
    init_parser.add_argument("config", help="Path to config file to create")
    init_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Overwrite existing file",
    )
    init_parser.set_defaults(func=cmd_init)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
