"""
Batch content generator — V2 flow.
Generates N posts at once using the content recipe from editorial rules.
Calls low-level services directly (no calendar dependency).
"""
import uuid
from datetime import date
from typing import Optional, Callable

from src.database import get_supabase, TABLE_POSTS
from src.services.editorial_engine import (
    get_current_season,
    select_best_media,
    _fetch_analyzed_media,
)
from src.services.editorial_queries import fetch_all_rules
from src.services.posts_queries import create_post, update_post


# -----------------------------------------------------------
# Content recipe from editorial rules
# -----------------------------------------------------------

# Map legacy format values to V2 post_types
_FORMAT_MAP = {
    "feed": "feed",
    "story": "feed",
    "reel": "reel-veo",
    "reel-kling": "reel-kling",
    "reel-veo": "reel-veo",
    "reel-slideshow": "reel-slideshow",
    "carousel": "carousel",
}


def get_content_recipe() -> list[dict]:
    """Read editorial rules, return a list of {category, post_type, focus, min_quality} dicts.

    This represents the weekly content distribution — one entry per active rule.
    """
    rules = fetch_all_rules()
    recipe = []
    for r in rules:
        if not r.get("is_active", True):
            continue
        raw_format = r.get("preferred_format", "feed")
        post_type = _FORMAT_MAP.get(raw_format, "feed")
        recipe.append({
            "category": r.get("default_category", "room"),
            "post_type": post_type,
            "focus": r.get("focus", "hotel"),
            "min_quality": r.get("min_quality", 6),
        })
    return recipe


def scale_recipe(recipe: list[dict], count: int) -> list[dict]:
    """Scale a recipe to exactly `count` items by cycling through it."""
    if not recipe:
        return []
    result = []
    for i in range(count):
        result.append(recipe[i % len(recipe)])
    return result


# -----------------------------------------------------------
# Batch generation
# -----------------------------------------------------------

