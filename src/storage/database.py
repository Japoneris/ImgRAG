"""SQLite database layer for image records."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..core.models import ImageRecord


class ImageDatabase:
    """Manages image metadata storage in SQLite."""

    def __init__(self, db_path: str | Path = "data/images.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Create the images table if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS images (
                    hash TEXT PRIMARY KEY,
                    width INTEGER NOT NULL,
                    height INTEGER NOT NULL,
                    size INTEGER NOT NULL,
                    mimetype TEXT NOT NULL,
                    created_at TEXT,
                    ingested_at TEXT
                )
            """)
            conn.commit()

    def add_record(self, record: ImageRecord) -> None:
        """Insert or update an image record."""
        # Set ingestion time if not already set
        if record.ingested_at is None:
            record.ingested_at = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO images (hash, width, height, size, mimetype, created_at, ingested_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                record.hash,
                record.width,
                record.height,
                record.size,
                record.mimetype,
                record.created_at.isoformat() if record.created_at else None,
                record.ingested_at.isoformat() if record.ingested_at else None,
            ))
            conn.commit()

    def _row_to_record(self, row) -> ImageRecord:
        """Convert a database row to an ImageRecord."""
        created_at = datetime.fromisoformat(row[5]) if row[5] else None
        ingested_at = datetime.fromisoformat(row[6]) if row[6] else None
        return ImageRecord(
            hash=row[0],
            width=row[1],
            height=row[2],
            size=row[3],
            mimetype=row[4],
            created_at=created_at,
            ingested_at=ingested_at,
        )

    def get_by_hash(self, hash: str) -> Optional[ImageRecord]:
        """Retrieve an image record by its hash (exact match)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT hash, width, height, size, mimetype, created_at, ingested_at FROM images WHERE hash = ?",
                (hash,)
            )
            row = cursor.fetchone()
            if row:
                return self._row_to_record(row)
            return None

    def search_by_prefix(self, hash_prefix: str) -> list[ImageRecord]:
        """Find all image records whose hash starts with the given prefix."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT hash, width, height, size, mimetype, created_at, ingested_at FROM images WHERE hash LIKE ?",
                (hash_prefix + "%",)
            )
            return [self._row_to_record(row) for row in cursor.fetchall()]

    def list_all(self) -> list[ImageRecord]:
        """List all image records in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT hash, width, height, size, mimetype, created_at, ingested_at FROM images"
            )
            return [self._row_to_record(row) for row in cursor.fetchall()]

    def delete_by_hash(self, hash: str) -> bool:
        """Delete an image record by its hash. Returns True if deleted."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM images WHERE hash = ?", (hash,))
            conn.commit()
            return cursor.rowcount > 0

    def count(self) -> int:
        """Return the number of records in the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM images")
            return cursor.fetchone()[0]
