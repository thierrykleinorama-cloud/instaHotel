"""
Creative transform service — photo-to-video, scenario generation, seasonal variants.
Uses Replicate (Kling v2.1) for video generation.
"""
import base64
import io
import os
import time
from typing import Optional

import httpx

from src.prompts.creative_transform import (
    MOTION_PROMPT_SYSTEM,
    MOTION_PROMPT_TEMPLATE,
    AMBIANCE_MOTION_MAP,
    CATEGORY_MOTION_MAP,
    SCENARIO_SYSTEM,
    SCENARIO_TEMPLATE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_secret(key: str) -> Optional[str]:
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)


def _get_replicate_client():
    import replicate as replicate_sdk
    from httpx import Timeout
    key = _get_secret("REPLICATE_API_TOKEN")
    if not key:
        raise ValueError("REPLICATE_API_TOKEN not found.")
    return replicate_sdk.Client(api_token=key, timeout=Timeout(600, connect=30))


def _get_anthropic_client():
    import anthropic
    key = _get_secret("ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()


def _ensure_png(image_bytes: bytes) -> bytes:
    from PIL import Image
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


# ---------------------------------------------------------------------------
# Motion prompt generation (Claude)
# ---------------------------------------------------------------------------

def build_motion_prompt(media: dict, creative_brief: str = "") -> str:
    """Build a motion prompt automatically from media metadata.

    Returns a simple default if no Claude call is desired.
    Uses ambiance and category maps for quick generation.
    """
    parts = []

    # Ambiance-based motion
    ambiance = media.get("ambiance", [])
    if isinstance(ambiance, list):
        for a in ambiance:
            if a in AMBIANCE_MOTION_MAP:
                parts.append(AMBIANCE_MOTION_MAP[a])
                break
    elif isinstance(ambiance, str) and ambiance in AMBIANCE_MOTION_MAP:
        parts.append(AMBIANCE_MOTION_MAP[ambiance])

    # Category-based motion
    category = media.get("category", "")
    if category in CATEGORY_MOTION_MAP:
        parts.append(CATEGORY_MOTION_MAP[category])

    if not parts:
        parts.append("slow cinematic dolly forward, gentle ambient movement, warm hotel atmosphere")

    return ". ".join(parts)


def generate_motion_prompt_ai(
    media: dict,
    creative_brief: str = "",
    image_base64: Optional[str] = None,
    duration: int = 5,
    aspect_ratio: str = "9:16",
    model: str = "claude-sonnet-4-6",
) -> dict:
    """Use Claude to generate a cinematic motion prompt from media metadata + optional image.

    Returns: {prompt: str, _usage: {model, input_tokens, output_tokens, cost_usd}}
    """
    client = _get_anthropic_client()

    user_text = MOTION_PROMPT_TEMPLATE.format(
        category=media.get("category", ""),
        subcategory=media.get("subcategory", ""),
        ambiance=", ".join(media.get("ambiance", [])) if isinstance(media.get("ambiance"), list) else media.get("ambiance", ""),
        elements=", ".join(media.get("elements", [])) if isinstance(media.get("elements"), list) else media.get("elements", ""),
        description_en=media.get("description_en", ""),
        duration=duration,
        aspect_ratio=aspect_ratio,
        creative_brief=creative_brief or "Liberté créative — propose le mouvement le plus cinématique pour cette photo",
    )

    content = []
    if image_base64:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": image_base64},
        })
    content.append({"type": "text", "text": user_text})

    response = client.messages.create(
        model=model,
        max_tokens=300,
        system=MOTION_PROMPT_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )

    prompt_text = response.content[0].text.strip()
    inp = response.usage.input_tokens
    out = response.usage.output_tokens

    # Cost estimate (Sonnet rates)
    cost_rates = {"claude-sonnet-4-6": (3.0, 15.0), "claude-haiku-4-5-20251001": (0.8, 4.0)}
    rates = cost_rates.get(model, (3.0, 15.0))
    cost = (inp * rates[0] + out * rates[1]) / 1_000_000

    return {
        "prompt": prompt_text,
        "_usage": {
            "model": model,
            "input_tokens": inp,
            "output_tokens": out,
            "cost_usd": cost,
        },
    }


# ---------------------------------------------------------------------------
# Scenario generation (Claude)
# ---------------------------------------------------------------------------

