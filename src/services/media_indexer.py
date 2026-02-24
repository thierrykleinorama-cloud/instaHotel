"""
Media Indexer — orchestrates Drive → Vision → Supabase pipeline.
Handles both images and videos, with dedup, error handling, and rate limiting.
"""
import json
import time
import traceback
from datetime import datetime, timezone
from typing import Optional

from src.database import get_supabase, TABLE_MEDIA_LIBRARY
from src.services.google_drive import (
    list_media_files,
    download_file_bytes,
    classify_media_type,
)
from src.services.vision_analyzer import analyze_image, MODEL
from src.services.video_analyzer import analyze_video
from src.utils import encode_image_bytes, get_aspect_ratio


# Rate limiting
DELAY_BETWEEN_CALLS = 1.5  # seconds between Claude API calls
MAX_RETRIES = 3
RETRY_BASE_DELAY = 5  # seconds, exponential backoff


def get_indexed_file_ids() -> set[str]:
    """Fetch all drive_file_ids already in the database."""
    client = get_supabase()
    result = client.table(TABLE_MEDIA_LIBRARY).select("drive_file_id").execute()
    return {row["drive_file_id"] for row in result.data}


def get_error_file_ids() -> set[str]:
    """Fetch drive_file_ids with status='error' (for re-indexing)."""
    client = get_supabase()
    result = (
        client.table(TABLE_MEDIA_LIBRARY)
        .select("drive_file_id")
        .eq("status", "error")
        .execute()
    )
    return {row["drive_file_id"] for row in result.data}


def _upsert_media(data: dict):
    """Insert or update a media_library row."""
    client = get_supabase()
    client.table(TABLE_MEDIA_LIBRARY).upsert(
        data, on_conflict="drive_file_id"
    ).execute()


def _call_with_retry(fn, *args, **kwargs):
    """Call a function with exponential backoff on rate limit errors."""
    for attempt in range(MAX_RETRIES):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "rate" in error_str or "overloaded" in error_str:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                print(f"    Rate limited, retrying in {delay}s (attempt {attempt + 1}/{MAX_RETRIES})...")
                time.sleep(delay)
            else:
                raise
    # Final attempt without catch
    return fn(*args, **kwargs)


def process_image(file_info: dict, dry_run: bool = False) -> dict:
    """Process a single image: download, analyze, store."""
    file_id = file_info["id"]
    file_name = file_info["name"]
    mime_type = file_info.get("mimeType", "image/jpeg")
    file_size = int(file_info.get("size", 0))

    # Download
    image_bytes = download_file_bytes(file_id)

    # Encode + get aspect ratio
    image_b64 = encode_image_bytes(image_bytes, mime_type)
    aspect_ratio = get_aspect_ratio(image_bytes)

    if dry_run:
        return {
            "drive_file_id": file_id,
            "file_name": file_name,
            "status": "dry_run",
            "aspect_ratio": aspect_ratio,
        }

    # Analyze with Claude
    analysis = _call_with_retry(analyze_image, image_b64)
    raw_data = analysis.model_dump()

    # Build row
    row = {
        "drive_file_id": file_id,
        "file_name": file_name,
        "file_path": file_info.get("_path"),
        "mime_type": mime_type,
        "file_size_bytes": file_size,
        "media_type": "image",
        "category": analysis.category,
        "subcategory": analysis.subcategory,
        "ambiance": analysis.ambiance,
        "season": analysis.season,
        "elements": analysis.elements,
        "ig_quality": analysis.ig_quality,
        "aspect_ratio": aspect_ratio,
        "description_fr": analysis.description_fr,
        "description_en": analysis.description_en,
        "analysis_raw": raw_data,
        "analysis_model": MODEL,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "status": "analyzed",
    }

    _upsert_media(row)
    return row


