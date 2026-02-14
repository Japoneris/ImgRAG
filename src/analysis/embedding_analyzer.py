"""Embedding analysis: dimensionality reduction and metadata enrichment."""

import json
import numpy as np
from pathlib import Path
from typing import Optional

from ..storage.embedding_db import EmbeddingDatabase
from ..storage.database import ImageDatabase
from ..core.scanner import ImageScanner


def get_all_embeddings(
    embed_db: EmbeddingDatabase,
    model_name: str,
) -> dict[str, list[float]]:
    """Fetch all embeddings for a model.

    Args:
        embed_db: Embedding database instance
        model_name: Name of the embedding model

    Returns:
        Dictionary mapping image hashes to embedding vectors
    """
    return embed_db.get_all_embeddings(model_name)


def reduce_dimensions(
    embeddings: dict[str, list[float]],
    method: str = "tsne",
    **kwargs,
) -> dict[str, tuple[float, float]]:
    """Reduce embedding vectors to 2D using t-SNE or UMAP.

    Args:
        embeddings: Dictionary mapping hashes to embedding vectors
        method: "tsne" or "umap"
        **kwargs: Extra arguments passed to the reducer

    Returns:
        Dictionary mapping hashes to (x, y) coordinates
    """
    if not embeddings:
        return {}

    hashes = list(embeddings.keys())
    matrix = np.array([embeddings[h] for h in hashes])

    if method == "tsne":
        from sklearn.manifold import TSNE

        perplexity = kwargs.get("perplexity", min(30, len(hashes) - 1))
        reducer = TSNE(
            n_components=2,
            perplexity=perplexity,
            random_state=42,
        )
    elif method == "umap":
        import umap

        n_neighbors = kwargs.get("n_neighbors", min(15, len(hashes) - 1))
        reducer = umap.UMAP(
            n_components=2,
            n_neighbors=n_neighbors,
            random_state=42,
        )
    else:
        raise ValueError(f"Unknown method: {method}. Use 'tsne' or 'umap'.")

    coords = reducer.fit_transform(matrix)

    return {h: (float(coords[i, 0]), float(coords[i, 1])) for i, h in enumerate(hashes)}


def build_analysis_data(
    embed_db: EmbeddingDatabase,
    img_db: ImageDatabase,
    index_path: str | Path,
    model_name: str,
    method: str = "tsne",
    **kwargs,
) -> dict:
    """Run the full analysis pipeline: fetch, reduce, enrich.

    Args:
        embed_db: Embedding database
        img_db: Image metadata database
        index_path: Path to the hash->filepath index JSON
        model_name: Embedding model name
        method: Dimensionality reduction method ("tsne" or "umap")
        **kwargs: Extra arguments for the reducer

    Returns:
        Analysis data dict ready for JSON serialization
    """
    # 1. Fetch embeddings
    embeddings = get_all_embeddings(embed_db, model_name)
    if not embeddings:
        return {"model": model_name, "method": method, "count": 0, "points": []}

    print(f"Fetched {len(embeddings)} embeddings for model '{model_name}'")

    # 2. Reduce dimensions
    print(f"Running {method.upper()} dimensionality reduction...")
    coords = reduce_dimensions(embeddings, method=method, **kwargs)

    # 3. Load file index
    index = {}
    meta = {}
    index_path = Path(index_path)
    if index_path.exists():
        index, meta = ImageScanner.load_index(index_path)

    # 4. Enrich with metadata
    points = []
    for h, (x, y) in coords.items():
        point = {
            "hash": h,
            "x": x,
            "y": y,
            "filepath": None,
            "width": None,
            "height": None,
            "size": None,
            "mimetype": None,
        }

        # File path from index
        matches = ImageScanner.find_by_hash(h, index, meta)
        if matches:
            point["filepath"] = matches[0][1]

        # Metadata from SQLite
        record = img_db.get_by_hash(h)
        if record:
            point["width"] = record.width
            point["height"] = record.height
            point["size"] = record.size
            point["mimetype"] = record.mimetype

        points.append(point)

    return {
        "model": model_name,
        "method": method,
        "count": len(points),
        "points": points,
    }


def save_analysis(data: dict, output_path: str | Path) -> None:
    """Save analysis results to JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Analysis saved to {output_path} ({data['count']} points)")


def load_analysis(path: str | Path) -> dict:
    """Load analysis results from JSON."""
    with open(path, "r") as f:
        return json.load(f)
