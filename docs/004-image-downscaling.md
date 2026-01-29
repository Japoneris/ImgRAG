# Image Downscaling for Embeddings

## Overview

Large images are automatically downscaled before being sent to the embedding API. This improves efficiency by reducing:
- Network transfer time (smaller base64 payloads)
- API processing time
- Memory usage

Embedding models typically work on fixed-size inputs (e.g., 224x224 or 384x384 pixels), so sending very large images provides no quality benefit.

## Default Behavior

By default, images exceeding 1024 pixels in width or height are downscaled while maintaining aspect ratio.

```
4000x3000 image → 1024x768 (downscaled)
800x600 image   → 800x600  (unchanged)
1024x1024 image → 1024x1024 (unchanged)
```

## Configuration

### EmbeddingAPI

```python
from src.embedding_api import EmbeddingAPI

# Default: max 1024px
api = EmbeddingAPI("http://localhost:8000")

# Custom max dimension
api = EmbeddingAPI("http://localhost:8000", max_image_dimension=512)

# Disable downscaling (send original size)
api = EmbeddingAPI("http://localhost:8000", max_image_dimension=None)
```

### MockEmbeddingAPI

```python
from src.embedding_api import MockEmbeddingAPI

# Default: max 1024px
mock = MockEmbeddingAPI()

# Custom max dimension
mock = MockEmbeddingAPI(dimensions=512, max_image_dimension=768)

# Disable downscaling
mock = MockEmbeddingAPI(max_image_dimension=None)
```

### Direct Function Usage

```python
from src.embedding_api import convert_to_png_base64, downscale_image, DEFAULT_MAX_DIMENSION
from PIL import Image

# Convert with default downscaling (1024px max)
with open("large_image.jpg", "rb") as f:
    png_b64 = convert_to_png_base64(f.read())

# Convert with custom max dimension
with open("large_image.jpg", "rb") as f:
    png_b64 = convert_to_png_base64(f.read(), max_dimension=512)

# Convert without downscaling
with open("large_image.jpg", "rb") as f:
    png_b64 = convert_to_png_base64(f.read(), max_dimension=None)

# Downscale PIL Image directly
img = Image.open("large_image.jpg")
downscaled = downscale_image(img, max_dimension=768)
```

## Processing Flow

```
Input Image (any format)
         |
         v
    Read as bytes
         |
         v
   PIL.Image.open()
         |
         v
   Check dimensions
         |
    +----+----+
    |         |
    v         v
 > max?    <= max?
    |         |
    v         |
 Downscale   |
 (LANCZOS)   |
    |         |
    +----+----+
         |
         v
   Convert to RGB (if needed)
         |
         v
   Save as PNG to buffer
         |
         v
   Base64 encode
         |
         v
   data:image/png;base64,{data}
```

## Downscaling Algorithm

- **Method**: LANCZOS resampling (high quality)
- **Aspect Ratio**: Preserved (no distortion)
- **Direction**: Downscale only (never upscales small images)
- **Target**: Longest edge fits within max_dimension

### Example Calculations

| Original Size | Max Dimension | Result |
|--------------|---------------|--------|
| 4000x3000 | 1024 | 1024x768 |
| 1920x1080 | 1024 | 1024x576 |
| 800x600 | 1024 | 800x600 (unchanged) |
| 500x2000 | 1024 | 256x1024 |

## Helper Functions

### `downscale_image(img, max_dimension)`

Downscales a PIL Image if it exceeds the maximum dimension.

```python
from src.embedding_api import downscale_image
from PIL import Image

img = Image.open("photo.jpg")
# Returns original if within limits, downscaled copy otherwise
resized = downscale_image(img, max_dimension=1024)
```

### `convert_to_png_base64(image_data, max_dimension)`

Converts image bytes to PNG base64, with optional downscaling.

```python
from src.embedding_api import convert_to_png_base64

with open("photo.jpg", "rb") as f:
    # With downscaling (default)
    png_b64 = convert_to_png_base64(f.read())

    # Without downscaling
    png_b64_full = convert_to_png_base64(f.read(), max_dimension=None)
```

## Constants

### `DEFAULT_MAX_DIMENSION`

Default maximum image dimension: `1024` pixels.

```python
from src.embedding_api import DEFAULT_MAX_DIMENSION

print(DEFAULT_MAX_DIMENSION)  # 1024
```

## Performance Impact

For a 4000x3000 JPEG image:

| Metric | Original | Downscaled (1024px) |
|--------|----------|---------------------|
| Resolution | 12 MP | 0.79 MP |
| PNG size | ~35 MB | ~2.3 MB |
| Base64 size | ~47 MB | ~3.1 MB |
| Transfer time | Higher | ~15x faster |

## Dependencies

- `Pillow` - Image processing and resampling

## Files Modified

- `src/api/embedding_api.py` - Added downscaling function and max_dimension parameter
