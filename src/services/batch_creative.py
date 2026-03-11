"""
Batch Creative Pipeline — orchestrate scenario/video/music/composite generation
for all calendar slots in a date range, with content-type routing.

Routes:
  feed           → Caption only (no batch action)
  carousel       → AI select images → caption → save carousel draft
  reel-kling     → Scenario → Kling video → Music → Composite
  reel-veo       → Scenario → Veo video → Done (native audio)
  reel-slideshow → Select images → Ken Burns slideshow → Music → Composite

Each pass is independent and idempotent. Slots already processed are skipped.
Review gates (accept/reject) happen between passes via Drafts Review page.
"""
import json
from datetime import datetime
from typing import Callable, Optional

from src.services.media_queries import fetch_media_by_id
from src.services.google_drive import download_file_bytes, upload_file_to_drive, ensure_generated_folders
from src.services.publisher import upload_to_supabase_storage
from src.services.creative_job_queries import save_scenario_job, save_video_job, save_music_job
from src.services.creative_queries import (
    fetch_scenarios_for_calendar_ids,
    fetch_accepted_scenario_for_calendar,
    fetch_accepted_video_for_calendar,
    fetch_music_for_calendar,
    fetch_videos_for_calendar_ids,
    fetch_composite_for_calendar_ids,
    fetch_slideshows_for_calendar_ids,
)
from src.services.editorial_queries import update_calendar_creative_status
from src.services.creative_transform import (
    generate_scenarios,
    photo_to_video,
    VIDEO_MODELS,
    estimate_video_cost as _estimate_single_video_cost,
)
from src.services.music_generator import generate_music
from src.services.video_composer import composite_video_audio, images_to_slideshow
from src.prompts.music_generation import build_music_prompt
from src.utils import encode_image_bytes


# ---------------------------------------------------------------------------
# Route constants
# ---------------------------------------------------------------------------

ROUTE_VIDEO_MODEL = {
    "reel-kling": "kling-v2.1",
    "reel-veo": "veo-3.1-fast",
}

# Routes that need music + composite
ROUTES_NEED_MUSIC = {"reel-kling", "reel-slideshow"}