def generate_batch(
    count: int,
    recipe: list[dict],
    season: Optional[str] = None,
    tone: str = "default",
    min_quality: int = 6,
    model: str = "claude-sonnet-4-6",
    include_image: bool = False,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> dict:
    """Generate a batch of posts.

    Args:
        count: Number of posts to generate.
        recipe: Content recipe (from get_content_recipe + scale_recipe).
        season: Override season (auto-detect if None).
        tone: Caption tone.
        min_quality: Minimum media quality.
        model: Claude model for captions/scenarios.
        include_image: Include image in caption prompt.
        progress_cb: Callback(current, total, message) for progress tracking.

    Returns:
        {batch_id, post_ids, results: [{post_id, status, error}], summary}
    """
    from src.services.caption_generator import generate_captions
    from src.utils import encode_image_bytes
    from src.services.google_drive import download_file_bytes

    batch_id = str(uuid.uuid4())
    today = date.today()
    if not season:
        season = get_current_season(today)

    # Fetch all available media
    all_media = _fetch_analyzed_media()

    # Track used media to avoid duplicates within batch
    batch_used_ids: set[str] = set()
    # Get recently used from posts table (last 14 days)
    recently_used = _fetch_recent_post_media_ids(14)

    items = scale_recipe(recipe, count)
    post_ids = []
    results = []

    for i, item in enumerate(items):
        post_type = item["post_type"]
        category = item["category"]
        quality = max(min_quality, item.get("min_quality", 6))

        if progress_cb:
            progress_cb(i, count, f"Generating {post_type} ({category})...")

        # Select best media for this item
        candidates = select_best_media(
            all_media=all_media,
            target_category=category,
            target_season=season,
            target_format=post_type,
            min_quality=quality,
            theme=None,
            recently_used_ids=recently_used,
            batch_used_ids=batch_used_ids,
            today=today,
            top_n=1,
        )

        if not candidates:
            results.append({"post_id": None, "status": "error", "error": f"No media found for {category}/{post_type}"})
            continue

        media, score, breakdown = candidates[0]
        media_id = media["id"]
        batch_used_ids.add(media_id)

        # Create post row (draft status)
        post_id = create_post({
            "post_type": post_type,
            "media_id": media_id,
            "category": category,
            "season": season,
            "tone": tone,
            "batch_id": batch_id,
            "status": "draft",
            "generation_source": "batch",
        })
        post_ids.append(post_id)

        # Generate content based on type
        try:
            if post_type == "feed":
                _generate_feed_post(post_id, media, season, tone, model, include_image)
                results.append({"post_id": post_id, "status": "ok"})

            elif post_type == "carousel":
                _generate_carousel_post(post_id, media, all_media, season, tone, model, batch_used_ids)
                results.append({"post_id": post_id, "status": "ok"})

            elif post_type.startswith("reel"):
                _generate_reel_post(post_id, media, post_type, season, tone, model)
                results.append({"post_id": post_id, "status": "ok"})

            else:
                results.append({"post_id": post_id, "status": "ok"})

        except Exception as e:
            update_post(post_id, {"status": "failed", "publish_error": str(e)})
            results.append({"post_id": post_id, "status": "error", "error": str(e)})

    if progress_cb:
        progress_cb(count, count, "Done!")

    ok_count = sum(1 for r in results if r["status"] == "ok")
    err_count = sum(1 for r in results if r["status"] == "error")

    return {
        "batch_id": batch_id,
        "post_ids": post_ids,
        "results": results,
        "summary": f"{ok_count} generated, {err_count} errors",
    }


# -----------------------------------------------------------
# Per-type generation
# -----------------------------------------------------------

def _generate_feed_post(post_id, media, season, tone, model, include_image):
    """Generate captions for a feed post and update the post row."""
    from src.services.caption_generator import generate_captions
    from src.utils import encode_image_bytes
    from src.services.google_drive import download_file_bytes

    image_b64 = None
    if include_image and media.get("drive_file_id"):
        try:
            img_bytes = download_file_bytes(media["drive_file_id"])
            image_b64 = encode_image_bytes(img_bytes)
        except Exception:
            pass

    result = generate_captions(
        media=media,
        theme=media.get("description_en", "") or media.get("category", "room"),
        season=season,
        cta_type="auto",
        include_image=include_image,
        image_base64=image_b64,
        model=model,
        tone=tone,
    )

    short = result.get("short", {})
    hashtags = result.get("hashtags", [])
    cost = result.get("_usage", {}).get("cost_usd", 0)

    update_post(post_id, {
        "caption_es": short.get("es", ""),
        "caption_en": short.get("en", ""),
        "caption_fr": short.get("fr", ""),
        "hashtags": hashtags,
        "total_cost_usd": cost,
        "status": "review",
    })


def _generate_carousel_post(post_id, media, all_media, season, tone, model, batch_used_ids):
    """Generate a carousel post — select images + captions."""
    from src.services.carousel_ai import select_carousel_images, generate_carousel_captions
    from src.services.carousel_queries import save_carousel_draft

    category = media.get("category", "room")

    # Select carousel images from library (same category, sorted by quality)
    cat_media = [m for m in all_media
                 if m.get("category") == category
                 and m.get("media_type") == "image"
                 and m["id"] not in batch_used_ids]
    cat_media.sort(key=lambda m: m.get("ig_quality", 0), reverse=True)

    if len(cat_media) < 3:
        # Fallback: use any category
        cat_media = [m for m in all_media
                     if m.get("media_type") == "image"
                     and m["id"] not in batch_used_ids]
        cat_media.sort(key=lambda m: m.get("ig_quality", 0), reverse=True)

    selected_ids = [m["id"] for m in cat_media[:5]]
    if len(selected_ids) < 2:
        raise ValueError(f"Not enough images for carousel ({category})")

    # Mark carousel images as used
    for sid in selected_ids:
        batch_used_ids.add(sid)

    # Generate captions
    try:
        cap_result = generate_carousel_captions(
            theme=media.get("description_en", "") or category,
            image_descriptions=[m.get("description_fr", "") for m in cat_media[:5]],
            model=model,
        )
        cap_es = cap_result.get("caption_es", "")
        cap_en = cap_result.get("caption_en", "")
        cap_fr = cap_result.get("caption_fr", "")
        hashtags = cap_result.get("hashtags", [])
        cost = cap_result.get("_usage", {}).get("cost_usd", 0)
    except Exception:
        cap_es, cap_en, cap_fr = "", "", ""
        hashtags = []
        cost = 0

    # Save carousel draft
    draft_id = save_carousel_draft(
        title=f"Batch: {category}",
        media_ids=selected_ids,
        caption_es=cap_es,
        caption_en=cap_en,
        caption_fr=cap_fr,
        hashtags=hashtags,
    )

    update_post(post_id, {
        "caption_es": cap_es,
        "caption_en": cap_en,
        "caption_fr": cap_fr,
        "hashtags": hashtags,
        "carousel_draft_id": draft_id,
        "total_cost_usd": cost,
        "status": "review",
    })


def _generate_reel_post(post_id, media, post_type, season, tone, model):
    """Generate a reel post — full auto: scenario → video → music → composite.

    For Veo: scenario → video (native audio, no music step).
    For Kling: scenario → video → music → composite.
    For Slideshow: select images → slideshow → music → composite.
    """
    from src.services.creative_transform import generate_scenarios, photo_to_video, VIDEO_MODELS
    from src.services.google_drive import download_file_bytes
    from src.utils import encode_image_bytes
    from src.services.creative_job_queries import save_scenario_job, save_video_job, save_music_job
    from src.services.creative_queries import update_scenario_feedback

    total_cost = 0.0

    # Step 1: Download source image
    drive_file_id = media.get("drive_file_id")
    if not drive_file_id:
        raise ValueError("Media has no drive_file_id")

    image_bytes = download_file_bytes(drive_file_id)
    image_b64 = encode_image_bytes(image_bytes)

    # Step 2: Generate 3 scenarios
    scenario_result = generate_scenarios(
        media=media,
        creative_brief=f"Create a {season} reel for {media.get('category', 'hotel')}",
        hotel_context="",
        count=3,
        image_base64=image_b64,
        model=model,
    )
    scenarios = scenario_result.get("scenarios", [])
    total_cost += scenario_result.get("_usage", {}).get("cost_usd", 0)

    # Save scenarios
    save_scenario_job(
        source_media_id=media["id"],
        scenarios=scenarios,
        cost_usd=scenario_result.get("_usage", {}).get("cost_usd", 0),
        params={"batch": True, "post_id": post_id},
    )

    if not scenarios:
        raise ValueError("No scenarios generated")

    # Auto-pick best scenario (first one)
    chosen = scenarios[0]
    motion_prompt = chosen.get("motion_prompt", chosen.get("description", ""))
    char_ids = chosen.get("characters_used", []) or []

    # Step 3: Generate video (with character references if scenario uses them)
    if post_type == "reel-veo":
        video_result = _generate_veo_video(
            image_bytes, motion_prompt,
            reference_character_ids=char_ids if char_ids else None,
        )
    else:  # reel-kling
        video_result = photo_to_video(
            image_bytes=image_bytes,
            prompt=motion_prompt,
            duration=5,
            aspect_ratio="9:16",
            reference_character_ids=char_ids if char_ids else None,
        )

    total_cost += video_result.get("_cost", {}).get("cost_usd", 0)
    video_url = video_result.get("video_url", "")

    # Save video job
    job_row = save_video_job(
        source_media_id=media["id"],
        video_url=video_url,
        prompt=motion_prompt,
        cost_usd=video_result.get("_cost", {}).get("cost_usd", 0),
        provider="veo" if post_type == "reel-veo" else "replicate",
        params={"post_type": post_type, "post_id": post_id},
    )
    video_job_id = job_row.get("id") if job_row else None

    # Step 4: Music + composite (only for non-Veo reels)
    music_id = None
    if post_type != "reel-veo" and video_result.get("video_bytes"):
        try:
            from src.services.music_generator import generate_music
            from src.services.video_composer import composite_video_audio
            from src.prompts.music_generation import build_music_prompt

            music_prompt = build_music_prompt(media)
            mu_result = generate_music(prompt=music_prompt, duration=8)
            total_cost += mu_result.get("_cost", {}).get("cost_usd", 0)

            mu_job = save_music_job(
                source_media_id=media["id"],
                audio_url="",
                prompt=music_prompt,
                cost_usd=mu_result.get("_cost", {}).get("cost_usd", 0),
                params={"post_id": post_id},
            )
            music_id = mu_job.get("id") if mu_job else None

            # Composite video + music
            if mu_result.get("audio_bytes"):
                comp_result = composite_video_audio(
                    video_bytes=video_result["video_bytes"],
                    audio_bytes=mu_result["audio_bytes"],
                    music_volume=0.3,
                )
                # Update video job with composite result if possible
        except Exception:
            pass  # Music is optional, don't fail the whole post

    # Step 5: Generate captions for the reel (using scenario context)
    try:
        from src.services.caption_generator import generate_captions

        caption_hook = chosen.get("caption_hook", "")
        scenario_desc = chosen.get("description", "")
        reel_context = ""
        if caption_hook:
            reel_context += f"Opening hook: {caption_hook}\n"
        if scenario_desc:
            reel_context += f"Video concept: {scenario_desc}\n"

        cap_result = generate_captions(
            media=media,
            theme=reel_context if reel_context else media.get("description_en", "") or media.get("category", "room"),
            season=season,
            cta_type="auto",
            include_image=False,
            model=model,
            tone=tone,
        )
        short = cap_result.get("short", {})
        hashtags = cap_result.get("hashtags", [])
        total_cost += cap_result.get("_usage", {}).get("cost_usd", 0)
    except Exception:
        short = {}
        hashtags = []

    update_post(post_id, {
        "caption_es": short.get("es", ""),
        "caption_en": short.get("en", ""),
        "caption_fr": short.get("fr", ""),
        "hashtags": hashtags,
        "video_job_id": video_job_id,
        "music_id": music_id,
        "total_cost_usd": total_cost,
        "status": "review",
    })


def _generate_veo_video(image_bytes, prompt, reference_character_ids=None):
    """Generate video using Veo 3.1."""
    from src.services.veo_generator import veo_photo_to_video

    return veo_photo_to_video(
        image_bytes=image_bytes,
        prompt=prompt,
        duration=8 if reference_character_ids else 6,
        aspect_ratio="9:16",
        model="veo-3.1-fast",
        reference_character_ids=reference_character_ids,
    )


# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------

def _fetch_recent_post_media_ids(lookback_days: int = 14) -> set[str]:
    """Get media IDs used in recent posts (to avoid repetition)."""
    from datetime import timedelta

    client = get_supabase()
    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
    try:
        result = (
            client.table(TABLE_POSTS)
            .select("media_id")
            .gte("created_at", cutoff)
            .not_.is_("media_id", "null")
            .execute()
        )
        return {r["media_id"] for r in result.data if r.get("media_id")}
    except Exception:
        return set()


def retry_failed_posts(
    batch_id: Optional[str] = None,
    post_ids: Optional[list[str]] = None,
    progress_cb: Optional[Callable[[int, int, str], None]] = None,
) -> dict:
    """Retry generation for failed posts without losing successful ones.

    Pass either batch_id (retries all failed in that batch) or explicit post_ids.
    Re-runs the generation step for each failed post using its existing metadata
    (media_id, post_type, category, season, tone). Does NOT create new posts —
    updates the existing rows in place.

    Returns: {retried: int, succeeded: int, still_failed: int, results: [...]}
    """
    from src.services.caption_generator import generate_captions
    from src.services.google_drive import download_file_bytes
    from src.utils import encode_image_bytes

    client = get_supabase()

    if batch_id:
        failed = client.table(TABLE_POSTS).select("*").eq("batch_id", batch_id).eq("status", "failed").execute().data
    elif post_ids:
        failed = client.table(TABLE_POSTS).select("*").in_("id", post_ids).eq("status", "failed").execute().data
    else:
        failed = client.table(TABLE_POSTS).select("*").eq("status", "failed").order("created_at", desc=True).limit(50).execute().data

    if not failed:
        return {"retried": 0, "succeeded": 0, "still_failed": 0, "results": []}

    all_media = _fetch_analyzed_media()
    media_map = {m["id"]: m for m in all_media}
    results = []

    for i, post in enumerate(failed):
        post_id = post["id"]
        post_type = post["post_type"]
        media_id = post.get("media_id")
        season = post.get("season") or get_current_season(date.today())
        tone = post.get("tone") or "default"

        if progress_cb:
            progress_cb(i, len(failed), f"Retrying {post_type} ({post_id[:8]})...")

        media = media_map.get(media_id)
        if not media:
            results.append({"post_id": post_id, "status": "error", "error": "Media not found"})
            continue

        # Reset status to draft
        update_post(post_id, {"status": "draft", "publish_error": None})

        try:
            if post_type == "feed":
                _generate_feed_post(post_id, media, season, tone, "claude-sonnet-4-6", False)
            elif post_type == "carousel":
                _generate_carousel_post(post_id, media, all_media, season, tone, "claude-sonnet-4-6", set())
            elif post_type.startswith("reel"):
                _generate_reel_post(post_id, media, post_type, season, tone, "claude-sonnet-4-6")
            results.append({"post_id": post_id, "status": "ok"})
        except Exception as e:
            update_post(post_id, {"status": "failed", "publish_error": str(e)})
            results.append({"post_id": post_id, "status": "error", "error": str(e)})

    if progress_cb:
        progress_cb(len(failed), len(failed), "Done!")

    ok = sum(1 for r in results if r["status"] == "ok")
    err = sum(1 for r in results if r["status"] == "error")

    return {"retried": len(failed), "succeeded": ok, "still_failed": err, "results": results}


def estimate_batch_cost(recipe: list[dict], count: int) -> dict:
    """Estimate the cost of a batch run.

    Returns: {total_usd, breakdown: [{type, count, unit_cost, subtotal}]}
    """
    items = scale_recipe(recipe, count)
    breakdown = {}
    for item in items:
        pt = item["post_type"]
        if pt not in breakdown:
            breakdown[pt] = {"type": pt, "count": 0, "unit_cost": 0, "subtotal": 0}
        breakdown[pt]["count"] += 1

    # Cost estimates per type
    UNIT_COSTS = {
        "feed": 0.03,           # captions only
        "carousel": 0.05,      # captions + image selection
        "reel-kling": 0.80,    # scenario + Kling V3 Omni video + music + captions
        "reel-veo": 1.25,      # scenario + Veo 3.1 Fast 8s + captions
        "reel-slideshow": 0.10, # slideshow (free) + music + captions
    }

    total = 0
    for pt, info in breakdown.items():
        info["unit_cost"] = UNIT_COSTS.get(pt, 0.01)
        info["subtotal"] = info["unit_cost"] * info["count"]
        total += info["subtotal"]

    return {
        "total_usd": round(total, 2),
        "breakdown": list(breakdown.values()),
    }
