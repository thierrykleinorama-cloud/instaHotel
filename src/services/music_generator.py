"""
Music generation service — generates background music for Reels via Replicate MusicGen.
"""
import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
import httpx

from src.prompts.music_generation import build_music_prompt

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


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
    return replicate_sdk.Client(api_token=key, timeout=Timeout(300, connect=30))


# ---------------------------------------------------------------------------
# Music generation
# ---------------------------------------------------------------------------

MUSIC_MODELS = {
    "musicgen": {
        "model_id": "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb",
        "label": "MusicGen (Meta)",
        "cost_per_sec": 0.002,
    },
}

DEFAULT_MUSIC_MODEL = "musicgen"


def generate_music(
    prompt: str,
    duration: int = 10,
    model: str = DEFAULT_MUSIC_MODEL,
    temperature: float = 1.0,
) -> dict:
    """Generate instrumental music from a text prompt.

    Args:
        prompt: music description (style, mood, instruments)
        duration: length in seconds (5-30)
        model: music model key
        temperature: creativity (0.5-1.5)

    Returns: {audio_bytes, duration_sec, format, _cost}
    """
    client = _get_replicate_client()
    model_info = MUSIC_MODELS[model]

    # Use predictions.create() for real metrics
    # model_id format "owner/name:version" — extract version for predictions API
    mid = model_info["model_id"]
    version = mid.split(":")[-1] if ":" in mid else None

    if version:
        prediction = client.predictions.create(
            version=version,
            input={
                "prompt": prompt,
                "duration": duration,
                "temperature": temperature,
                "output_format": "wav",
                "normalization_strategy": "loudness",
            },
        )
    else:
        prediction = client.predictions.create(
            model=mid,
            input={
                "prompt": prompt,
                "duration": duration,
                "temperature": temperature,
                "output_format": "wav",
                "normalization_strategy": "loudness",
            },
        )
    prediction.wait()
    if prediction.status == "failed":
        raise RuntimeError(f"Music generation failed: {prediction.error}")

    # Output is a URL to the audio file
    audio_url = str(prediction.output)
    resp = httpx.get(audio_url, timeout=120, follow_redirects=True)
    resp.raise_for_status()
    audio_bytes = resp.content

    cost = duration * model_info["cost_per_sec"]

    # Real metrics from Replicate
    metrics = prediction.metrics or {}
    predict_time = metrics.get("predict_time", 0)

    from src.services.cost_tracker import log_cost
    log_cost("replicate", f"music_gen_{model}", cost,
             params={"duration": duration, "temperature": temperature,
                     "predict_time": predict_time, "source": "real_metrics"})

    return {
        "audio_bytes": audio_bytes,
        "duration_sec": duration,
        "format": "wav",
        "_cost": {"operation": f"music_gen_{model}", "cost_usd": cost,
                  "predict_time": predict_time},
    }


def generate_music_for_media(
    media: dict,
    duration: int = 10,
    mood: str | None = None,
    custom_prompt: str | None = None,
    model: str = DEFAULT_MUSIC_MODEL,
) -> dict:
    """Generate music matched to a media item's ambiance.

    Builds the prompt from media metadata, then generates.
    Returns: {audio_bytes, duration_sec, format, prompt, _cost}
    """
    prompt = build_music_prompt(media, mood=mood, custom_prompt=custom_prompt)

    result = generate_music(
        prompt=prompt,
        duration=duration,
        model=model,
    )
    result["prompt"] = prompt
    return result
