"""
Multi-backend image enhancement service.
Supports Stability AI (upscale + outpaint) and Replicate (Real-ESRGAN upscale).
"""
import io
import os
import time
from typing import Optional

import httpx
from PIL import Image

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_secret(key: str) -> Optional[str]:
    """Get a secret from st.secrets (Streamlit Cloud) or os.environ (local)."""
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)


def _get_stability_key() -> str:
    key = _get_secret("STABILITY_API_KEY")
    if not key:
        raise ValueError(
            "STABILITY_API_KEY not found. Set it in .env or Streamlit secrets."
        )
    return key


def _get_replicate_key() -> str:
    key = _get_secret("REPLICATE_API_TOKEN")
    if not key:
        raise ValueError(
            "REPLICATE_API_TOKEN not found. Set it in .env or Streamlit secrets."
        )
    return key


def _ensure_png(image_bytes: bytes) -> bytes:
    """Convert any image format (including HEIC) to PNG bytes."""
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
    except ImportError:
        pass
    img = Image.open(io.BytesIO(image_bytes))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _image_dimensions(image_bytes: bytes) -> tuple[int, int]:
    """Return (width, height) of image."""
    img = Image.open(io.BytesIO(image_bytes))
    return img.size


def _downscale_for_api(image_bytes: bytes, max_pixels: int = 1_048_576) -> bytes:
    """Downscale image if it exceeds max pixel count (preserving aspect ratio).
    Stability AI fast upscale limit = 1,048,576 pixels (1 MP).
    """
    img = Image.open(io.BytesIO(image_bytes))
    w, h = img.size
    pixels = w * h
    if pixels <= max_pixels:
        return image_bytes
    scale = (max_pixels / pixels) ** 0.5
    new_w, new_h = int(w * scale), int(h * scale)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Outpaint padding computation
# ---------------------------------------------------------------------------

# Target ratios as (w, h) tuples
TARGET_RATIOS = {
    "4:5": (4, 5),
    "1:1": (1, 1),
    "9:16": (9, 16),
}


def compute_outpaint_padding(
    w: int, h: int, target_ratio: str
) -> dict:
    """
    Calculate symmetric pixel padding to reach the target aspect ratio.

    Returns dict with keys: left, right, top, bottom, new_w, new_h.
    Padding is added only to the dimension that needs extending.
    """
    tw, th = TARGET_RATIOS[target_ratio]
    target = tw / th

    current = w / h

    if abs(current - target) < 0.01:
        return {"left": 0, "right": 0, "top": 0, "bottom": 0, "new_w": w, "new_h": h}

    if current > target:
        # Image is wider than target — extend height
        new_h = round(w * th / tw)
        new_w = w
        pad_total = new_h - h
        top = pad_total // 2
        bottom = pad_total - top
        return {"left": 0, "right": 0, "top": top, "bottom": bottom, "new_w": new_w, "new_h": new_h}
    else:
        # Image is taller than target — extend width
        new_w = round(h * tw / th)
        new_h = h
        pad_total = new_w - w
        left = pad_total // 2
        right = pad_total - left
        return {"left": left, "right": right, "top": 0, "bottom": 0, "new_w": new_w, "new_h": new_h}


# ---------------------------------------------------------------------------
# Stability AI
# ---------------------------------------------------------------------------

STABILITY_BASE = "https://api.stability.ai"

STABILITY_METHODS = {
    "fast": {"path": "fast", "cost": 0.02, "description": "Fast 2x ($0.02)"},
    "conservative": {"path": "conservative", "cost": 0.40, "description": "Conservative 2x ($0.40)"},
    "creative": {"path": "creative", "cost": 0.60, "description": "Creative 4x ($0.60)"},
}


def stability_upscale(
    image_bytes: bytes,
    method: str = "fast",
) -> dict:
    """
    Upscale image via Stability AI.
    Returns: {image_bytes, width, height, _cost: {operation, cost_usd}}
    """
    api_key = _get_stability_key()
    png = _ensure_png(image_bytes)
    png = _downscale_for_api(png)  # Stability AI limit: 1 MP
    info = STABILITY_METHODS[method]

    if method == "fast":
        # Fast upscale: single-step, returns image directly
        url = f"{STABILITY_BASE}/v2beta/stable-image/upscale/fast"
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "image/*",
            },
            files={"image": ("image.png", png, "image/png")},
            data={"output_format": "png"},
            timeout=120,
        )
        resp.raise_for_status()
        result_bytes = resp.content
    else:
        # Conservative / Creative: async — start generation then poll
        url = f"{STABILITY_BASE}/v2beta/stable-image/upscale/{info['path']}"
        resp = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
            files={"image": ("image.png", png, "image/png")},
            data={"output_format": "png"},
            timeout=120,
        )
        resp.raise_for_status()
        generation_id = resp.json()["id"]
        result_bytes = _stability_poll(api_key, generation_id)

    rw, rh = _image_dimensions(result_bytes)
    return {
        "image_bytes": result_bytes,
        "width": rw,
        "height": rh,
        "_cost": {"operation": f"upscale_{method}", "cost_usd": info["cost"]},
    }


