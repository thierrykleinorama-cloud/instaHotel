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
from src.services.cost_tracker import log_cost


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

    from src.prompts.creative_transform import HOTEL_CONTEXT
    user_text = MOTION_PROMPT_TEMPLATE.format(
        hotel_context=HOTEL_CONTEXT,
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

    log_cost("claude", "motion_prompt_ai", cost, model=model,
             input_tokens=inp, output_tokens=out,
             params={"source": "real_tokens"})

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
    include_characters: bool = True,
) -> dict:
    """Generate creative video scenarios for a photo.

    Returns: {scenarios: [...], _usage: {...}}
    Each scenario includes a "characters_used" field with character IDs (or empty list).
    """
    import json
    import re

    client = _get_anthropic_client()

    if not hotel_context:
        from src.prompts.creative_transform import HOTEL_CONTEXT
        hotel_context = HOTEL_CONTEXT

    # Build character roster for prompt injection
    character_roster = ""
    if include_characters:
        try:
            from src.services.characters_queries import (
                fetch_active_characters, build_character_roster_prompt,
            )
            chars = fetch_active_characters()
            if chars:
                roster_text = build_character_roster_prompt(chars)
                id_lines = "\n".join(f"  {c['name']}: {c['id']}" for c in chars)
                character_roster = f"{roster_text}\n\nCHARACTER IDs (use these exact UUIDs in characters_used):\n{id_lines}"
        except Exception:
            pass  # Characters optional — proceed without if it fails

    user_text = SCENARIO_TEMPLATE.format(
        count=count,
        category=media.get("category", ""),
        elements=", ".join(media.get("elements", [])) if isinstance(media.get("elements"), list) else media.get("elements", ""),
        description_en=media.get("description_en", ""),
        hotel_context=hotel_context,
        character_roster=character_roster,
        creative_brief=creative_brief or "Full creative freedom",
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

    log_cost("claude", "generate_scenarios", cost, model=model,
             input_tokens=inp, output_tokens=out,
             params={"source": "real_tokens"})

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

# Available video models
VIDEO_MODELS = {
    "kling-v3-omni": {
        "model_id": "kwaivgi/kling-v3-omni-video",
        "label": "Kling V3 Omni",
        "provider": "replicate",
        "cost_per_sec": 0.126,
        "supports_image": True,
        "supports_characters": True,
        "image_param": "start_image",
        "max_refs": 7,
    },
    "veo-3.1-fast": {
        "label": "Veo 3.1 Fast",
        "provider": "google",
        "cost_4s": 0.60,
        "cost_6s": 0.90,
        "cost_8s": 1.20,
        "supports_image": True,
        "supports_characters": True,
    },
    "veo-3.1": {
        "label": "Veo 3.1 Standard",
        "provider": "google",
        "cost_4s": 1.60,
        "cost_6s": 2.40,
        "cost_8s": 3.20,
        "supports_image": True,
        "supports_characters": True,
    },
}

DEFAULT_VIDEO_MODEL = "kling-v3-omni"


def get_model_durations(model: str) -> list[int]:
    """Return valid duration options for a given video model."""
    info = VIDEO_MODELS.get(model, {})
    if info.get("provider") == "google":
        return [4, 6, 8]
    return [5, 8, 10, 15]  # Kling V3 Omni default


def estimate_video_cost(model: str, duration: int) -> float:
    """Estimate the cost in USD for a video generation."""
    info = VIDEO_MODELS.get(model, {})
    if info.get("provider") == "google":
        return info.get(f"cost_{duration}s", 0.0)
    if "cost_per_sec" in info:
        return round(duration * info["cost_per_sec"], 2)
    return info.get("cost_5s", 0.0) if duration <= 5 else info.get("cost_10s", 0.0)


def _build_kling_v3_omni_refs(
    image_bytes: bytes,
    prompt: str,
    reference_character_ids: Optional[list[str]],
) -> tuple[dict, list[str]]:
    """Build Kling V3 Omni input params with character reference images.

    Kling V3 Omni uses `reference_images` (file URI array, max 7) and
    `<<<image_N>>>` tags in the prompt to reference specific images.
    A character may have multiple reference photos — all are included (up to 7 total).
    Returns (input_params_extras, characters_loaded).
    """
    if not reference_character_ids:
        return {}, []

    from src.services.characters_queries import load_character_reference_images
    loaded = load_character_reference_images(reference_character_ids)
    if not loaded:
        return {}, []

    ref_uris = []
    characters_loaded = []
    prompt_tags = []
    seen_names = set()
    for i, (char, img_bytes) in enumerate(loaded[:7], start=1):
        ref_png = _ensure_png(img_bytes)
        b64 = base64.b64encode(ref_png).decode()
        ref_uris.append(f"data:image/png;base64,{b64}")
        if char["name"] not in seen_names:
            characters_loaded.append(char["name"])
            seen_names.add(char["name"])
        desc = char.get("description", char["name"])
        prompt_tags.append(f"<<<image_{i}>>> is {desc}")

    ref_preamble = ". ".join(prompt_tags) + ". "

    return {
        "reference_images": ref_uris,
        "_prompt_prefix": ref_preamble,
    }, characters_loaded


def photo_to_video(
    image_bytes: bytes,
    prompt: str,
    duration: int = 5,
    aspect_ratio: str = "9:16",
    model: str = DEFAULT_VIDEO_MODEL,
    negative_prompt: str = "blurry, distorted, low quality, text overlay, watermark",
    resolution: str = "720p",
    reference_character_ids: Optional[list[str]] = None,
) -> dict:
    """Convert a photo to video.

    Dispatches to the correct backend based on model provider:
    - "replicate" kling-v3-omni → Kling V3 Omni (up to 7 character refs via <<<image_N>>>)
    - "replicate" kling-v3-omni → Kling V3 Omni (up to 7 character refs via <<<image_N>>>)
    - "google" → Veo 3.1 via Gemini API (up to 2 character refs as ASSET references)

    Returns: {video_bytes, duration_sec, aspect_ratio, _cost, characters_used}
    """
    model_info = VIDEO_MODELS[model]

    # Dispatch to Veo for Google models
    if model_info.get("provider") == "google":
        from src.services.veo_generator import veo_photo_to_video
        return veo_photo_to_video(
            image_bytes, prompt, duration, aspect_ratio, model,
            negative_prompt, resolution,
            reference_character_ids=reference_character_ids,
        )

    client = _get_replicate_client()

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

    # Kling V3 Omni: add character references + aspect_ratio
    characters_loaded = []
    if model == "kling-v3-omni":
        input_params["aspect_ratio"] = aspect_ratio
        input_params["mode"] = "standard"
        ref_extras, characters_loaded = _build_kling_v3_omni_refs(
            image_bytes, prompt, reference_character_ids,
        )
        if ref_extras.get("reference_images"):
            input_params["reference_images"] = ref_extras["reference_images"]
            input_params["prompt"] = ref_extras["_prompt_prefix"] + prompt

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

    cost = estimate_video_cost(model, duration)

    # Real metrics from Replicate
    metrics = result.metrics or {}
    predict_time = metrics.get("predict_time", 0)

    log_cost("replicate", f"photo_to_video_{model}", cost,
             params={"duration": duration, "aspect_ratio": aspect_ratio,
                     "predict_time": predict_time, "source": "real_metrics"})

    return {
        "video_bytes": video_bytes,
        "duration_sec": duration,
        "aspect_ratio": aspect_ratio,
        "characters_used": characters_loaded,
        "_cost": {"operation": f"photo_to_video_{model}", "cost_usd": cost,
                  "predict_time": predict_time},
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
