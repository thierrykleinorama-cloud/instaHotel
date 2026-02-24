"""
Utility functions: image encoding, aspect ratio detection, MIME type mapping.
"""
import base64
import io
from typing import Optional

from PIL import Image
from pillow_heif import register_heif_opener

register_heif_opener()


# Maximum dimension for images sent to Claude (saves tokens)
MAX_IMAGE_DIMENSION = 2048


def encode_image_bytes(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """Resize if needed and return base64-encoded string."""
    img = Image.open(io.BytesIO(image_bytes))

    # Convert HEIC/HEIF to JPEG (Pillow may not support HEIC natively)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    # Resize if too large
    w, h = img.size
    if max(w, h) > MAX_IMAGE_DIMENSION:
        ratio = MAX_IMAGE_DIMENSION / max(w, h)
        new_w, new_h = int(w * ratio), int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    # Encode to JPEG
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")


def get_aspect_ratio(image_bytes: bytes) -> str:
    """Detect aspect ratio from image bytes. Returns string like '4:3', '16:9', '1:1'."""
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    ratio = w / h

    # Common aspect ratios
    if abs(ratio - 1.0) < 0.05:
        return "1:1"
    elif abs(ratio - 4 / 3) < 0.08:
        return "4:3"
    elif abs(ratio - 3 / 4) < 0.08:
        return "3:4"
    elif abs(ratio - 16 / 9) < 0.08:
        return "16:9"
    elif abs(ratio - 9 / 16) < 0.08:
        return "9:16"
    elif abs(ratio - 3 / 2) < 0.08:
        return "3:2"
    elif abs(ratio - 2 / 3) < 0.08:
        return "2:3"
    else:
        return f"{w}:{h}"


def get_aspect_ratio_from_dimensions(width: int, height: int) -> str:
    """Detect aspect ratio from width/height."""
    ratio = width / height
    if abs(ratio - 1.0) < 0.05:
        return "1:1"
    elif abs(ratio - 4 / 3) < 0.08:
        return "4:3"
    elif abs(ratio - 3 / 4) < 0.08:
        return "3:4"
    elif abs(ratio - 16 / 9) < 0.08:
        return "16:9"
    elif abs(ratio - 9 / 16) < 0.08:
        return "9:16"
    elif abs(ratio - 3 / 2) < 0.08:
        return "3:2"
    elif abs(ratio - 2 / 3) < 0.08:
        return "2:3"
    else:
        return f"{width}:{height}"


def encode_cv2_frame(frame) -> str:
    """Encode an OpenCV BGR frame to base64 JPEG string."""
    import cv2
    # Convert BGR to RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb)

    # Resize if needed
    w, h = img.size
    if max(w, h) > MAX_IMAGE_DIMENSION:
        ratio = MAX_IMAGE_DIMENSION / max(w, h)
        new_w, new_h = int(w * ratio), int(h * ratio)
        img = img.resize((new_w, new_h), Image.LANCZOS)

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=85)
    return base64.standard_b64encode(buffer.getvalue()).decode("utf-8")
