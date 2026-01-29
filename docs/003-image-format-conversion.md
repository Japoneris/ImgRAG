# Image Format Conversion

## Overview

All images are automatically converted to PNG format before being sent to the embedding API. This ensures consistent image format across different input types.

## Data URL Format

Images are sent to the API as data URLs:

```
data:image/png;base64,{base64_encoded_data}
```

**Example:**
```
data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAIAAAD...
```

## Conversion Flow

```
Input Image (any format)
         │
         ▼
    Read as bytes
         │
         ▼
   PIL.Image.open()
         │
         ▼
   Convert to RGB (if RGBA/P mode)
         │
         ▼
   Save as PNG to buffer
         │
         ▼
   Base64 encode
         │
         ▼
   Format as data URL
         │
         ▼
   data:image/png;base64,{data}
```

## API Request Format

```json
{
  "image": "data:image/png;base64,iVBORw0KGgo...",
  "model": "model-name"
}
```

## Supported Input Formats

Any format supported by PIL/Pillow:
- PNG
- JPEG / JPG
- BMP
- GIF
- WebP
- TIFF

## Helper Functions

### `convert_to_png_base64(image_bytes)`

Converts raw image bytes to PNG format and returns base64-encoded string.

```python
from src.embedding_api import convert_to_png_base64

with open("photo.jpg", "rb") as f:
    png_b64 = convert_to_png_base64(f.read())
```

### `format_image_data_url(png_base64)`

Formats base64 PNG data as a data URL.

```python
from src.embedding_api import format_image_data_url

data_url = format_image_data_url(png_b64)
# Returns: "data:image/png;base64,iVBORw0KGgo..."
```

## Why PNG?

- **Consistency**: Single format for the embedding API
- **Lossless**: No quality loss during conversion
- **Compatibility**: Widely supported format

## Usage Example

```python
from src.embedding_api import EmbeddingAPI

api = EmbeddingAPI("http://localhost:8000")

# JPEG file - automatically converted to PNG
embedding = api.get_embedding("photo.jpg", model="clip")

# PNG file - converted anyway for consistency
embedding = api.get_embedding("image.png", model="clip")

# From bytes
with open("image.bmp", "rb") as f:
    embedding = api.get_embedding_from_bytes(f.read(), model="clip")
```

## Dependencies

- `Pillow` - Image processing and format conversion

## Files Modified

- `src/api/embedding_api.py` - Added PNG conversion functions
