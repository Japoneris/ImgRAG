"""Embedding API client for generating image embeddings.

This module provides a client to call an external embedding API.
The API is expected to accept image data and return vector embeddings.
"""

import base64
import io
import requests
from pathlib import Path
from typing import Optional

from PIL import Image

# Default maximum dimension (width or height) for images sent to embedding API
DEFAULT_MAX_DIMENSION = 1024


class EmbeddingAPIError(Exception):
    """Raised when the embedding API returns an error."""
    pass


def downscale_image(
    img: Image.Image,
    max_dimension: int = DEFAULT_MAX_DIMENSION,
) -> Image.Image:
    """Downscale image if it exceeds the maximum dimension.

    Maintains aspect ratio. Only downscales; never upscales images.

    Args:
        img: PIL Image object
        max_dimension: Maximum allowed width or height in pixels

    Returns:
        PIL Image object (downscaled if necessary, original otherwise)
    """
    width, height = img.size

    # No downscaling needed if within limits
    if width <= max_dimension and height <= max_dimension:
        return img

    # Calculate scale factor to fit within max_dimension
    scale = min(max_dimension / width, max_dimension / height)
    new_width = int(width * scale)
    new_height = int(height * scale)

    # Use LANCZOS resampling for high-quality downscaling
    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)


def convert_to_png_base64(
    image_data: bytes,
    max_dimension: Optional[int] = DEFAULT_MAX_DIMENSION,
) -> str:
    """Convert image bytes to PNG format and return as base64.

    Optionally downscales large images before conversion for efficiency.

    Args:
        image_data: Raw image bytes (any supported format)
        max_dimension: Maximum width or height in pixels. Set to None to
            disable downscaling. Defaults to 1024.

    Returns:
        Base64-encoded PNG data
    """
    img = Image.open(io.BytesIO(image_data))

    # Downscale if max_dimension is set
    if max_dimension is not None:
        img = downscale_image(img, max_dimension)

    # Convert to RGB if necessary (e.g., RGBA, P mode)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def format_image_data_url(png_base64: str) -> str:
    """Format PNG base64 data as a data URL.

    Args:
        png_base64: Base64-encoded PNG data

    Returns:
        Data URL in format: data:image/png;base64,{data}
    """
    return f"data:image/png;base64,{png_base64}"


