"""
Caption generator — sends media metadata (and optionally the image) to Claude
for Instagram caption generation in ES/EN/FR.
"""
import json
import re
from typing import Optional

import anthropic

from src.prompts.caption_generation import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, VIDEO_INSTRUCTION
from src.prompts.tone_variants import get_tone_instruction, get_tone_system_addendum

# Available models for AI Lab
AVAILABLE_MODELS = {
    "claude-sonnet-4-6": {"label": "Sonnet 4.6", "input_per_mtok": 3.0, "output_per_mtok": 15.0},
    "claude-sonnet-4-5-20241022": {"label": "Sonnet 4.5 (legacy)", "input_per_mtok": 3.0, "output_per_mtok": 15.0},
    "claude-opus-4-6": {"label": "Opus 4.6", "input_per_mtok": 15.0, "output_per_mtok": 75.0},
    "claude-haiku-4-5-20251001": {"label": "Haiku 4.5", "input_per_mtok": 0.80, "output_per_mtok": 4.0},
}

DEFAULT_MODEL = "claude-sonnet-4-6"


def _get_client() -> anthropic.Anthropic:
    """Get Anthropic client, supporting st.secrets or env var."""
    api_key = None
    try:
        import streamlit as st
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        pass
    return anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()


def _parse_json_response(text: str) -> dict:
    """Parse Claude's JSON response, stripping markdown fences if present."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Compute cost in USD for a given model and token counts."""
    info = AVAILABLE_MODELS.get(model, AVAILABLE_MODELS[DEFAULT_MODEL])
    return (input_tokens * info["input_per_mtok"] + output_tokens * info["output_per_mtok"]) / 1_000_000


def build_prompt(media: dict, theme: str, season: str, cta_type: str, tone: str = "default") -> str:
    """Build the filled user prompt for display purposes."""
    media_type = media.get("media_type", "image")
    return USER_PROMPT_TEMPLATE.format(
        media_type=media_type,
        category=media.get("category", ""),
        subcategory=media.get("subcategory", ""),
        ambiance=", ".join(media.get("ambiance", [])) if isinstance(media.get("ambiance"), list) else media.get("ambiance", ""),
        elements=", ".join(media.get("elements", [])) if isinstance(media.get("elements"), list) else media.get("elements", ""),
        description_fr=media.get("description_fr", ""),
        description_en=media.get("description_en", ""),
        manual_notes=media.get("manual_notes", "Aucune"),
        theme=theme,
        season=season,
        cta_type=cta_type,
        tone_instruction=get_tone_instruction(tone),
        video_instruction=VIDEO_INSTRUCTION if media_type == "video" else "",
    )


def generate_captions(
    media: dict,
    theme: str,
    season: str,
    cta_type: str,
    include_image: bool = False,
    image_base64: Optional[str] = None,
    model: str = DEFAULT_MODEL,
    system_prompt: Optional[str] = None,
    user_prompt: Optional[str] = None,
    tone: str = "default",
) -> dict:
    """
    Generate Instagram captions via Claude API.

    Returns dict with keys: short, storytelling, hashtags, _usage
    (_usage contains model, input_tokens, output_tokens, cost_usd)
    """
    client = _get_client()

    prompt_text = user_prompt if user_prompt is not None else build_prompt(media, theme, season, cta_type, tone=tone)

    # Build system prompt with tone addendum
    sys_prompt = system_prompt if system_prompt is not None else SYSTEM_PROMPT
    tone_addendum = get_tone_system_addendum(tone)
    if tone_addendum and system_prompt is None:
        sys_prompt = sys_prompt + "\n\n" + tone_addendum

    content = []
    if include_image and image_base64:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_base64,
                },
            }
        )
    content.append({"type": "text", "text": prompt_text})

    response = client.messages.create(
        model=model,
        max_tokens=2000,
        system=sys_prompt,
        messages=[{"role": "user", "content": content}],
    )

    raw_text = response.content[0].text
    result = _parse_json_response(raw_text)

    # Attach usage metadata
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    result["_usage"] = {
        "model": model,
        "model_label": AVAILABLE_MODELS.get(model, {}).get("label", model),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": compute_cost(model, input_tokens, output_tokens),
    }

    return result
