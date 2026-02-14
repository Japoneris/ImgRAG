"""ChromaDB-based embedding storage for images.

Each embedding model gets its own collection to ensure consistent vector dimensions.
"""

import chromadb
import numpy as np
from pathlib import Path
from typing import Optional


class EmbeddingDatabase:
    """Manages image embeddings in ChromaDB with one collection per model."""

    def __init__(self, db_path: str | Path = "data/embeddings"):
        """Initialize the ChromaDB client with persistent storage.

        Args:
            db_path: Directory for ChromaDB persistent storage
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.db_path))

    def _get_collection(self, model_name: str) -> chromadb.Collection:
        """Get or create a collection for a specific embedding model.

        Args:
            model_name: Name of the embedding model (e.g., 'clip-vit-base')

        Returns:
            ChromaDB collection for this model
        """
        # Sanitize model name for collection name (ChromaDB has restrictions)
        safe_name = model_name.replace("/", "_").replace(":", "_")
        return self.client.get_or_create_collection(
            name=safe_name,
            metadata={"model": model_name}
        )

    def add_embedding(
        self,
        image_hash: str,
        embedding: list[float],
        model_name: str,
        metadata: Optional[dict] = None,
    ) -> None:
        """Store an embedding for an image.

        Args:
            image_hash: SHA-256 hash of the image (used as ID)
            embedding: Vector embedding from the model
            model_name: Name of the embedding model used
            metadata: Optional additional metadata
        """
        collection = self._get_collection(model_name)

        doc_metadata = metadata or {}
        doc_metadata["image_hash"] = image_hash

        # Upsert to handle updates
        collection.upsert(
            ids=[image_hash],
            embeddings=[embedding],
            metadatas=[doc_metadata],
        )

    def get_embedding(
        self,
        image_hash: str,
        model_name: str,
    ) -> Optional[list[float]]:
        """Retrieve an embedding by image hash.

        Args:
            image_hash: SHA-256 hash of the image
            model_name: Name of the embedding model

        Returns:
            The embedding vector, or None if not found
        """
        collection = self._get_collection(model_name)

        result = collection.get(
            ids=[image_hash],
            include=["embeddings"]
        )

        if result["embeddings"] is not None and len(result["embeddings"]) > 0:
            emb = result["embeddings"][0]
            # Convert numpy array to list if needed
            if hasattr(emb, "tolist"):
                return emb.tolist()
            return list(emb)
        return None

    def search_similar(
        self,
        embedding: list[float],
        model_name: str,
        n_results: int = 10,
    ) -> list[tuple[str, float]]:
        """Find images with similar embeddings.

        Args:
            embedding: Query embedding vector
            model_name: Name of the embedding model
            n_results: Maximum number of results to return

        Returns:
            List of (image_hash, distance) tuples, sorted by similarity
        """
        collection = self._get_collection(model_name)

        results = collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["distances"]
        )

        matches = []
        if results["ids"] and len(results["ids"]) > 0:
            ids = results["ids"][0]
            distances = results["distances"][0] if results["distances"] else [0.0] * len(ids)
            for hash_id, dist in zip(ids, distances):
                matches.append((hash_id, dist))

        return matches

    def search_similar_with_cosine(
        self,
        embedding: list[float],
        model_name: str,
        n_results: int = 10,
    ) -> list[tuple[str, float, float]]:
        """Find images with similar embeddings, returning both L2 distance and cosine similarity.

        Args:
            embedding: Query embedding vector
            model_name: Name of the embedding model
            n_results: Maximum number of results to return

        Returns:
            List of (image_hash, l2_distance, cosine_similarity) tuples, sorted by L2 distance
        """
        collection = self._get_collection(model_name)

        results = collection.query(
            query_embeddings=[embedding],
            n_results=n_results,
            include=["distances", "embeddings"],
        )

        matches = []
        if results["ids"] and len(results["ids"]) > 0:
            ids = results["ids"][0]
            distances = results["distances"][0] if results["distances"] else [0.0] * len(ids)
            result_embeddings = results["embeddings"][0] if results["embeddings"] else []

            query_vec = np.array(embedding)
            query_norm = np.linalg.norm(query_vec)

            for idx, (hash_id, dist) in enumerate(zip(ids, distances)):
                if idx < len(result_embeddings) and query_norm > 0:
                    result_vec = np.array(result_embeddings[idx])
                    result_norm = np.linalg.norm(result_vec)
                    if result_norm > 0:
                        cosine_sim = float(np.dot(query_vec, result_vec) / (query_norm * result_norm))
                    else:
                        cosine_sim = 0.0
                else:
                    cosine_sim = 0.0
                matches.append((hash_id, dist, cosine_sim))

        return matches

    def search_by_hash(
        self,
        query_hash: str,
        model_name: str,
        n_results: int = 10,
    ) -> list[tuple[str, float]]:
        """Find similar images given an image hash.

        First retrieves the embedding for the given hash, then searches for similar.

        Args:
            query_hash: SHA-256 hash of the query image
            model_name: Name of the embedding model
            n_results: Maximum number of results to return

        Returns:
            List of (image_hash, distance) tuples, sorted by similarity
        """
        embedding = self.get_embedding(query_hash, model_name)
        if embedding is None:
            return []

        # Search and exclude the query image itself
        results = self.search_similar(embedding, model_name, n_results + 1)
        return [(h, d) for h, d in results if h != query_hash][:n_results]

    def delete_embedding(self, image_hash: str, model_name: str) -> bool:
        """Delete an embedding by image hash.

        Args:
            image_hash: SHA-256 hash of the image
            model_name: Name of the embedding model

        Returns:
            True if deleted, False if not found
        """
        collection = self._get_collection(model_name)

        # Check if exists first
        existing = collection.get(ids=[image_hash])
        if not existing["ids"]:
            return False

        collection.delete(ids=[image_hash])
        return True

    def list_models(self) -> list[str]:
        """List all embedding models with stored embeddings.

        Returns:
            List of model names
        """
        collections = self.client.list_collections()
        models = []
        for col in collections:
            metadata = col.metadata or {}
            model = metadata.get("model", col.name)
            models.append(model)
        return models

    def count(self, model_name: str) -> int:
        """Count embeddings for a specific model.

        Args:
            model_name: Name of the embedding model

        Returns:
            Number of embeddings stored
        """
        collection = self._get_collection(model_name)
        return collection.count()

    def get_all_embeddings(self, model_name: str) -> dict[str, list[float]]:
        """Fetch all embeddings for a model in one batch.

        Args:
            model_name: Name of the embedding model

        Returns:
            Dictionary mapping image hashes to embedding vectors
        """
        collection = self._get_collection(model_name)
        result = collection.get(include=["embeddings"])

        embeddings = {}
        if result["ids"] and result["embeddings"] is not None and len(result["embeddings"]) > 0:
            for hash_id, emb in zip(result["ids"], result["embeddings"]):
                if hasattr(emb, "tolist"):
                    embeddings[hash_id] = emb.tolist()
                else:
                    embeddings[hash_id] = list(emb)
        return embeddings

    def list_hashes(self, model_name: str, limit: int = 100) -> list[str]:
        """List image hashes stored for a model.

        Args:
            model_name: Name of the embedding model
            limit: Maximum number of hashes to return

        Returns:
            List of image hashes
        """
        collection = self._get_collection(model_name)
        result = collection.get(limit=limit)
        return result["ids"] if result["ids"] else []
