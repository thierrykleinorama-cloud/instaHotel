"""
Veo 3.1 video generation via the Gemini API (google-generativeai SDK).
Async with polling pattern — same return shape as photo_to_video() in creative_transform.py.
"""
import io
import os
import time
from typing import Optional

from google import genai
from google.genai import types


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


def _get_genai_client() -> genai.Client:
    key = _get_secret("GOOGLE_GENAI_API_KEY")
    if not key:
        raise ValueError(
            "GOOGLE_GENAI_API_KEY not found. Set it in .env or Streamlit secrets."
        )
    return genai.Client(api_key=key)


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
# Model definitions
# ---------------------------------------------------------------------------

VEO_MODELS = {
    "veo-3.1-fast": {
        "model_id": "veo-3.1-fast-generate-preview",
        "label": "Veo 3.1 Fast",
        "cost_per_sec": 0.15,   # $0.60/4s, $1.20/8s
    },
    "veo-3.1": {
        "model_id": "veo-3.1-generate-preview",
        "label": "Veo 3.1 Standard",
        "cost_per_sec": 0.40,   # $1.60/4s, $3.20/8s
    },
}


# ---------------------------------------------------------------------------
# Main generation function
# ---------------------------------------------------------------------------

def veo_photo_to_video(
    image_bytes: bytes,
    prompt: str,
    duration: int = 8,
    aspect_ratio: str = "9:16",
    model: str = "veo-3.1-fast",
    negative_prompt: str = "blurry, distorted, low quality, text overlay, watermark",
    resolution: str = "720p",
    reference_character_ids: Optional[list[str]] = None,
) -> dict:
    """Convert a photo to video using Google Veo 3.1.

    Args:
        image_bytes: source photo (the setting)
        prompt: motion/scene prompt
        duration: 4, 6, or 8 seconds
        aspect_ratio: "9:16" (reel), "16:9"
        model: "veo-3.1-fast" or "veo-3.1"
        negative_prompt: what to avoid
        resolution: "720p" or "1080p"
        reference_character_ids: optional list of character UUIDs whose
            canonical reference photos should be loaded as Veo asset references
            to preserve their appearance in the output. Max 2 (Veo limit is 3
            total references, 1 is already used as base image).

    Returns: {video_bytes, duration_sec, aspect_ratio, _cost, characters_used}
    """
    client = _get_genai_client()

    model_info = VEO_MODELS.get(model)
    if not model_info:
        raise ValueError(f"Unknown Veo model: {model}. Available: {list(VEO_MODELS.keys())}")

    # Ensure PNG format for the input image
    png_bytes = _ensure_png(image_bytes)

    # Build the full prompt with negative prompt
    full_prompt = prompt
    if negative_prompt:
        full_prompt = f"{prompt}. Avoid: {negative_prompt}"

    # Load character reference images if requested.
    # Veo 3.1 on the Gemini API supports reference_images with these constraints
    # (verified 2026-04-15, see memory/project_characters_flow.md):
    #   - duration_seconds MUST be 8
    #   - negative_prompt MUST NOT be passed
    #   - `image=` (first-frame) MUST NOT be passed
    #   - Max 3 references total, all ASSET type
    #   - veo-3.1-lite does NOT support reference_images
    char_references = []
    characters_loaded = []
    if reference_character_ids:
        try:
            from src.services.characters_queries import load_character_reference_images
            loaded = load_character_reference_images(reference_character_ids)
            # Veo: max 3 total refs, 1 reserved for hotel scene → 2 char ref slots.
            # Pick up to 2 ref images (multiple images per character are now possible).
            seen_names = set()
            for char, img_bytes in loaded[:2]:
                ref_png = _ensure_png(img_bytes)
                char_references.append(
                    types.VideoGenerationReferenceImage(
                        image=types.Image(image_bytes=ref_png, mime_type="image/png"),
                        reference_type=types.VideoGenerationReferenceType.ASSET,
                    )
                )
                if char["name"] not in seen_names:
                    characters_loaded.append(char["name"])
                    seen_names.add(char["name"])
        except Exception as e:
            print(f"[veo] character reference loading failed: {e}")

    use_refs = bool(char_references)

    if use_refs:
        # Force duration to 8s — Veo rejects refs at any other duration.
        if duration != 8:
            print(f"[veo] duration forced from {duration}s to 8s (required with refs)")
            duration = 8
        # Hotel photo joins the reference list as the scene asset.
        hotel_ref = types.VideoGenerationReferenceImage(
            image=types.Image(image_bytes=png_bytes, mime_type="image/png"),
            reference_type=types.VideoGenerationReferenceType.ASSET,
        )
        all_refs = [hotel_ref] + char_references

        config_kwargs = dict(
            aspect_ratio=aspect_ratio,
            number_of_videos=1,
            duration_seconds=8,
            person_generation="allow_adult",
            reference_images=all_refs,
            # NB: negative_prompt intentionally omitted — rejected with refs.
        )
        operation = client.models.generate_videos(
            model=model_info["model_id"],
            prompt=prompt,  # plain prompt, not full_prompt (which appends negatives)
            config=types.GenerateVideosConfig(**config_kwargs),
        )
    else:
        # Image-to-video mode: first frame = hotel photo, any supported duration.
        config_kwargs = dict(
            aspect_ratio=aspect_ratio,
            number_of_videos=1,
            duration_seconds=duration,
            negative_prompt=negative_prompt,
            person_generation="allow_adult",
        )
        operation = client.models.generate_videos(
            model=model_info["model_id"],
            prompt=full_prompt,
            image=types.Image(image_bytes=png_bytes, mime_type="image/png"),
            config=types.GenerateVideosConfig(**config_kwargs),
        )

    # Poll for completion
    max_wait = 600  # 10 minutes
    elapsed = 0
    interval = 10
    while not operation.done and elapsed < max_wait:
        time.sleep(interval)
        elapsed += interval
        operation = client.operations.get(operation)

    if not operation.done:
        raise TimeoutError(f"Veo video generation timed out after {max_wait}s")

    # Extract the video
    if not operation.result or not operation.result.generated_videos:
        error = getattr(operation, 'error', None)
        raise RuntimeError(f"Veo generation failed: {error or 'No videos returned'}")

    video = operation.result.generated_videos[0]

    # video.video.video_bytes is None for remote files — download via URI
    vid = video.video
    video_data = vid.video_bytes
    if video_data is None and vid.uri:
        import httpx
        api_key = _get_secret("GOOGLE_GENAI_API_KEY")
        resp = httpx.get(
            f"{vid.uri}&key={api_key}" if "?" in vid.uri else f"{vid.uri}?key={api_key}",
            follow_redirects=True,
            timeout=120,
        )
        resp.raise_for_status()
        video_data = resp.content

    if not video_data:
        raise RuntimeError("Veo generation succeeded but video bytes could not be downloaded.")

    cost = duration * model_info["cost_per_sec"]

    from src.services.cost_tracker import log_cost
    log_cost("google_veo", f"photo_to_video_{model}", cost,
             params={"duration": duration, "aspect_ratio": aspect_ratio,
                     "resolution": resolution, "source": "estimate"})

    return {
        "video_bytes": video_data,
        "duration_sec": duration,
        "aspect_ratio": aspect_ratio,
        "characters_used": characters_loaded,
        "_cost": {"operation": f"photo_to_video_{model}", "cost_usd": cost},
    }