def process_video(file_info: dict, dry_run: bool = False) -> dict:
    """Process a single video: download, detect scenes, analyze, store."""
    file_id = file_info["id"]
    file_name = file_info["name"]
    mime_type = file_info.get("mimeType", "video/mp4")
    file_size = int(file_info.get("size", 0))

    # Download
    video_bytes = download_file_bytes(file_id)

    if dry_run:
        return {
            "drive_file_id": file_id,
            "file_name": file_name,
            "status": "dry_run",
            "file_size_bytes": file_size,
        }

    # Full video analysis pipeline
    result = _call_with_retry(analyze_video, video_bytes, file_name)

    # Build row
    row = {
        "drive_file_id": file_id,
        "file_name": file_name,
        "file_path": file_info.get("_path"),
        "mime_type": mime_type,
        "file_size_bytes": file_size,
        "media_type": "video",
        "category": result.get("category"),
        "subcategory": result.get("subcategory"),
        "ambiance": result.get("ambiance", []),
        "season": result.get("season", []),
        "elements": result.get("elements", []),
        "ig_quality": result.get("ig_quality"),
        "aspect_ratio": result.get("aspect_ratio"),
        "description_fr": result.get("description_fr"),
        "description_en": result.get("description_en"),
        "duration_seconds": result.get("duration_seconds"),
        "scenes": result.get("scenes"),
        "analysis_raw": result.get("analysis_raw"),
        "analysis_model": result.get("analysis_model", MODEL),
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "status": "analyzed",
    }

    _upsert_media(row)
    return row


def run_indexer(
    folder_id: Optional[str] = None,
    limit: Optional[int] = None,
    dry_run: bool = False,
    reindex_errors: bool = False,
):
    """
    Main indexer loop: list files, skip already-indexed, process each.
    Yields progress dicts for each file processed.
    """
    print("Listing media files from Google Drive...")
    all_files = list_media_files(folder_id)
    print(f"Found {len(all_files)} media files")

    # Dedup
    indexed_ids = get_indexed_file_ids()
    if reindex_errors:
        error_ids = get_error_file_ids()
        to_process = [
            f for f in all_files
            if f["id"] not in indexed_ids or f["id"] in error_ids
        ]
        print(f"Reindexing {len(error_ids)} error files + {len(to_process) - len(error_ids)} new files")
    else:
        to_process = [f for f in all_files if f["id"] not in indexed_ids]

    print(f"Already indexed: {len(indexed_ids)}, to process: {len(to_process)}")

    if limit:
        to_process = to_process[:limit]
        print(f"Limited to {limit} files")

    total = len(to_process)
    stats = {"processed": 0, "errors": 0, "images": 0, "videos": 0}

    for i, file_info in enumerate(to_process, 1):
        file_name = file_info["name"]
        mime_type = file_info.get("mimeType", "")
        media_type = classify_media_type(mime_type)

        print(f"[{i}/{total}] {media_type}: {file_name}", end=" ", flush=True)

        try:
            if media_type == "image":
                result = process_image(file_info, dry_run=dry_run)
                stats["images"] += 1
            elif media_type == "video":
                result = process_video(file_info, dry_run=dry_run)
                stats["videos"] += 1
            else:
                print("SKIP (unsupported)")
                continue

            status = result.get("status", "?")
            quality = result.get("ig_quality", "?")
            category = result.get("category", "?")
            print(f"-> {status} | {category} | quality={quality}")
            stats["processed"] += 1

        except Exception as e:
            print(f"ERROR: {e}")
            stats["errors"] += 1
            # Save error to DB
            try:
                _upsert_media({
                    "drive_file_id": file_info["id"],
                    "file_name": file_name,
                    "file_path": file_info.get("_path"),
                    "mime_type": mime_type,
                    "file_size_bytes": int(file_info.get("size", 0)),
                    "media_type": media_type or "image",
                    "status": "error",
                    "error_message": f"{type(e).__name__}: {e}",
                })
            except Exception:
                pass

        # Rate limit between Claude calls
        if not dry_run and i < total:
            time.sleep(DELAY_BETWEEN_CALLS)

    print(f"\n{'=' * 50}")
    print(f"Indexing complete!")
    print(f"  Processed: {stats['processed']} ({stats['images']} images, {stats['videos']} videos)")
    print(f"  Errors: {stats['errors']}")
    print(f"  Total: {total}")
    return stats