def _stability_poll(api_key: str, generation_id: str, max_wait: int = 300) -> bytes:
    """Poll Stability AI for an async generation result."""
    url = f"{STABILITY_BASE}/v2beta/stable-image/upscale/result/{generation_id}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*",
    }
    elapsed = 0
    interval = 5
    while elapsed < max_wait:
        time.sleep(interval)
        elapsed += interval
        resp = httpx.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.content
        if resp.status_code == 202:
            continue  # still processing
        resp.raise_for_status()
    raise TimeoutError(f"Stability AI upscale timed out after {max_wait}s")


def stability_outpaint(
    image_bytes: bytes,
    target_ratio: str = "4:5",
    creativity: float = 0.5,
) -> dict:
    """
    Outpaint (extend) image to target aspect ratio via Stability AI.
    Returns: {image_bytes, width, height, padding, _cost}
    """
    api_key = _get_stability_key()
    png = _ensure_png(image_bytes)
    png = _downscale_for_api(png)  # Stability AI limit: 1 MP
    w, h = _image_dimensions(png)
    padding = compute_outpaint_padding(w, h, target_ratio)

    if padding["left"] == 0 and padding["right"] == 0 and padding["top"] == 0 and padding["bottom"] == 0:
        return {
            "image_bytes": png,
            "width": w,
            "height": h,
            "padding": padding,
            "_cost": {"operation": "outpaint", "cost_usd": 0.0},
        }

    url = f"{STABILITY_BASE}/v2beta/stable-image/edit/outpaint"

    data = {
        "output_format": "png",
        "creativity": str(creativity),
    }
    # Only send non-zero padding values
    if padding["left"] > 0:
        data["left"] = str(padding["left"])
    if padding["right"] > 0:
        data["right"] = str(padding["right"])
    if padding["top"] > 0:
        data["top"] = str(padding["top"])
    if padding["bottom"] > 0:
        data["bottom"] = str(padding["bottom"])

    resp = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "image/*",
        },
        files={"image": ("image.png", png, "image/png")},
        data=data,
        timeout=120,
    )
    resp.raise_for_status()
    result_bytes = resp.content

    rw, rh = _image_dimensions(result_bytes)
    return {
        "image_bytes": result_bytes,
        "width": rw,
        "height": rh,
        "padding": padding,
        "_cost": {"operation": "outpaint", "cost_usd": 0.04},
    }


# ---------------------------------------------------------------------------
# Replicate
# ---------------------------------------------------------------------------

def replicate_upscale(
    image_bytes: bytes,
    model: str = "real-esrgan",
    scale: int = 4,
) -> dict:
    """
    Upscale image via Replicate Real-ESRGAN.
    Returns: {image_bytes, width, height, _cost}
    """
    import replicate as replicate_sdk
    import base64

    api_key = _get_replicate_key()
    os.environ["REPLICATE_API_TOKEN"] = api_key

    png = _ensure_png(image_bytes)
    # Replicate expects a data URI
    b64 = base64.b64encode(png).decode()
    data_uri = f"data:image/png;base64,{b64}"

    output = replicate_sdk.run(
        "nightmareai/real-esrgan:f121d640bd286e1fdc67f9799164c1d5be36ff74576ee11c803ae5b665dd46aa",
        input={
            "image": data_uri,
            "scale": scale,
            "face_enhance": False,
        },
    )

    # output is a FileOutput / URL — download the result
    result_url = str(output)
    resp = httpx.get(result_url, timeout=120)
    resp.raise_for_status()
    result_bytes = resp.content

    rw, rh = _image_dimensions(result_bytes)
    return {
        "image_bytes": result_bytes,
        "width": rw,
        "height": rh,
        "_cost": {"operation": "replicate_upscale", "cost_usd": 0.003 * scale},
    }