# Routes that go through the scenario → video pipeline
ROUTES_REEL = {"reel-kling", "reel-veo"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ProgressCallback = Optional[Callable[[int, int, str], None]]


def _get_media_and_image(slot: dict, include_image: bool = True) -> tuple[Optional[dict], Optional[str]]:
    """Fetch media row and optionally download + encode image for a calendar slot."""
    media_id = slot.get("manual_media_id") or slot.get("media_id")
    if not media_id:
        return None, None
    media = fetch_media_by_id(media_id)
    if not media:
        return None, None

    image_b64 = None
    if include_image and media.get("drive_file_id"):
        try:
            raw = download_file_bytes(media["drive_file_id"])
            image_b64 = encode_image_bytes(raw)
        except Exception:
            pass  # proceed without image

    return media, image_b64


def classify_slots_by_route(slots: list[dict]) -> dict[str, list[dict]]:
    """Group calendar slots by their route (target_format).

    Handles legacy values: 'story' → 'feed', 'reel' → 'reel-kling', NULL → 'feed'.
    """
    groups: dict[str, list[dict]] = {
        "feed": [], "carousel": [], "reel-kling": [], "reel-veo": [], "reel-slideshow": [],
    }
    for s in slots:
        route = s.get("target_format") or "feed"
        # Legacy compat
        if route == "story":
            route = "feed"
        if route == "reel":
            route = "reel-veo"
        groups.setdefault(route, []).append(s)
    return groups


def get_video_model_for_slot(slot: dict) -> str:
    """Return the video model string for a slot's route."""
    route = slot.get("target_format") or "reel-veo"
    if route == "reel":
        route = "reel-veo"
    return ROUTE_VIDEO_MODEL.get(route, "kling-v2.1")


# ---------------------------------------------------------------------------
# Pass 1: Scenarios (Claude, ~5-10s per slot) — reel-kling + reel-veo only
# ---------------------------------------------------------------------------

def batch_generate_scenarios(
    slots: list[dict],
    count: int = 3,
    model: str = "claude-sonnet-4-6",
    include_image: bool = True,
    progress_callback: ProgressCallback = None,
) -> dict:
    """Generate creative scenarios for calendar slots.

    Skips slots that already have scenarios for this calendar_id.

    Returns: {total, success, skipped, failed, errors: [], total_cost}
    """
    total = len(slots)
    success = 0
    skipped = 0
    failed = 0
    errors = []
    total_cost = 0.0

    # Pre-check which slots already have scenarios
    cal_ids = [s["id"] for s in slots]
    existing = fetch_scenarios_for_calendar_ids(cal_ids)

    for i, slot in enumerate(slots):
        cal_id = slot["id"]
        if progress_callback:
            progress_callback(i, total, f"Slot {i+1}/{total}: generating scenarios...")

        # Skip if already has active (non-rejected) scenarios
        if cal_id in existing:
            active = [s for s in existing[cal_id] if s.get("status") != "rejected"]
            if active:
                skipped += 1
                continue

        try:
            media, image_b64 = _get_media_and_image(slot, include_image)
            if not media:
                errors.append(f"Slot {slot.get('post_date')} S{slot.get('slot_index', 1)}: no media assigned")
                failed += 1
                continue

            result = generate_scenarios(
                media=media,
                count=count,
                image_base64=image_b64,
                model=model,
            )

            scenarios = result.get("scenarios", [])
            cost = result.get("_usage", {}).get("cost_usd", 0)
            total_cost += cost

            save_scenario_job(
                source_media_id=media["id"],
                scenarios=scenarios,
                cost_usd=cost,
                params={"count": count, "include_image": include_image, "batch": True},
                model=model,
                calendar_id=cal_id,
            )

            update_calendar_creative_status(cal_id, "scenarios_draft")
            success += 1

        except Exception as e:
            errors.append(f"Slot {slot.get('post_date')} S{slot.get('slot_index', 1)}: {e}")
            failed += 1

    if progress_callback:
        progress_callback(total, total, "Scenarios complete!")

    return {
        "total": total,
        "success": success,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
        "total_cost": total_cost,
    }


# ---------------------------------------------------------------------------
# Pass 2: Videos (Kling/Veo, 1-5 min per slot) — route determines model
# ---------------------------------------------------------------------------

def batch_generate_videos(
    slots: list[dict],
    video_model: str = "kling-v2.1",
    duration: int = 5,
    aspect_ratio: str = "9:16",
    progress_callback: ProgressCallback = None,
) -> dict:
    """Generate videos for calendar slots with accepted scenarios.

    Per slot: finds accepted scenario → uses motion_prompt → generates video.
    The video_model parameter is used as a fallback; route-aware callers
    can pass slots that already have their model determined by route.

    Returns: {total, success, skipped, failed, errors: [], total_cost}
    """
    total = len(slots)
    success = 0
    skipped = 0
    failed = 0
    errors = []
    total_cost = 0.0

    # Pre-check which slots already have videos
    cal_ids = [s["id"] for s in slots]
    existing_videos = fetch_videos_for_calendar_ids(cal_ids)

    for i, slot in enumerate(slots):
        cal_id = slot["id"]
        # Use explicit model if caller specified one, otherwise derive from route
        slot_model = video_model if video_model != "kling-v2.1" else get_video_model_for_slot(slot)
        # Adapt duration for provider
        model_info = VIDEO_MODELS.get(slot_model, {})
        slot_duration = duration
        if model_info.get("provider") == "google" and duration not in (4, 6, 8):
            slot_duration = 4  # default short for Veo
        elif model_info.get("provider") != "google" and duration not in (5, 10):
            slot_duration = 5

        if progress_callback:
            progress_callback(i, total, f"Slot {i+1}/{total}: generating video ({slot_model})...")

        # Skip if already has an active (non-rejected) video
        if cal_id in existing_videos:
            active = [v for v in existing_videos[cal_id] if v.get("status") != "rejected"]
            if active:
                skipped += 1
                continue

        try:
            # Find accepted scenario
            scenario = fetch_accepted_scenario_for_calendar(cal_id)
            if not scenario:
                skipped += 1  # no accepted scenario — skip (not an error)
                continue

            media, _ = _get_media_and_image(slot, include_image=True)
            if not media or not media.get("drive_file_id"):
                errors.append(f"Slot {slot.get('post_date')} S{slot.get('slot_index', 1)}: no media/image")
                failed += 1
                continue

            # Download full-res image for video gen
            image_bytes = download_file_bytes(media["drive_file_id"])
            motion_prompt = scenario.get("motion_prompt", "")

            result = photo_to_video(
                image_bytes=image_bytes,
                prompt=motion_prompt,
                duration=slot_duration,
                aspect_ratio=aspect_ratio,
                model=slot_model,
            )

            cost = result["_cost"]["cost_usd"]
            total_cost += cost

            # Upload to Storage + Drive
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = media.get("file_name", "video").rsplit(".", 1)[0][:40]
            fname = f"{stem}_reel_{ts}.mp4"

            video_url = upload_to_supabase_storage(result["video_bytes"], fname, "video/mp4")

            drive_fid = None
            try:
                folders = ensure_generated_folders()
                drive_result = upload_file_to_drive(
                    result["video_bytes"], fname, "video/mp4", folders["videos"],
                )
                drive_fid = drive_result["id"]
            except Exception:
                pass

            provider = VIDEO_MODELS[slot_model].get("provider", "replicate")
            save_video_job(
                source_media_id=media["id"],
                video_url=video_url,
                prompt=motion_prompt,
                cost_usd=cost,
                provider=provider,
                params={"duration": slot_duration, "aspect_ratio": aspect_ratio, "model": slot_model, "batch": True},
                drive_file_id=drive_fid,
                calendar_id=cal_id,
            )

            update_calendar_creative_status(cal_id, "video_draft")
            success += 1

        except Exception as e:
            errors.append(f"Slot {slot.get('post_date')} S{slot.get('slot_index', 1)}: {e}")
            failed += 1

    if progress_callback:
        progress_callback(total, total, "Videos complete!")

    return {
        "total": total,
        "success": success,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
        "total_cost": total_cost,
    }


# ---------------------------------------------------------------------------
# Pass 3: Music (MusicGen, 1-2 min per slot) — reel-kling + reel-slideshow
# ---------------------------------------------------------------------------

def batch_generate_music(
    slots: list[dict],
    music_duration: int = 10,
    progress_callback: ProgressCallback = None,
) -> dict:
    """Generate music for calendar slots with accepted videos or slideshows.

    Per slot: finds accepted video → builds music prompt from media metadata →
    generates music → uploads to Drive → saves.
    Skips slots without accepted videos or already with music.

    Returns: {total, success, skipped, failed, errors: [], total_cost}
    """
    from src.services.creative_queries import fetch_music_for_calendar_ids

    total = len(slots)
    success = 0
    skipped = 0
    failed = 0
    errors = []
    total_cost = 0.0

    # Pre-check which slots already have music
    cal_ids = [s["id"] for s in slots]
    existing_music = fetch_music_for_calendar_ids(cal_ids)

    for i, slot in enumerate(slots):
        cal_id = slot["id"]
        if progress_callback:
            progress_callback(i, total, f"Slot {i+1}/{total}: generating music...")

        # Skip if already has active (non-rejected) music
        if cal_id in existing_music:
            active = [m for m in existing_music[cal_id] if m.get("status") != "rejected"]
            if active:
                skipped += 1
                continue

        try:
            # Check for accepted video (covers both reel-kling and slideshow)
            video = fetch_accepted_video_for_calendar(cal_id)
            if not video:
                # Also check slideshow jobs
                from src.services.creative_queries import fetch_slideshow_for_calendar
                slideshow = fetch_slideshow_for_calendar(cal_id)
                if not slideshow:
                    skipped += 1
                    continue

            media, _ = _get_media_and_image(slot, include_image=False)
            if not media:
                errors.append(f"Slot {slot.get('post_date')} S{slot.get('slot_index', 1)}: no media")
                failed += 1
                continue

            prompt = build_music_prompt(media)

            result = generate_music(
                prompt=prompt,
                duration=music_duration,
            )

            cost = result["_cost"]["cost_usd"]
            total_cost += cost

            # Upload to Drive
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = media.get("file_name", "music").rsplit(".", 1)[0][:40]
            fname = f"{stem}_music_{ts}.wav"

            drive_fid = None
            audio_url = ""
            try:
                folders = ensure_generated_folders()
                drive_result = upload_file_to_drive(
                    result["audio_bytes"], fname, "audio/wav", folders["music"],
                )
                drive_fid = drive_result["id"]
                audio_url = drive_result.get("webViewLink", "")
            except Exception:
                pass

            save_music_job(
                source_media_id=media["id"],
                audio_url=audio_url,
                prompt=prompt,
                cost_usd=cost,
                params={"duration": music_duration, "batch": True},
                drive_file_id=drive_fid,
                calendar_id=cal_id,
            )

            update_calendar_creative_status(cal_id, "music_draft")
            success += 1

        except Exception as e:
            errors.append(f"Slot {slot.get('post_date')} S{slot.get('slot_index', 1)}: {e}")
            failed += 1

    if progress_callback:
        progress_callback(total, total, "Music complete!")

    return {
        "total": total,
        "success": success,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
        "total_cost": total_cost,
    }


# ---------------------------------------------------------------------------
# Pass 4: Composite (FFmpeg, ~30s per slot, free) — reel-kling + reel-slideshow
# ---------------------------------------------------------------------------

def batch_composite(
    slots: list[dict],
    volume: float = 0.3,
    progress_callback: ProgressCallback = None,
) -> dict:
    """Merge accepted video + accepted music into final MP4.

    Skips slots without both accepted video AND accepted music.

    Returns: {total, success, skipped, failed, errors: [], total_cost}
    """
    import httpx

    total = len(slots)
    success = 0
    skipped = 0
    failed = 0
    errors = []

    # Pre-check which slots already have composites
    cal_ids = [s["id"] for s in slots]
    existing_composites = fetch_composite_for_calendar_ids(cal_ids)

    for i, slot in enumerate(slots):
        cal_id = slot["id"]
        if progress_callback:
            progress_callback(i, total, f"Slot {i+1}/{total}: compositing...")

        # Skip if already has an active (non-rejected) composite
        if cal_id in existing_composites:
            active = [c for c in existing_composites[cal_id] if c.get("status") != "rejected"]
            if active:
                skipped += 1
                continue

        try:
            # Need accepted video + accepted music
            video = fetch_accepted_video_for_calendar(cal_id)
            music = fetch_music_for_calendar(cal_id)

            # For slideshows, also check slideshow jobs
            if not video:
                from src.services.creative_queries import fetch_slideshow_for_calendar
                video = fetch_slideshow_for_calendar(cal_id)

            if not video or not music:
                skipped += 1
                continue

            # Download video bytes
            video_url = video.get("result_url", "")
            video_drive_id = video.get("drive_file_id")
            if video_drive_id:
                video_bytes = download_file_bytes(video_drive_id)
            elif video_url:
                resp = httpx.get(video_url, timeout=120, follow_redirects=True)
                resp.raise_for_status()
                video_bytes = resp.content
            else:
                errors.append(f"Slot {slot.get('post_date')}: no video URL")
                failed += 1
                continue

            # Download music bytes (from Drive if available)
            music_drive_id = music.get("drive_file_id")
            music_url = music.get("audio_url", "")
            if music_drive_id:
                audio_bytes = download_file_bytes(music_drive_id)
            elif music_url:
                resp = httpx.get(music_url, timeout=120, follow_redirects=True)
                resp.raise_for_status()
                audio_bytes = resp.content
            else:
                errors.append(f"Slot {slot.get('post_date')}: no music source")
                failed += 1
                continue

            result = composite_video_audio(
                video_bytes=video_bytes,
                audio_bytes=audio_bytes,
                volume=volume,
            )

            # Upload composite to Storage + Drive
            media_id = slot.get("manual_media_id") or slot.get("media_id")
            media = fetch_media_by_id(media_id) if media_id else None
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = (media.get("file_name", "comp") if media else "comp").rsplit(".", 1)[0][:40]
            fname = f"{stem}_reel_music_{ts}.mp4"

            comp_url = upload_to_supabase_storage(result["video_bytes"], fname, "video/mp4")

            drive_fid = None
            try:
                folders = ensure_generated_folders()
                drive_result = upload_file_to_drive(
                    result["video_bytes"], fname, "video/mp4", folders["videos"],
                )
                drive_fid = drive_result["id"]
            except Exception:
                pass

            # Save as a creative_job with type "video_composite"
            from src.database import get_supabase, TABLE_CREATIVE_JOBS
            client = get_supabase()
            row = {
                "source_media_id": media_id,
                "job_type": "video_composite",
                "provider": "ffmpeg",
                "status": "completed",
                "params": json.dumps({"volume": volume, "batch": True}),
                "cost_usd": 0.0,
                "result_url": comp_url,
                "calendar_id": cal_id,
            }
            if drive_fid:
                row["drive_file_id"] = drive_fid
            client.table(TABLE_CREATIVE_JOBS).insert(row).execute()

            update_calendar_creative_status(cal_id, "composite_done")
            success += 1

        except Exception as e:
            errors.append(f"Slot {slot.get('post_date')} S{slot.get('slot_index', 1)}: {e}")
            failed += 1

    if progress_callback:
        progress_callback(total, total, "Composites complete!")

    return {
        "total": total,
        "success": success,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
        "total_cost": 0.0,
    }


# ---------------------------------------------------------------------------
# Carousel batch (AI select images + captions)
# ---------------------------------------------------------------------------

def batch_generate_carousels(
    slots: list[dict],
    model: str = "claude-sonnet-4-6",
    slide_count: int = 5,
    progress_callback: ProgressCallback = None,
) -> dict:
    """Generate carousel drafts for calendar slots with route='carousel'.

    Per slot: uses category/season context → AI selects images → generates captions
    → saves carousel draft linked to calendar slot.

    Returns: {total, success, skipped, failed, errors: [], total_cost}
    """
    from src.services.carousel_ai import select_carousel_images, generate_carousel_captions
    from src.services.carousel_queries import save_carousel_draft, fetch_carousels_for_calendar_ids
    from src.services.editorial_engine import _fetch_analyzed_media

    total = len(slots)
    success = 0
    skipped = 0
    failed = 0
    errors = []
    total_cost = 0.0

    # Pre-check which slots already have carousels
    cal_ids = [s["id"] for s in slots]
    existing = fetch_carousels_for_calendar_ids(cal_ids)

    # Fetch full media library for image selection
    all_media = _fetch_analyzed_media()

    for i, slot in enumerate(slots):
        cal_id = slot["id"]
        if progress_callback:
            progress_callback(i, total, f"Slot {i+1}/{total}: generating carousel...")

        # Skip if already has an active (non-rejected) carousel
        if cal_id in existing:
            active = [c for c in existing[cal_id] if c.get("status") != "rejected"]
            if active:
                skipped += 1
                continue

        try:
            cat = slot.get("target_category") or "experience"
            season = slot.get("season_context") or "toute_saison"
            theme_name = slot.get("theme_name") or ""
            post_date = slot.get("post_date", "")

            # Filter media by category (with fallback to all if too few)
            cat_media = [m for m in all_media if m.get("category") == cat]
            if len(cat_media) < slide_count * 2:
                cat_media = all_media  # fallback to full library

            # Build theme context for image selection
            theme_desc = f"Hotel content for {cat} category, {season} season"
            if theme_name:
                theme_desc += f", theme: {theme_name}"

            # Step 1: AI select images
            sel_result = select_carousel_images(
                theme_title=f"{cat.title()} — {post_date}",
                theme_description=theme_desc,
                ordering="narrative arc",
                slide_count=slide_count,
                media_list=cat_media,
                model=model,
            )
            sel_cost = sel_result.get("_usage", {}).get("cost_usd", 0)
            total_cost += sel_cost

            selected = sel_result.get("selected", [])
            if not selected:
                errors.append(f"Slot {post_date}: AI returned no images")
                failed += 1
                continue

            media_ids = [s["media_id"] for s in selected if s.get("media_id")]
            if not media_ids:
                errors.append(f"Slot {post_date}: no valid media IDs in selection")
                failed += 1
                continue

            # Gather media dicts for caption generation
            selected_media = [m for m in all_media if m["id"] in media_ids]
            # Preserve ordering from AI selection
            id_order = {mid: idx for idx, mid in enumerate(media_ids)}
            selected_media.sort(key=lambda m: id_order.get(m["id"], 999))

            # Step 2: Generate captions
            cap_result = generate_carousel_captions(
                theme_title=sel_result.get("carousel_title", f"{cat.title()} Carousel"),
                theme_description=theme_desc,
                selected_media=selected_media,
                model=model,
            )
            cap_cost = cap_result.get("_usage", {}).get("cost_usd", 0)
            total_cost += cap_cost

            # Step 3: Save carousel draft linked to calendar
            title = sel_result.get("carousel_title", f"{cat.title()} — {post_date}")
            save_carousel_draft(
                title=title,
                media_ids=media_ids,
                caption_es=cap_result.get("caption_es", ""),
                caption_en=cap_result.get("caption_en", ""),
                caption_fr=cap_result.get("caption_fr", ""),
                hashtags=cap_result.get("hashtags", []),
                calendar_id=cal_id,
            )

            update_calendar_creative_status(cal_id, "carousel_draft")
            success += 1

        except Exception as e:
            errors.append(f"Slot {slot.get('post_date')} S{slot.get('slot_index', 1)}: {e}")
            failed += 1

    if progress_callback:
        progress_callback(total, total, "Carousels complete!")

    return {
        "total": total,
        "success": success,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
        "total_cost": total_cost,
    }


# ---------------------------------------------------------------------------
# Slideshow batch (Ken Burns from images — free, FFmpeg)
# ---------------------------------------------------------------------------

def batch_generate_slideshows(
    slots: list[dict],
    slide_count: int = 5,
    duration_per_slide: float = 3.0,
    progress_callback: ProgressCallback = None,
) -> dict:
    """Generate Ken Burns slideshow videos for calendar slots with route='reel-slideshow'.

    Per slot: select top images by category/season → download → images_to_slideshow →
    upload MP4 → save creative_job.

    Returns: {total, success, skipped, failed, errors: [], total_cost}
    """
    from src.services.editorial_engine import _fetch_analyzed_media, score_media, get_current_season
    from src.database import get_supabase, TABLE_CREATIVE_JOBS
    from datetime import date

    total = len(slots)
    success = 0
    skipped = 0
    failed = 0
    errors = []

    # Pre-check which slots already have slideshows
    cal_ids = [s["id"] for s in slots]
    existing = fetch_slideshows_for_calendar_ids(cal_ids)

    # Fetch full media library
    all_media = _fetch_analyzed_media()
    # Only images
    image_media = [m for m in all_media if m.get("media_type") == "image"]

    for i, slot in enumerate(slots):
        cal_id = slot["id"]
        if progress_callback:
            progress_callback(i, total, f"Slot {i+1}/{total}: generating slideshow...")

        # Skip if already has an active (non-rejected) slideshow
        if cal_id in existing:
            active = [s for s in existing[cal_id] if s.get("status") != "rejected"]
            if active:
                skipped += 1
                continue

        try:
            cat = slot.get("target_category") or "experience"
            season = slot.get("season_context") or "toute_saison"
            post_date_str = slot.get("post_date", date.today().isoformat())
            post_date = date.fromisoformat(post_date_str) if isinstance(post_date_str, str) else post_date_str

            # Score and rank images for this slot's category/season
            scored = []
            for m in image_media:
                sc, _ = score_media(m, cat, season, "reel-slideshow", None, set(), post_date)
                scored.append((m, sc))
            scored.sort(key=lambda x: x[1], reverse=True)
            top_media = [m for m, _ in scored[:slide_count]]

            if len(top_media) < 2:
                errors.append(f"Slot {post_date_str}: not enough images for slideshow")
                failed += 1
                continue

            # Download image bytes
            image_bytes_list = []
            for m in top_media:
                if m.get("drive_file_id"):
                    try:
                        raw = download_file_bytes(m["drive_file_id"])
                        image_bytes_list.append(raw)
                    except Exception:
                        pass

            if len(image_bytes_list) < 2:
                errors.append(f"Slot {post_date_str}: could not download enough images")
                failed += 1
                continue

            # Generate slideshow
            result = images_to_slideshow(
                image_bytes_list=image_bytes_list,
                duration_per_slide=duration_per_slide,
                aspect_ratio="9:16",
            )

            video_bytes = result["video_bytes"]

            # Upload to Storage + Drive
            media_id = slot.get("manual_media_id") or slot.get("media_id")
            source_media = fetch_media_by_id(media_id) if media_id else None
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = (source_media.get("file_name", "slideshow") if source_media else "slideshow").rsplit(".", 1)[0][:40]
            fname = f"{stem}_slideshow_{ts}.mp4"

            video_url = upload_to_supabase_storage(video_bytes, fname, "video/mp4")

            drive_fid = None
            try:
                folders = ensure_generated_folders()
                drive_result = upload_file_to_drive(
                    video_bytes, fname, "video/mp4", folders["videos"],
                )
                drive_fid = drive_result["id"]
            except Exception:
                pass

            # Save as creative_job with type "slideshow"
            client = get_supabase()
            row = {
                "source_media_id": media_id,
                "job_type": "slideshow",
                "provider": "ffmpeg",
                "status": "completed",
                "params": json.dumps({
                    "slides": len(image_bytes_list),
                    "duration_per_slide": duration_per_slide,
                    "media_ids": [m["id"] for m in top_media],
                    "batch": True,
                }),
                "cost_usd": 0.0,
                "result_url": video_url,
                "calendar_id": cal_id,
            }
            if drive_fid:
                row["drive_file_id"] = drive_fid
            client.table(TABLE_CREATIVE_JOBS).insert(row).execute()

            update_calendar_creative_status(cal_id, "slideshow_done")
            success += 1

        except Exception as e:
            errors.append(f"Slot {slot.get('post_date')} S{slot.get('slot_index', 1)}: {e}")
            failed += 1

    if progress_callback:
        progress_callback(total, total, "Slideshows complete!")

    return {
        "total": total,
        "success": success,
        "skipped": skipped,
        "failed": failed,
        "errors": errors,
        "total_cost": 0.0,
    }


# ---------------------------------------------------------------------------
# Cost Estimators
# ---------------------------------------------------------------------------

def estimate_scenario_cost(
    slot_count: int,
    count: int = 3,
    include_image: bool = True,
    model: str = "claude-sonnet-4-6",
) -> dict:
    """Estimate cost for scenario batch."""
    # ~1500 input tokens (text) + ~5000 (image) + ~500 output per call
    rates = {"claude-sonnet-4-6": (3.0, 15.0), "claude-haiku-4-5-20251001": (0.8, 4.0)}
    inp_rate, out_rate = rates.get(model, (3.0, 15.0))
    inp_tokens = 1500 + (5000 if include_image else 0)
    out_tokens = 500 * count  # roughly scales with count
    per_slot = (inp_tokens * inp_rate + out_tokens * out_rate) / 1_000_000
    return {
        "per_slot": round(per_slot, 4),
        "total": round(per_slot * slot_count, 4),
        "model": model,
        "slots": slot_count,
    }


def estimate_video_cost(
    slot_count: int,
    model: str = "kling-v2.1",
    duration: int = 5,
) -> dict:
    """Estimate cost for video batch."""
    per_slot = _estimate_single_video_cost(model, duration)
    return {
        "per_slot": per_slot,
        "total": round(per_slot * slot_count, 2),
        "model": model,
        "duration": duration,
        "slots": slot_count,
    }


def estimate_carousel_cost(
    slot_count: int,
    model: str = "claude-sonnet-4-6",
) -> dict:
    """Estimate cost for carousel batch (2 Claude calls per slot: select + caption)."""
    rates = {"claude-sonnet-4-6": (3.0, 15.0), "claude-haiku-4-5-20251001": (0.8, 4.0)}
    inp_rate, out_rate = rates.get(model, (3.0, 15.0))
    # Select: ~3000 input, ~800 output; Caption: ~1500 input, ~600 output
    select_cost = (3000 * inp_rate + 800 * out_rate) / 1_000_000
    caption_cost = (1500 * inp_rate + 600 * out_rate) / 1_000_000
    per_slot = select_cost + caption_cost
    return {
        "per_slot": round(per_slot, 4),
        "total": round(per_slot * slot_count, 4),
        "model": model,
        "slots": slot_count,
    }


def estimate_music_cost(
    slot_count: int,
    duration: int = 10,
) -> dict:
    """Estimate cost for music batch."""
    per_slot = duration * 0.002  # MusicGen rate
    return {
        "per_slot": round(per_slot, 4),
        "total": round(per_slot * slot_count, 4),
        "duration": duration,
        "slots": slot_count,
    }
