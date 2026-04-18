"""
Claude Vision analyzer — sends hotel photos to Claude and parses structured JSON.
"""
import json
import os
import re
from pathlib import Path
from typing import Optional

import anthropic
from dotenv import load_dotenv

from src.models import VisionAnalysis

_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env")

MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """You are an expert in hotel photography and Instagram marketing.
You analyze photos and videos of Hotel Noucentista, a boutique Art Nouveau hotel in Sitges (Barcelona), Spain.

The hotel has these main spaces:
- Rooms (suites, double rooms, single rooms) with Art Nouveau decor
- Common areas (lobby, living_room, terrace, hallways, staircase)
- Exteriors (facade, patio, sea view, street)
- Food (breakfast, bar, dining_room)
- Experiences (spa, events, activities, panoramic views)
- Destination (photos of Sitges: beaches, streets, monuments, restaurants, landscapes — not the hotel itself)

Respond ONLY with a valid JSON object (no markdown, no commentary)."""

USER_PROMPT = """Analyze this hotel image and return JSON with exactly these fields:

{
  "category": "room|common|exterior|food|experience|destination",
  "subcategory": "specific space name in English snake_case (e.g. suite, terrace, pool, breakfast, spa)",
  "ambiance": ["list of mood tags in English snake_case: bright, warm, romantic, modern, art_nouveau, mediterranean, cozy, elegant, natural, colorful"],
  "season": ["spring|summer|autumn|winter|any_season — when this photo would be ideal for Instagram"],
  "elements": ["list of visible elements in English snake_case: bed, sea_view, pool, terrace, furniture, plants, natural_light, decor, food, etc."],
  "ig_quality": 8,
  "description_fr": "One-sentence French description for internal use",
  "description_en": "One-sentence English description for search and retrieval"
}

Criteria for ig_quality (1-10):
- 9-10: Exceptional photo, Instagram-ready (composition, light, pro quality)
- 7-8: Good photo, usable with minimal retouching
- 5-6: Decent photo but not ideal (angle, light, staging)
- 3-4: Mediocre photo (blurry, poorly framed, unattractive)
- 1-2: Unusable photo (very blurry, dark, off-topic)

IMPORTANT: All values must be in English snake_case. Keep `art_nouveau` as a proper noun."""


def _parse_json_response(text: str) -> dict:
    """Parse Claude's JSON response, stripping markdown fences if present."""
    text = text.strip()
    # Strip markdown code fences
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def analyze_image(
    image_base64: str,
    media_type: str = "image/jpeg",
    model: str = MODEL,
) -> VisionAnalysis:
    """Send a single image to Claude Vision and return structured analysis."""
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": USER_PROMPT},
                ],
            }
        ],
    )

    raw_text = response.content[0].text
    data = _parse_json_response(raw_text)
    analysis = VisionAnalysis(**data)
    return analysis


def analyze_frames(
    frames_base64: list[str],
    context: str = "",
    model: str = MODEL,
) -> VisionAnalysis:
    """Send multiple video frames to Claude Vision as a single scene analysis."""
    client = anthropic.Anthropic()

    content = []
    for frame_b64 in frames_base64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": frame_b64,
            },
        })

    prompt = USER_PROMPT
    if context:
        prompt = f"{context}\n\n{USER_PROMPT}"
    content.append({"type": "text", "text": prompt})

    response = client.messages.create(
        model=model,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    raw_text = response.content[0].text
    data = _parse_json_response(raw_text)
    analysis = VisionAnalysis(**data)
    return analysis


def get_raw_response(
    image_base64: str,
    media_type: str = "image/jpeg",
    model: str = MODEL,
) -> dict:
    """Like analyze_image but returns the raw dict (for storage in analysis_raw)."""
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": USER_PROMPT},
                ],
            }
        ],
    )

    raw_text = response.content[0].text
    return {
        "raw_text": raw_text,
        "parsed": _parse_json_response(raw_text),
        "model": response.model,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }
