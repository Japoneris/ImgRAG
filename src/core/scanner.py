"""Image scanning and metadata extraction."""

import hashlib
import json
import mimetypes
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image

from .models import ImageRecord


class ImageScanner:
    """Scans directories for images and extracts metadata."""

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".tif"}

    @staticmethod
    def compute_hash(filepath: str | Path) -> str:
        """Compute SHA-256 hash of file contents."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def get_file_creation_date(filepath: Path) -> datetime:
        """Get the file creation date (or modification date as fallback)."""
        stat = filepath.stat()
        # Try to get birth time (creation time) if available
        # On Linux, st_birthtime may not be available, fall back to st_mtime
        try:
            timestamp = stat.st_birthtime
        except AttributeError:
            # st_birthtime not available, use modification time
            timestamp = stat.st_mtime
        return datetime.fromtimestamp(timestamp)

    @staticmethod
    def extract_metadata(filepath: str | Path) -> ImageRecord:
        """Extract all metadata from an image file."""
        filepath = Path(filepath)

        # Compute hash
        file_hash = ImageScanner.compute_hash(filepath)

        # Get file size
        file_size = filepath.stat().st_size

        # Get dimensions using PIL
        with Image.open(filepath) as img:
            width, height = img.size

        # Get mimetype
        mimetype, _ = mimetypes.guess_type(str(filepath))
        if mimetype is None:
            mimetype = "application/octet-stream"

        # Get file creation date
        created_at = ImageScanner.get_file_creation_date(filepath)

        return ImageRecord(
            hash=file_hash,
            width=width,
            height=height,
            size=file_size,
            mimetype=mimetype,
            created_at=created_at,
        )

    @classmethod
    def is_image(cls, filepath: str | Path) -> bool:
        """Check if a file is an image based on extension."""
        return Path(filepath).suffix.lower() in cls.IMAGE_EXTENSIONS

    @classmethod
    def scan_directory(
        cls,
        path: str | Path,
        recursive: bool = True,
        relative: bool = False,
        base_path: Path | None = None,
    ) -> dict[str, str]:
        """
        Scan a directory for images and return hash -> filepath mapping.

        Args:
            path: Directory to scan
            recursive: Whether to scan subdirectories
            relative: If True, store paths relative to base_path
            base_path: Base directory for relative paths (defaults to path)

        Returns:
            Dictionary mapping image hashes to their file paths
        """
        path = Path(path).resolve()
        if base_path is None:
            base_path = path
        else:
            base_path = Path(base_path).resolve()

        index: dict[str, str] = {}

        if recursive:
            files = path.rglob("*")
        else:
            files = path.glob("*")

        for filepath in files:
            if filepath.is_file() and cls.is_image(filepath):
                try:
                    file_hash = cls.compute_hash(filepath)
                    if relative:
                        index[file_hash] = str(filepath.relative_to(base_path))
                    else:
                        index[file_hash] = str(filepath.absolute())
                except Exception as e:
                    print(f"Warning: Could not process {filepath}: {e}")

        return index

    @classmethod
    def build_index(
        cls,
        path: str | Path,
        output: str | Path = "data/index.json",
        relative: bool = False,
    ) -> dict[str, str]:
        """
        Build and save a hash->filepath index as JSON.

        Args:
            path: Directory to scan
            output: Output JSON file path
            relative: If True, store paths relative to the scanned directory

        Returns:
            The generated index
        """
        index = cls.scan_directory(path, relative=relative)

        output = Path(output)
        output.parent.mkdir(parents=True, exist_ok=True)

        # Store metadata about the index
        index_data = {
            "_meta": {
                "base_path": str(Path(path).resolve()) if relative else None,
                "relative": relative,
            },
            "images": index,
        }

        with open(output, "w") as f:
            json.dump(index_data, f, indent=2)

        return index

    @staticmethod
    def load_index(index_path: str | Path = "data/index.json") -> tuple[dict[str, str], dict]:
        """
        Load a previously built index from JSON.

        Returns:
            Tuple of (images dict, metadata dict)
        """
        with open(index_path, "r") as f:
            data = json.load(f)

        # Handle both old format (flat dict) and new format (with _meta)
        if "_meta" in data:
            return data["images"], data["_meta"]
        else:
            # Legacy format: flat hash->path dict
            return data, {"base_path": None, "relative": False}

    @staticmethod
    def find_by_hash(
        hash_prefix: str,
        index: dict[str, str],
        meta: dict | None = None,
    ) -> list[tuple[str, str]]:
        """
        Find file paths by hash prefix.

        Args:
            hash_prefix: Beginning of the hash to search for
            index: Hash -> filepath mapping
            meta: Index metadata (for resolving relative paths)

        Returns:
            List of (hash, filepath) tuples for all matches.
        """
        matches = []
        base_path = meta.get("base_path") if meta else None

        for full_hash, filepath in index.items():
            if full_hash.startswith(hash_prefix):
                # Resolve relative paths if base_path is set
                if base_path and not Path(filepath).is_absolute():
                    filepath = str(Path(base_path) / filepath)
                matches.append((full_hash, filepath))
        return matches
