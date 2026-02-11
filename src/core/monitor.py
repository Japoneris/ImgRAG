"""Image directory monitoring and database synchronization."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .scanner import ImageScanner
from .models import ImageRecord
from ..storage.database import ImageDatabase
from ..storage.embedding_db import EmbeddingDatabase
from ..api.embedding_api import EmbeddingAPI, EmbeddingAPIError


@dataclass
class SyncReport:
    """Report of changes made during synchronization."""

    new_images: list[str] = field(default_factory=list)  # hashes added
    removed_images: list[str] = field(default_factory=list)  # hashes removed
    embeddings_computed: list[str] = field(default_factory=list)  # hashes that got new embeddings
    orphan_embeddings_removed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        lines = []
        if self.new_images:
            lines.append(f"New images added: {len(self.new_images)}")
        if self.removed_images:
            lines.append(f"Images removed: {len(self.removed_images)}")
        if self.embeddings_computed:
            lines.append(f"Embeddings computed: {len(self.embeddings_computed)}")
        if self.orphan_embeddings_removed:
            lines.append(f"Orphan embeddings removed: {len(self.orphan_embeddings_removed)}")
        if self.errors:
            lines.append(f"Errors: {len(self.errors)}")
        if not lines:
            lines.append("No changes")
        return "\n".join(lines)


@dataclass
class ConsistencyReport:
    """Report of consistency check between databases."""

    images_not_in_db: dict[str, str] = field(default_factory=dict)  # hash -> path
    images_missing_from_disk: list[str] = field(default_factory=list)  # hashes in DB but not on disk
    missing_embeddings: list[str] = field(default_factory=list)  # hashes in hash DB without embeddings
    orphan_embeddings: list[str] = field(default_factory=list)  # hashes in embedding DB without hash DB entry

    def has_issues(self) -> bool:
        return bool(
            self.images_not_in_db
            or self.images_missing_from_disk
            or self.missing_embeddings
            or self.orphan_embeddings
        )

    def __str__(self) -> str:
        lines = []
        if self.images_not_in_db:
            lines.append(f"Images on disk not in hash DB: {len(self.images_not_in_db)}")
        if self.images_missing_from_disk:
            lines.append(f"Images in hash DB missing from disk: {len(self.images_missing_from_disk)}")
        if self.missing_embeddings:
            lines.append(f"Images in hash DB without embeddings: {len(self.missing_embeddings)}")
        if self.orphan_embeddings:
            lines.append(f"Embeddings without corresponding hash DB entry: {len(self.orphan_embeddings)}")
        if not lines:
            lines.append("All databases are consistent")
        return "\n".join(lines)


class ImageMonitor:
    """Monitors configured directories and keeps databases in sync."""

    def __init__(
        self,
        config: dict,
        db: ImageDatabase,
        embedding_db: EmbeddingDatabase,
        api: EmbeddingAPI,
        model: str,
    ):
        """Initialize the image monitor.

        Args:
            config: Configuration dict with 'paths' and optional 'recursive'
            db: ImageDatabase for hash/metadata storage
            embedding_db: EmbeddingDatabase for embeddings
            api: EmbeddingAPI for computing embeddings
            model: Embedding model name
        """
        self.config = config
        self.db = db
        self.embedding_db = embedding_db
        self.api = api
        self.model = model
        self.paths = [Path(p) for p in config.get("paths", [])]
        self.recursive = config.get("recursive", True)

    def scan_configured_paths(self) -> dict[str, str]:
        """Scan all configured paths for images.

        Returns:
            Dictionary mapping image hashes to their file paths
        """
        all_images: dict[str, str] = {}

        for path in self.paths:
            if not path.exists():
                continue
            if path.is_file():
                if ImageScanner.is_image(path):
                    file_hash = ImageScanner.compute_hash(path)
                    all_images[file_hash] = str(path.absolute())
            else:
                images = ImageScanner.scan_directory(path, recursive=self.recursive)
                all_images.update(images)

        return all_images

    def detect_changes(self) -> tuple[dict[str, str], list[str]]:
        """Detect changes between disk and hash DB.

        Returns:
            Tuple of (new_images: {hash: path}, removed_hashes: list)
        """
        disk_images = self.scan_configured_paths()
        disk_hashes = set(disk_images.keys())

        db_records = self.db.list_all()
        db_hashes = {r.hash for r in db_records}

        # New images: on disk but not in DB
        new_hashes = disk_hashes - db_hashes
        new_images = {h: disk_images[h] for h in new_hashes}

        # Removed images: in DB but not on disk
        removed_hashes = list(db_hashes - disk_hashes)

        return new_images, removed_hashes

    def check_consistency(self) -> ConsistencyReport:
        """Check consistency between disk, hash DB, and embedding DB.

        Returns:
            ConsistencyReport with detected issues
        """
        report = ConsistencyReport()

        # Get all data
        disk_images = self.scan_configured_paths()
        disk_hashes = set(disk_images.keys())

        db_records = self.db.list_all()
        db_hashes = {r.hash for r in db_records}

        embedding_hashes = set(self._get_all_embedding_hashes())

        # Images on disk not in hash DB
        for h in disk_hashes - db_hashes:
            report.images_not_in_db[h] = disk_images[h]

        # Images in hash DB missing from disk
        report.images_missing_from_disk = list(db_hashes - disk_hashes)

        # Images in hash DB without embeddings
        report.missing_embeddings = list(db_hashes - embedding_hashes)

        # Embeddings without corresponding hash DB entry
        report.orphan_embeddings = list(embedding_hashes - db_hashes)

        return report

    def _get_all_embedding_hashes(self) -> list[str]:
        """Get all hashes stored in embedding DB for current model.

        Note: This fetches in batches to handle large collections.
        """
        # ChromaDB's list_hashes has a limit parameter, so we need to
        # fetch all by getting a count first
        total = self.embedding_db.count(self.model)
        if total == 0:
            return []

        # Fetch all hashes (ChromaDB get without limit gets all)
        collection = self.embedding_db._get_collection(self.model)
        result = collection.get(include=[])
        return result["ids"] if result["ids"] else []

    def sync(
        self,
        dry_run: bool = False,
        auto_confirm: bool = False,
        confirm_callback: Optional[callable] = None,
    ) -> SyncReport:
        """Perform full synchronization.

        Args:
            dry_run: If True, report what would happen without making changes
            auto_confirm: If True, skip deletion confirmation
            confirm_callback: Function to call for deletion confirmation.
                              Should accept (removed_hashes: list) and return bool.

        Returns:
            SyncReport with changes made
        """
        report = SyncReport()

        # Detect changes
        new_images, removed_hashes = self.detect_changes()

        # Handle removed images (prompt for confirmation)
        if removed_hashes:
            if dry_run:
                report.removed_images = removed_hashes
            elif auto_confirm or (confirm_callback and confirm_callback(removed_hashes)):
                for h in removed_hashes:
                    self.db.delete_by_hash(h)
                    self.embedding_db.delete_embedding(h, self.model)
                report.removed_images = removed_hashes

        # Add new images
        for image_hash, filepath in new_images.items():
            if dry_run:
                report.new_images.append(image_hash)
                report.embeddings_computed.append(image_hash)
                continue

            try:
                # Extract metadata and add to hash DB
                record = ImageScanner.extract_metadata(filepath)
                self.db.add_record(record)
                report.new_images.append(image_hash)

                # Compute and store embedding
                embedding = self.api.get_embedding(filepath, model=self.model)
                metadata = {"filepath": filepath}
                self.embedding_db.add_embedding(image_hash, embedding, self.model, metadata)
                report.embeddings_computed.append(image_hash)

            except EmbeddingAPIError as e:
                report.errors.append(f"Embedding error for {image_hash[:12]}...: {e}")
            except Exception as e:
                report.errors.append(f"Error processing {filepath}: {e}")

        # Run consistency check and auto-fix
        consistency = self.check_consistency()

        # Compute missing embeddings
        for image_hash in consistency.missing_embeddings:
            if image_hash in [r.hash for r in self.db.list_all()]:
                # Need to find the file path
                disk_images = self.scan_configured_paths()
                if image_hash in disk_images:
                    filepath = disk_images[image_hash]
                    if dry_run:
                        report.embeddings_computed.append(image_hash)
                        continue

                    try:
                        embedding = self.api.get_embedding(filepath, model=self.model)
                        metadata = {"filepath": filepath}
                        self.embedding_db.add_embedding(image_hash, embedding, self.model, metadata)
                        report.embeddings_computed.append(image_hash)
                    except EmbeddingAPIError as e:
                        report.errors.append(f"Embedding error for {image_hash[:12]}...: {e}")

        # Remove orphan embeddings
        for image_hash in consistency.orphan_embeddings:
            if dry_run:
                report.orphan_embeddings_removed.append(image_hash)
            else:
                self.embedding_db.delete_embedding(image_hash, self.model)
                report.orphan_embeddings_removed.append(image_hash)

        return report
