# 012 - Cosine Similarity Option in Search

## Summary

Added the ability to display **cosine similarity** (values between -1 and 1) alongside the existing L2 Euclidean distance in the image search page.

## Details

- A new **Metric** radio button in the sidebar lets users choose between "L2 Distance" and "Cosine Similarity".
- Cosine similarity is computed post-hoc from stored embeddings (no re-indexing needed).
- Results are still ordered by ChromaDB's L2 nearest neighbor search; only the displayed score changes.
- Typical cosine similarity values: ~1.0 for very similar images, ~0 for unrelated, ~-1 for opposite.

## Files Modified

- `src/storage/embedding_db.py`: Added `search_similar_with_cosine()` method.
- `app/pages/2_Search.py`: Added metric selector and conditional display logic.
