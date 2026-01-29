# Image Embedding Storage

We want to make a specific database system.

Images might be stored in folder, may be change of location.
Therefore, we cannot rely on its path.
However, we can rely on its hash, which does not change.
Therefore, we want to store in a DB, a records which looks like this:

- hash
- width
- height
- size (bytes)
- mimetype

We want to be able to retrieve an image at any time.
We will be given a hash, and we need to find out.

So, we need to implement that:
- Ingestion system (add records in the DB)
- Search system: Compute the hash of the images in the folder/subfolders to keep it in memory, and address requests. Maybe in a static way: Ask to recompute the image tree (store as a json,) and then for each query, read the file.

We will have very infrequent access, so file DB are OK.

