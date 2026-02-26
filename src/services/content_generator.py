"""
Content generator — bridge between caption_generator and editorial calendar slots.
Resolves slot context, generates captions, saves to DB, links to calendar.
"""
from datetime import date
from typing import Optional

from src.services.caption_generator import (
    generate_captions,
    compute_cost,
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
)
from src.services.content_queries import insert_content, link_content_to_calendar
from src.services.media_queries import fetch_media_by_id
from src.services.editorial_queries import fetch_active_theme_for_date
from src.services.editorial_engine import get_current_season


def resolve_slot_context(entry: dict) -> dict:
    """Resolve media, theme, season, and CTA from a calendar entry.

    Returns dict with keys: media, theme_name, season, cta_type, media_id
    """
    media_id = entry.get("manual_media_id") or entry.get("media_id")
    media = fetch_media_by_id(media_id) if media_id else None

    # Season: from entry or derive from date
    season = entry.get("season_context")
    if not season:
        post_date = entry.get("post_date")
        if isinstance(post_date, str):
            post_date = date.fromisoformat(post_date)
        season = get_current_season(post_date) if post_date else "toute_saison"

    # Theme: from entry or look up by date
    theme_name = entry.get("theme_name") or ""
    cta_type = "link_bio"  # default
    if entry.get("theme_id"):
        post_date = entry.get("post_date")
        if isinstance(post_date, str):
            post_date = date.fromisoformat(post_date)
        theme_data = fetch_active_theme_for_date(post_date) if post_date else None
        if theme_data:
            theme_name = theme_data.get("theme_name", theme_name)
            cta_type = theme_data.get("cta_focus", cta_type)

    return {
        "media": media or {},
        "media_id": media_id,
        "theme_name": theme_name,
        "season": season,
        "cta_type": cta_type,
    }


def generate_for_slot(
    entry: dict,
    model: str = DEFAULT_MODEL,
    include_image: bool = False,
    image_base64: Optional[str] = None,
    cta_override: Optional[str] = None,
) -> Optional[dict]:
    """Generate captions for a calendar slot, save to DB, and link.

    Args:
        entry: editorial_calendar row dict (must have 'id')
        model: Claude model ID
        include_image: whether to include the image in the prompt
        image_base64: pre-encoded base64 image (if include_image is True)
        cta_override: if set, use this CTA instead of theme-derived one

    Returns the generated_content row dict (with id), or None on error.
    """
    ctx = resolve_slot_context(entry)
    media = ctx["media"]

    if not media:
        return None

    cta_type = cta_override if cta_override else ctx["cta_type"]

    # Generate captions via Claude
    result = generate_captions(
        media=media,
        theme=ctx["theme_name"],
        season=ctx["season"],
        cta_type=cta_type,
        include_image=include_image,
        image_base64=image_base64,
        model=model,
    )

    # Extract caption data
    short = result.get("short", {})
    story = result.get("storytelling", {})
    reel = result.get("reel", {})
    hashtags = result.get("hashtags", [])
    usage = result.get("_usage", {})

    # Build DB row
    content_data = {
        "calendar_id": entry["id"],
        "media_id": ctx["media_id"],
        "caption_short_es": short.get("es", ""),
        "caption_short_en": short.get("en", ""),
        "caption_short_fr": short.get("fr", ""),
        "caption_story_es": story.get("es", ""),
        "caption_story_en": story.get("en", ""),
        "caption_story_fr": story.get("fr", ""),
        "hashtags": hashtags,
        "model": usage.get("model", model),
        "input_tokens": usage.get("input_tokens", 0),
        "output_tokens": usage.get("output_tokens", 0),
        "cost_usd": usage.get("cost_usd", 0),
        "generation_params": {
            "method": "caption_v1",
            "include_image": include_image,
            "theme": ctx["theme_name"],
            "season": ctx["season"],
            "cta_type": cta_type,
        },
        "content_status": "draft",
    }

    # Add reel captions only for video media
    if media.get("media_type") == "video" and reel:
        content_data["caption_reel_es"] = reel.get("es", "")
        content_data["caption_reel_en"] = reel.get("en", "")
        content_data["caption_reel_fr"] = reel.get("fr", "")

    # Insert into DB
    content_id = insert_content(content_data)
    if not content_id:
        return None

    # Link to calendar
    link_content_to_calendar(entry["id"], content_id)

    content_data["id"] = content_id
    return content_data


def estimate_batch_cost(
    entries: list[dict],
    model: str = DEFAULT_MODEL,
    include_image: bool = False,
) -> dict:
    """Estimate cost for batch caption generation.

    Returns dict with: slot_count, estimated_cost_usd, model, model_label
    """
    # Average token estimates based on caption generation patterns
    # Without image: ~800 input, ~600 output
    # With image: ~2000 input (image tokens), ~600 output
    avg_input = 2000 if include_image else 800
    avg_output = 600

    slot_count = len(entries)
    per_slot_cost = compute_cost(model, avg_input, avg_output)
    total_cost = per_slot_cost * slot_count

    model_info = AVAILABLE_MODELS.get(model, AVAILABLE_MODELS[DEFAULT_MODEL])

    return {
        "slot_count": slot_count,
        "per_slot_cost_usd": per_slot_cost,
        "estimated_cost_usd": total_cost,
        "model": model,
        "model_label": model_info.get("label", model),
        "include_image": include_image,
    }