def generate_scenarios(
    media: dict,
    creative_brief: str = "",
    hotel_context: str = "",
    count: int = 3,
    image_base64: Optional[str] = None,
    model: str = "claude-sonnet-4-6",
) -> dict:
    """Generate creative video scenarios for a photo.

    Returns: {scenarios: [...], _usage: {...}}
    """
    import json
    import re

    client = _get_anthropic_client()

    if not hotel_context:
        hotel_context = (
            "Hôtel Noucentista — boutique Art Nouveau à Sitges (Barcelone). "
            "Ambiance chaleureuse, méditerranéenne. Des chats vivent à l'hôtel."
        )

    user_text = SCENARIO_TEMPLATE.format(
        count=count,
        category=media.get("category", ""),
        elements=", ".join(media.get("elements", [])) if isinstance(media.get("elements"), list) else media.get("elements", ""),
        description_en=media.get("description_en", ""),
        hotel_context=hotel_context,
        creative_brief=creative_brief or "Liberté créative totale",
    )

    content = []
    if image_base64:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": image_base64},
        })
    content.append({"type": "text", "text": user_text})

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=SCENARIO_SYSTEM,
        messages=[{"role": "user", "content": content}],
    )

    raw = response.content[0].text.strip()
    # Parse JSON from response
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        raw = match.group(1).strip()
    result = json.loads(raw)

    inp = response.usage.input_tokens
    out = response.usage.output_tokens
    cost_rates = {"claude-sonnet-4-6": (3.0, 15.0), "claude-haiku-4-5-20251001": (0.8, 4.0)}
    rates = cost_rates.get(model, (3.0, 15.0))
    cost = (inp * rates[0] + out * rates[1]) / 1_000_000

    result["_usage"] = {
        "model": model,
        "input_tokens": inp,
        "output_tokens": out,
        "cost_usd": cost,
    }

    return result


# ---------------------------------------------------------------------------
# Photo-to-Video via Replicate (Kling v2.1)
# ---------------------------------------------------------------------------

# Available video models on Replicate
VIDEO_MODELS = {
    "kling-v2.1": {
        "model_id": "kwaivgi/kling-v2.1",
        "label": "Kling v2.1",
        "cost_5s": 0.30,
        "cost_10s": 0.60,
        "supports_image": True,
        "image_param": "start_image",
    },
}

DEFAULT_VIDEO_MODEL = "kling-v2.1"


def photo_to_video(
    image_bytes: bytes,
    prompt: str,
    duration: int = 5,
    aspect_ratio: str = "9:16",
    model: str = DEFAULT_VIDEO_MODEL,
    negative_prompt: str = "blurry, distorted, low quality, text overlay, watermark",
) -> dict:
    """Convert a photo to video using Replicate.

    Args:
        image_bytes: source photo
        prompt: motion/scene prompt
        duration: 5 or 10 seconds
        aspect_ratio: "9:16" (reel), "16:9", "1:1"
        model: video model key
        negative_prompt: what to avoid

    Returns: {video_bytes, duration_sec, width, height, _cost}
    """
    client = _get_replicate_client()
    model_info = VIDEO_MODELS[model]

    png = _ensure_png(image_bytes)
    b64 = base64.b64encode(png).decode()
    data_uri = f"data:image/png;base64,{b64}"

    image_param = model_info.get("image_param", "start_image")
    input_params = {
        image_param: data_uri,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "duration": duration,
    }

    # Create prediction (async — video gen takes 1-5 min)
    prediction = client.predictions.create(
        model=model_info["model_id"],
        input=input_params,
    )

    # Poll for completion
    result = _poll_prediction(client, prediction.id, max_wait=600)

    # Download result video
    video_url = result.output if isinstance(result.output, str) else result.output[0]
    resp = httpx.get(str(video_url), timeout=120, follow_redirects=True)
    resp.raise_for_status()
    video_bytes = resp.content

    cost = model_info["cost_5s"] if duration <= 5 else model_info["cost_10s"]

    return {
        "video_bytes": video_bytes,
        "duration_sec": duration,
        "aspect_ratio": aspect_ratio,
        "_cost": {"operation": f"photo_to_video_{model}", "cost_usd": cost},
    }


def _poll_prediction(client, prediction_id: str, max_wait: int = 600):
    """Poll a Replicate prediction until complete."""
    elapsed = 0
    interval = 5
    while elapsed < max_wait:
        time.sleep(interval)
        elapsed += interval
        pred = client.predictions.get(prediction_id)
        if pred.status == "succeeded":
            return pred
        if pred.status == "failed":
            raise RuntimeError(f"Prediction failed: {pred.error}")
        if pred.status == "canceled":
            raise RuntimeError("Prediction was canceled.")
        # Increase interval for long-running video generation
        if elapsed > 30:
            interval = 10
    raise TimeoutError(f"Prediction timed out after {max_wait}s")