class EmbeddingAPI:
    """Client for the image embedding API.

    Expected API format:
        POST {base_url}/v1/embeddings
        Request body: {"image": "<base64_encoded_image>", "model": "<model_name>"}
        Response: {"embedding": [0.1, 0.2, ...], "model": "<model_name>", "dimensions": 512}
    """

    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_image_dimension: Optional[int] = DEFAULT_MAX_DIMENSION,
    ):
        """Initialize the embedding API client.

        Args:
            base_url: Base URL of the embedding API (e.g., 'http://localhost:8000')
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
            max_image_dimension: Maximum width or height for images in pixels.
                Large images are downscaled to this limit before sending to API.
                Set to None to disable downscaling. Defaults to 1024.
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_image_dimension = max_image_dimension

    def _get_headers(self) -> dict:
        """Build request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def get_embedding(
        self,
        image_path: str | Path,
        model: str = "default",
    ) -> list[float]:
        """Get embedding for an image file.

        Args:
            image_path: Path to the image file
            model: Name of the embedding model to use

        Returns:
            List of floats representing the embedding vector

        Raises:
            EmbeddingAPIError: If the API call fails
            FileNotFoundError: If the image file doesn't exist
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Read image and convert to PNG
        with open(image_path, "rb") as f:
            image_bytes = f.read()

        return self.get_embedding_from_bytes(image_bytes, model)

    def get_embedding_from_base64(
        self,
        image_base64: str,
        model: str = "default",
    ) -> list[float]:
        """Get embedding for a base64-encoded image.

        The image will be converted to PNG format before sending.

        Args:
            image_base64: Base64-encoded image data (any format)
            model: Name of the embedding model to use

        Returns:
            List of floats representing the embedding vector

        Raises:
            EmbeddingAPIError: If the API call fails
        """
        # Decode, convert to PNG, and re-encode
        image_bytes = base64.b64decode(image_base64)
        return self.get_embedding_from_bytes(image_bytes, model)

    def get_embedding_from_bytes(
        self,
        image_bytes: bytes,
        model: str = "default",
    ) -> list[float]:
        """Get embedding for image bytes.

        The image will be converted to PNG format before sending.
        Large images are automatically downscaled based on max_image_dimension.

        Args:
            image_bytes: Raw image bytes (any supported format)
            model: Name of the embedding model to use

        Returns:
            List of floats representing the embedding vector

        Raises:
            EmbeddingAPIError: If the API call fails
        """
        url = f"{self.base_url}/v1/embeddings"

        # Convert to PNG (with optional downscaling) and format as data URL
        png_base64 = convert_to_png_base64(image_bytes, self.max_image_dimension)
        image_data_url = format_image_data_url(png_base64)

        payload = {
            "image": image_data_url,
            "model": model,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            if response.status_code != 200:
                raise EmbeddingAPIError(
                    f"API error {response.status_code}: {response.text}"
                )

            data = response.json()
            return data["embedding"]

        except requests.RequestException as e:
            raise EmbeddingAPIError(f"Request failed: {e}")

    def health_check(self) -> bool:
        """Check if the API is available.

        Returns:
            True if the API is reachable, False otherwise
        """
        try:
            # Try common health endpoints
            for endpoint in ["/health", "/v1/health", "/"]:
                try:
                    response = requests.get(
                        f"{self.base_url}{endpoint}",
                        timeout=5.0,
                    )
                    if response.status_code < 500:
                        return True
                except requests.RequestException:
                    continue
            return False
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """List available embedding models.

        Returns:
            List of model names, or empty list if not supported

        Note:
            This assumes the API provides a /v1/models endpoint.
            Returns empty list if not available.
        """
        url = f"{self.base_url}/v1/models"

        try:
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                # Handle common response formats
                if isinstance(data, list):
                    return data
                elif "models" in data:
                    return data["models"]
                elif "data" in data:
                    return [m.get("id", m.get("name")) for m in data["data"]]
            return []
        except Exception:
            return []


class MockEmbeddingAPI(EmbeddingAPI):
    """Mock embedding API for testing without a real server.

    Generates deterministic pseudo-embeddings based on image content.
    """

    def __init__(
        self,
        dimensions: int = 512,
        max_image_dimension: Optional[int] = DEFAULT_MAX_DIMENSION,
    ):
        """Initialize mock API.

        Args:
            dimensions: Number of dimensions for generated embeddings
            max_image_dimension: Maximum width or height for images in pixels.
                Large images are downscaled to this limit. Set to None to
                disable downscaling. Defaults to 1024.
        """
        super().__init__(base_url="http://mock", max_image_dimension=max_image_dimension)
        self.dimensions = dimensions

    def get_embedding_from_bytes(
        self,
        image_bytes: bytes,
        model: str = "default",
    ) -> list[float]:
        """Generate a deterministic mock embedding.

        The embedding is derived from a hash of the PNG image data,
        so the same image always produces the same embedding.
        Large images are downscaled before hashing based on max_image_dimension.
        """
        import hashlib

        # Convert to PNG (with optional downscaling) for consistent hashing
        png_base64 = convert_to_png_base64(image_bytes, self.max_image_dimension)

        # Create deterministic embedding from image hash
        # Use multiple hashes to generate enough bytes for larger embeddings
        seed = png_base64.encode()
        hash_bytes = b""
        for i in range((self.dimensions // 32) + 1):
            hash_bytes += hashlib.sha256(seed + str(i).encode()).digest()

        embedding = []
        for i in range(self.dimensions):
            # Each byte gives a value 0-255
            value = (hash_bytes[i] / 255.0) - 0.5  # Normalize to [-0.5, 0.5]
            embedding.append(value)

        # Normalize to unit vector
        magnitude = sum(x * x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding

    def health_check(self) -> bool:
        """Mock always returns True."""
        return True

    def list_models(self) -> list[str]:
        """Return mock model list."""
        return ["mock-512", "mock-768", "mock-1024"]
