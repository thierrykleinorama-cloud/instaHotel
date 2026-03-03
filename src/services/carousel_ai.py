"""
AI-powered carousel generation — theme suggestions, image selection, caption writing.
Uses Claude (Anthropic API) following the same pattern as caption_generator.py.
"""
import json
import os
import re
from collections import Counter
from typing import Optional

from src.prompts.carousel_prompts import (
    CAROUSEL_THEME_SYSTEM,
    CAROUSEL_THEME_TEMPLATE,
    CAROUSEL_SELECT_SYSTEM,
    CAROUSEL_SELECT_TEMPLATE,
    CAROUSEL_CAPTION_SYSTEM,
    CAROUSEL_CAPTION_TEMPLATE,
)


DEFAULT_MODEL = "claude-sonnet-4-6"

COST_RATES = {
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5-20251001": (0.8, 4.0),
}


def _get_secret(key: str) -> Optional[str]:
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)


def _get_client():
    import anthropic
    key = _get_secret("ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()


def _parse_json(raw: str) -> dict:
    """Extract JSON from Claude response (may be wrapped in ```json blocks)."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
    if match:
        raw = match.group(1).strip()
    return json.loads(raw)


def _compute_cost(model: str, inp: int, out: int) -> float:
    rates = COST_RATES.get(model, (3.0, 15.0))
    return (inp * rates[0] + out * rates[1]) / 1_000_000


# ---------------------------------------------------------------------------
# 1. Suggest carousel themes from media library
# ---------------------------------------------------------------------------

def suggest_carousel_themes(
    media_list: list[dict],
    count: int = 5,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Suggest carousel themes based on available media library.

    Args:
        media_list: list of media dicts (from fetch_all_media)
        count: number of themes to suggest
        model: Claude model to use

    Returns: {themes: [...], _usage: {model, input_tokens, output_tokens, cost_usd}}
    """
    client = _get_client()

    # Summarize media library for the prompt
    categories = list(set(m.get("category", "unknown") for m in media_list if m.get("category")))
    total = len(media_list)

    # Top elements
    all_elements = []
    for m in media_list:
        elems = m.get("elements", [])
        if isinstance(elems, list):
            all_elements.extend(elems)
    top_elements = [e for e, _ in Counter(all_elements).most_common(20)]

    # Seasons
    all_seasons = set()
    for m in media_list:
        seasons = m.get("season", [])
        if isinstance(seasons, list):
            all_seasons.update(seasons)
        elif isinstance(seasons, str):
            all_seasons.add(seasons)

    user_text = CAROUSEL_THEME_TEMPLATE.format(
        count=count,
        categories=", ".join(categories),
        total_images=total,
        top_elements=", ".join(top_elements[:15]),
        seasons=", ".join(all_seasons) or "toute_saison",
    )

    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=CAROUSEL_THEME_SYSTEM,
        messages=[{"role": "user", "content": user_text}],
    )

    raw = response.content[0].text.strip()
    result = _parse_json(raw)

    inp = response.usage.input_tokens
    out = response.usage.output_tokens

    cost = _compute_cost(model, inp, out)

    from src.services.cost_tracker import log_cost
    log_cost("claude", "carousel_suggest_themes", cost, model=model,
             input_tokens=inp, output_tokens=out)

    result["_usage"] = {
        "model": model,
        "input_tokens": inp,
        "output_tokens": out,
        "cost_usd": cost,
    }
    return result


# ---------------------------------------------------------------------------
# 2. Select + order images for a carousel theme
# ---------------------------------------------------------------------------

def select_carousel_images(
    theme_title: str,
    theme_description: str,
    ordering: str,
    slide_count: int,
    media_list: list[dict],
    model: str = DEFAULT_MODEL,
) -> dict:
    """Use Claude to pick the best images for a carousel and order them.

    Args:
        theme_title: carousel theme title
        theme_description: what the carousel is about
        ordering: how to order (e.g., "best-first", "narrative arc")
        slide_count: how many images to pick
        media_list: candidate images from the library

    Returns: {selected: [{media_id, position, reason}], carousel_title, hook_note, _usage}
    """
    client = _get_client()

    # Build concise image list for Claude (limit to 100 to stay within context)
    candidates = sorted(media_list, key=lambda m: m.get("ig_quality", 0), reverse=True)[:100]
    lines = []
    for m in candidates:
        mid = m.get("id", "?")
        fname = m.get("file_name", "?")[:30]
        cat = m.get("category", "?")
        quality = m.get("ig_quality", "?")
        desc = (m.get("description_en") or m.get("description_fr") or "")[:80]
        lines.append(f"{mid} | {fname} | {cat} | {quality} | {desc}")

    user_text = CAROUSEL_SELECT_TEMPLATE.format(
        slide_count=slide_count,
        theme_title=theme_title,
        theme_description=theme_description,
        ordering=ordering,
        image_list="\n".join(lines),
    )

    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=CAROUSEL_SELECT_SYSTEM,
        messages=[{"role": "user", "content": user_text}],
    )

    raw = response.content[0].text.strip()
    result = _parse_json(raw)

    inp = response.usage.input_tokens
    out = response.usage.output_tokens

    cost = _compute_cost(model, inp, out)

    from src.services.cost_tracker import log_cost
    log_cost("claude", "carousel_select_images", cost, model=model,
             input_tokens=inp, output_tokens=out)

    result["_usage"] = {
        "model": model,
        "input_tokens": inp,
        "output_tokens": out,
        "cost_usd": cost,
    }
    return result


# ---------------------------------------------------------------------------
# 3. Generate carousel captions
# ---------------------------------------------------------------------------

def generate_carousel_captions(
    theme_title: str,
    theme_description: str,
    selected_media: list[dict],
    model: str = DEFAULT_MODEL,
) -> dict:
    """Generate multilingual captions for a carousel.

    Args:
        theme_title: carousel theme
        theme_description: what the carousel is about
        selected_media: ordered list of media dicts (with descriptions)
        model: Claude model

    Returns: {caption_es, caption_en, caption_fr, hashtags: [...], _usage}
    """
    client = _get_client()

    # Build image descriptions
    desc_lines = []
    for i, m in enumerate(selected_media, 1):
        desc = (m.get("description_en") or m.get("description_fr") or "No description")[:120]
        cat = m.get("category", "?")
        desc_lines.append(f"Slide {i}: [{cat}] {desc}")

    user_text = CAROUSEL_CAPTION_TEMPLATE.format(
        theme_title=theme_title,
        theme_description=theme_description,
        slide_count=len(selected_media),
        image_descriptions="\n".join(desc_lines),
    )

    response = client.messages.create(
        model=model,
        max_tokens=1500,
        system=CAROUSEL_CAPTION_SYSTEM,
        messages=[{"role": "user", "content": user_text}],
    )

    raw = response.content[0].text.strip()
    result = _parse_json(raw)

    inp = response.usage.input_tokens
    out = response.usage.output_tokens

    cost = _compute_cost(model, inp, out)

    from src.services.cost_tracker import log_cost
    log_cost("claude", "carousel_generate_captions", cost, model=model,
             input_tokens=inp, output_tokens=out)

    result["_usage"] = {
        "model": model,
        "input_tokens": inp,
        "output_tokens": out,
        "cost_usd": cost,
    }
    return result
