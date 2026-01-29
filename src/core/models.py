"""Data models for image records."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ImageRecord:
    """Represents metadata for a stored image."""

    hash: str
    width: int
    height: int
    size: int  # bytes
    mimetype: str
    created_at: Optional[datetime] = None  # file creation/modification date
    ingested_at: Optional[datetime] = None  # when added to database

    def to_dict(self) -> dict:
        return {
            "hash": self.hash,
            "width": self.width,
            "height": self.height,
            "size": self.size,
            "mimetype": self.mimetype,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "ingested_at": self.ingested_at.isoformat() if self.ingested_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ImageRecord":
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        ingested_at = None
        if data.get("ingested_at"):
            ingested_at = datetime.fromisoformat(data["ingested_at"])
        return cls(
            hash=data["hash"],
            width=data["width"],
            height=data["height"],
            size=data["size"],
            mimetype=data["mimetype"],
            created_at=created_at,
            ingested_at=ingested_at,
        )
