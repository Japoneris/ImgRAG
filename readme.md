# Image RAG

**Scenario**:

You have images on your computer, that are in folders, subfolders.
You may move it, classify them differently.
Possibly, you may rescale them, do minor edits.

The tool helps you to search accros your images, whatever you do with.

# How it works

## Indexing phase

- Compute the embedding of an image
- Compute the hash of the image
- Store (embedding, hash) into a RAG db (chromaDB here)

## Path indexing

Files might be move here and there.
Before searching accross files, you need to compute (path, hash), so when getting a image match, you can get the raw image.

## Seach / Retrieval Phase

Upload an image (a rescaled version or not).
It computes the embedding and search accross the RAG DB.

For the embedding, we use [dinov2-small](https://huggingface.co/facebook/dinov2-small)

To do the embedding, we connect to a local openai like embedding server.


# How to Run?

See the guide [how to use](how_to_use.md)

# Environment Variables

You need to configure a few env variables:

```sh
# Model you want to use for embedding
# URL of the server
EMBEDDING_MODEL=dinov2-small
EMBEDDING_API_URL=http://0.0.0.0:8000

# For the streamlit app, multichoice
EMBEDDING_MODELS='dinov2-small,dinov2-base,dinov2-large'
```

# TODO list


- Add a sample code to run a minimal server if needed (as my server is not public and implementation for image embedding is not standard)
- Improve UX to run the indexing. 
