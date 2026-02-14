# 011 - Embedding Analysis & Visualization

Adds tools to analyze and visualize the high-dimensional embedding space.

## Overview

Two-step workflow:
1. **Analyze**: Extract all embeddings for a model, reduce to 2D via t-SNE or UMAP, enrich with metadata, save to JSON.
2. **Visualize**: Interactive Bokeh scatter plot showing the 2D projection with image thumbnails on hover.

## CLI Commands

```bash
# Run dimensionality reduction (default: t-SNE)
imgdb-full analyze --method tsne --output data/analysis.json
imgdb-full analyze --method umap --output data/analysis.json

# Launch interactive Bokeh server (click points to open folder)
imgdb-full visualize data/analysis.json

# Generate standalone HTML file (no server needed)
imgdb-full visualize data/analysis.json --static data/analysis.html
```

## Visualization Features

- Scatter plot colored by file extension
- Hover tooltip: thumbnail, filename, folder path, dimensions, file size
- **Bokeh server mode**: click a point to open its folder in the file manager
- **Static HTML mode**: click a point to copy its folder path to clipboard

## Files

- `src/analysis/embedding_analyzer.py` — dimensionality reduction pipeline
- `src/analysis/visualizer.py` — Bokeh server visualization
- `src/analysis/viewer.py` — standalone HTML generator

## Dependencies

- `scikit-learn` (t-SNE)
- `umap-learn` (UMAP)
- `bokeh` (visualization)
