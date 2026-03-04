"""
Batch Creative Pipeline — orchestrate scenario/video/music/composite generation
for all calendar slots in a date range.

Each pass is independent and idempotent. Slots already processed are skipped.
Review gates (accept/reject) happen between passes via Drafts Review page.
"""
import base64
import io
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
)
from src.services.editorial_queries import update_calendar_creative_status
from src.services.creative_transform import (
    generate_scenarios,
    photo_to_video,
    VIDEO_MODELS,
    estimate_video_cost as _estimate_single_video_cost,
)
from src.services.music_generator import generate_music
from src.services.video_composer import composite_video_audio
from src.prompts.music_generation import build_music_prompt
from src.utils import encode_image_bytes


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


# ---------------------------------------------------------------------------
# Pass 1: Scenarios (Claude, ~5-10s per slot)
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

        # Skip if already has scenarios
        if cal_id in existing and len(existing[cal_id]) > 0:
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

            update_calendar_creative_status(cal_id, "scenarios_generated")
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
# Pass 2: Videos (Kling/Veo, 1-5 min per slot)
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
    Skips slots without accepted scenarios or already with videos.

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
        if progress_callback:
            progress_callback(i, total, f"Slot {i+1}/{total}: generating video...")

        # Skip if already has a video
        if cal_id in existing_videos and len(existing_videos[cal_id]) > 0:
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
                duration=duration,
                aspect_ratio=aspect_ratio,
                model=video_model,
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

            provider = VIDEO_MODELS[video_model].get("provider", "replicate")
            save_video_job(
                source_media_id=media["id"],
                video_url=video_url,
                prompt=motion_prompt,
                cost_usd=cost,
                provider=provider,
                params={"duration": duration, "aspect_ratio": aspect_ratio, "model": video_model, "batch": True},
                drive_file_id=drive_fid,
                calendar_id=cal_id,
            )

            update_calendar_creative_status(cal_id, "video_generated")
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
# Pass 3: Music (MusicGen, 1-2 min per slot)
# ---------------------------------------------------------------------------

def batch_generate_music(
    slots: list[dict],
    music_duration: int = 10,
    progress_callback: ProgressCallback = None,
) -> dict:
    """Generate music for calendar slots with accepted videos.

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

        # Skip if already has music
        if cal_id in existing_music and len(existing_music[cal_id]) > 0:
            skipped += 1
            continue

        try:
            # Check for accepted video
            video = fetch_accepted_video_for_calendar(cal_id)
            if not video:
                skipped += 1  # no accepted video — skip
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

            update_calendar_creative_status(cal_id, "music_generated")
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
# Pass 4: Composite (FFmpeg, ~30s per slot, free)
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

        # Skip if already has a composite
        if cal_id in existing_composites and len(existing_composites[cal_id]) > 0:
            skipped += 1
            continue

        try:
            # Need accepted video + accepted music
            video = fetch_accepted_video_for_calendar(cal_id)
            music = fetch_music_for_calendar(cal_id)

            if not video or not music:
                skipped += 1
                continue

            # Download video bytes
            video_url = video.get("result_url", "")
            if not video_url:
                errors.append(f"Slot {slot.get('post_date')}: no video URL")
                failed += 1
                continue

            resp = httpx.get(video_url, timeout=120, follow_redirects=True)
            resp.raise_for_status()
            video_bytes = resp.content

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
            import json
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

            update_calendar_creative_status(cal_id, "complete")
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
