"""
Instagram Graph API publisher + Supabase Storage upload.
Handles container creation, polling, publishing, and scheduling.
"""
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GRAPH_API_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.instagram.com/{GRAPH_API_VERSION}"
SUPABASE_STORAGE_BUCKET = "media-publish"


def _get_secret(key: str) -> Optional[str]:
    """Get a secret from st.secrets (Streamlit Cloud) or os.environ (local)."""
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)


def _get_ig_token() -> str:
    token = _get_secret("INSTAGRAM_ACCESS_TOKEN")
    if not token:
        raise ValueError(
            "INSTAGRAM_ACCESS_TOKEN not found. Set it in .env or Streamlit secrets."
        )
    return token


def _get_ig_account_id() -> str:
    acct = _get_secret("INSTAGRAM_ACCOUNT_ID")
    if not acct:
        raise ValueError(
            "INSTAGRAM_ACCOUNT_ID not found. Set it in .env or Streamlit secrets."
        )
    return acct


# ---------------------------------------------------------------------------
# Supabase Storage
# ---------------------------------------------------------------------------

def _get_supabase_url() -> str:
    url = _get_secret("SUPABASE_URL")
    if not url:
        raise ValueError("SUPABASE_URL not set")
    return url.rstrip("/")


def _get_supabase_key() -> str:
    key = _get_secret("SUPABASE_KEY")
    if not key:
        raise ValueError("SUPABASE_KEY not set")
    return key


def upload_to_supabase_storage(
    file_bytes: bytes,
    filename: str,
    mime_type: str = "image/jpeg",
) -> str:
    """Upload a file to the public media-publish bucket. Returns the public URL."""
    base_url = _get_supabase_url()
    key = _get_supabase_key()

    # Unique filename to avoid collisions
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    unique_name = f"{uuid.uuid4().hex[:12]}_{filename}"

    upload_url = f"{base_url}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{unique_name}"

    resp = httpx.post(
        upload_url,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": mime_type,
            "x-upsert": "true",
        },
        content=file_bytes,
        timeout=120,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Supabase Storage upload failed ({resp.status_code}): {resp.text[:300]}"
        )

    public_url = f"{base_url}/storage/v1/object/public/{SUPABASE_STORAGE_BUCKET}/{unique_name}"
    return public_url


def delete_from_supabase_storage(filename: str) -> bool:
    """Delete a file from the media-publish bucket. Returns True on success."""
    base_url = _get_supabase_url()
    key = _get_supabase_key()

    delete_url = f"{base_url}/storage/v1/object/{SUPABASE_STORAGE_BUCKET}/{filename}"
    resp = httpx.delete(
        delete_url,
        headers={"Authorization": f"Bearer {key}"},
        timeout=30,
    )
    return resp.status_code in (200, 204)


# ---------------------------------------------------------------------------
# Instagram Graph API — Container lifecycle
# ---------------------------------------------------------------------------

def create_ig_container(
    account_id: str,
    token: str,
    media_url: str,
    caption: str,
    media_type: str = "IMAGE",
    scheduled_publish_time: Optional[int] = None,
) -> str:
    """
    Create an IG media container.
    media_type: "IMAGE" or "REELS"
    scheduled_publish_time: Unix timestamp for future scheduling (optional).
    Returns container_id.
    """
    url = f"{GRAPH_BASE}/{account_id}/media"

    data = {
        "caption": caption,
        "access_token": token,
    }

    if media_type == "REELS":
        data["media_type"] = "REELS"
        data["video_url"] = media_url
    else:
        data["image_url"] = media_url

    if scheduled_publish_time:
        data["published"] = "false"
        data["scheduled_publish_time"] = str(scheduled_publish_time)

    resp = httpx.post(url, data=data, timeout=60)
    if resp.status_code != 200:
        error = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:300]
        raise RuntimeError(f"IG container creation failed ({resp.status_code}): {error}")

    body = resp.json()
    container_id = body.get("id")
    if not container_id:
        raise RuntimeError(f"No container ID in response: {body}")
    return container_id


def poll_container_status(
    container_id: str,
    token: str,
    max_wait: int = 120,
    interval: int = 5,
) -> str:
    """
    Poll an IG container until status is FINISHED or ERROR.
    Returns the final status_code string.
    """
    url = f"{GRAPH_BASE}/{container_id}"
    params = {
        "fields": "status_code",
        "access_token": token,
    }

    elapsed = 0
    while elapsed < max_wait:
        resp = httpx.get(url, params=params, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        status = body.get("status_code", "IN_PROGRESS")

        if status == "FINISHED":
            return status
        if status == "ERROR":
            raise RuntimeError(f"IG container {container_id} failed: {body}")

        time.sleep(interval)
        elapsed += interval

    raise TimeoutError(
        f"IG container {container_id} not ready after {max_wait}s (last status: {status})"
    )


def publish_container(
    account_id: str,
    token: str,
    container_id: str,
) -> dict:
    """
    Publish a FINISHED container.
    Returns {"id": ig_post_id}.
    """
    url = f"{GRAPH_BASE}/{account_id}/media_publish"
    data = {
        "creation_id": container_id,
        "access_token": token,
    }

    resp = httpx.post(url, data=data, timeout=60)
    if resp.status_code != 200:
        error = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:300]
        raise RuntimeError(f"IG publish failed ({resp.status_code}): {error}")

    return resp.json()


def get_post_permalink(ig_post_id: str, token: str) -> Optional[str]:
    """Get the permalink of a published IG post. May return None for scheduled posts."""
    url = f"{GRAPH_BASE}/{ig_post_id}"
    params = {
        "fields": "permalink",
        "access_token": token,
    }
    try:
        resp = httpx.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("permalink")
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Carousel publishing
# ---------------------------------------------------------------------------

def create_carousel_child(
    account_id: str,
    token: str,
    media_url: str,
) -> str:
    """Create one carousel child container. Returns child_container_id."""
    url = f"{GRAPH_BASE}/{account_id}/media"
    data = {
        "image_url": media_url,
        "is_carousel_item": "true",
        "access_token": token,
    }
    resp = httpx.post(url, data=data, timeout=60)
    if resp.status_code != 200:
        error = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:300]
        raise RuntimeError(f"Carousel child creation failed ({resp.status_code}): {error}")
    body = resp.json()
    child_id = body.get("id")
    if not child_id:
        raise RuntimeError(f"No container ID for carousel child: {body}")
    return child_id


def create_carousel_container(
    account_id: str,
    token: str,
    children_ids: list[str],
    caption: str,
    scheduled_publish_time: Optional[int] = None,
) -> str:
    """Create a carousel parent container. Returns container_id."""
    url = f"{GRAPH_BASE}/{account_id}/media"
    data = {
        "media_type": "CAROUSEL",
        "children": ",".join(children_ids),
        "caption": caption,
        "access_token": token,
    }
    if scheduled_publish_time:
        data["published"] = "false"
        data["scheduled_publish_time"] = str(scheduled_publish_time)

    resp = httpx.post(url, data=data, timeout=60)
    if resp.status_code != 200:
        error = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:300]
        raise RuntimeError(f"Carousel container creation failed ({resp.status_code}): {error}")
    body = resp.json()
    container_id = body.get("id")
    if not container_id:
        raise RuntimeError(f"No container ID for carousel: {body}")
    return container_id


def publish_carousel(
    image_urls: list[str],
    caption: str,
    scheduled_publish_time: Optional[int] = None,
) -> dict:
    """Full carousel publish flow: children → carousel → poll → publish.

    Args:
        image_urls: list of public URLs for each carousel image (2-10).
        caption: the full caption text.
        scheduled_publish_time: optional Unix timestamp for scheduling.

    Returns: {success, ig_post_id, ig_permalink, status}
    """
    token = _get_ig_token()
    account_id = _get_ig_account_id()

    if len(image_urls) < 2:
        raise ValueError("Carousel requires at least 2 images")
    if len(image_urls) > 10:
        raise ValueError("Carousel supports at most 10 images")

    # Step 1: Create child containers
    children_ids = []
    for img_url in image_urls:
        child_id = create_carousel_child(account_id, token, img_url)
        children_ids.append(child_id)
        time.sleep(1)  # Brief pause between child creations

    # Step 2: Create carousel container
    container_id = create_carousel_container(
        account_id, token, children_ids, caption, scheduled_publish_time,
    )

    # Step 3: Poll until ready
    poll_container_status(container_id, token, max_wait=120)

    # Step 4: Publish
    publish_result = publish_container(account_id, token, container_id)
    ig_post_id = publish_result.get("id")

    # Step 5: Get permalink
    permalink = get_post_permalink(ig_post_id, token) if ig_post_id else None

    status = "scheduled" if scheduled_publish_time else "published"

    return {
        "success": True,
        "ig_post_id": ig_post_id,
        "ig_permalink": permalink,
        "status": status,
    }


# ---------------------------------------------------------------------------
# Caption resolution
# ---------------------------------------------------------------------------

def resolve_caption(
    content: dict,
    media_type: str,
    variant: str,
    language: str,
) -> str:
    """
    Build the final caption string from a generated_content row.
    variant: "short", "story", or "reel"
    language: "es", "en", or "fr"
    Appends hashtags as #tag1 #tag2 ...
    """
    # For video/reels, prefer reel variant
    if media_type == "video" and variant != "reel":
        variant = "reel"

    field = f"caption_{variant}_{language}"
    caption_text = content.get(field, "")

    if not caption_text:
        # Fallback: try short, then story, then reel
        for fallback in ["short", "story", "reel"]:
            fb_field = f"caption_{fallback}_{language}"
            caption_text = content.get(fb_field, "")
            if caption_text:
                break

    if not caption_text:
        raise ValueError(
            f"No caption found for {field} (or fallbacks) in content {content.get('id')}"
        )

    # Append hashtags
    hashtags = content.get("hashtags") or []
    if hashtags:
        tag_str = " ".join(f"#{h}" for h in hashtags)
        caption_text = f"{caption_text}\n\n{tag_str}"

    return caption_text


def resolve_multilingual_caption(
    content: dict,
    media_type: str,
    variant: str,
) -> str:
    """
    Build a multilingual stacked caption (ES + EN + FR) for a single post.
    """
    if media_type == "video" and variant != "reel":
        variant = "reel"

    parts = []
    for lang, flag in [("es", ""), ("en", "\U0001f1ec\U0001f1e7"), ("fr", "\U0001f1eb\U0001f1f7")]:
        field = f"caption_{variant}_{lang}"
        text = content.get(field, "")
        if text:
            if flag:
                parts.append(f"{flag}\n{text}")
            else:
                parts.append(text)

    if not parts:
        raise ValueError(f"No captions found for variant={variant} in content {content.get('id')}")

    caption_text = "\n\n".join(parts)

    hashtags = content.get("hashtags") or []
    if hashtags:
        tag_str = " ".join(f"#{h}" for h in hashtags)
        caption_text = f"{caption_text}\n\n{tag_str}"

    return caption_text


# ---------------------------------------------------------------------------
# Orchestrator: publish a single calendar slot
# ---------------------------------------------------------------------------

def publish_slot(
    entry: dict,
    content: dict,
    media: dict,
    variant: str = "short",
    language: str = "es",
    multilingual: bool = True,
    schedule: bool = True,
) -> dict:
    """
    Full publish flow for one calendar slot.

    1. Download media bytes from Drive
    2. Upload to Supabase Storage → public URL
    3. Resolve caption
    4. Compute scheduled_publish_time if future date
    5. Create IG container
    6. Poll until FINISHED
    7. Publish container
    8. Get permalink
    9. Update calendar entry
    10. Cleanup temp file from Storage
    11. Return result dict

    Returns: {success, ig_post_id, ig_permalink, status, scheduled_publish_time, error}
    """
    from src.services.google_drive import download_file_bytes
    from src.services.editorial_queries import update_calendar_publish_info, clear_publish_error

    token = _get_ig_token()
    account_id = _get_ig_account_id()

    drive_file_id = media.get("drive_file_id")
    if not drive_file_id:
        return {"success": False, "error": "No drive_file_id on media"}

    media_type_str = media.get("media_type", "image")
    is_video = media_type_str == "video"
    ig_media_type = "REELS" if is_video else "IMAGE"

    storage_filename = None

    try:
        # 1. Clear any previous publish error
        clear_publish_error(entry["id"])

        # 2. Download from Drive
        file_bytes = download_file_bytes(drive_file_id)

        # 3. Upload to Supabase Storage
        file_ext = "mp4" if is_video else "jpg"
        mime = "video/mp4" if is_video else "image/jpeg"
        fname = f"publish_{entry['id'][:8]}.{file_ext}"
        public_url = upload_to_supabase_storage(file_bytes, fname, mime)
        # Extract the unique filename for later cleanup
        storage_filename = public_url.split(f"{SUPABASE_STORAGE_BUCKET}/")[-1]

        # 4. Resolve caption
        if multilingual:
            caption = resolve_multilingual_caption(content, media_type_str, variant)
        else:
            caption = resolve_caption(content, media_type_str, variant, language)

        # 5. Compute scheduled_publish_time
        publish_ts = None
        post_date_str = entry.get("post_date")
        time_slot = entry.get("time_slot", "10:00")
        if schedule and post_date_str:
            try:
                naive_dt = datetime.strptime(f"{post_date_str} {time_slot}", "%Y-%m-%d %H:%M")
                # Assume Europe/Madrid timezone — use UTC+1 as a simple offset
                # (For production, use pytz or zoneinfo)
                publish_dt = naive_dt.replace(tzinfo=timezone.utc)  # treat as UTC for simplicity
                now = datetime.now(timezone.utc)
                if publish_dt > now:
                    # Must be at least 10 minutes in the future for IG
                    min_future = now.timestamp() + 600
                    publish_ts = max(int(publish_dt.timestamp()), int(min_future))
            except (ValueError, TypeError):
                pass  # Publish immediately if date parsing fails

        # 6. Create container
        container_id = create_ig_container(
            account_id=account_id,
            token=token,
            media_url=public_url,
            caption=caption,
            media_type=ig_media_type,
            scheduled_publish_time=publish_ts,
        )

        # 7. Poll until FINISHED
        poll_container_status(container_id, token, max_wait=180 if is_video else 60)

        # 8. Publish
        publish_result = publish_container(account_id, token, container_id)
        ig_post_id = publish_result.get("id")

        # 9. Get permalink (may be None for scheduled)
        permalink = get_post_permalink(ig_post_id, token) if ig_post_id else None

        # 10. Update calendar
        if publish_ts:
            new_status = "scheduled"
            published_at = None
            sched_time = datetime.fromtimestamp(publish_ts, tz=timezone.utc).isoformat()
        else:
            new_status = "published"
            published_at = datetime.now(timezone.utc).isoformat()
            sched_time = None

        update_calendar_publish_info(
            entry_id=entry["id"],
            status=new_status,
            ig_post_id=ig_post_id,
            ig_permalink=permalink,
            ig_container_id=container_id,
            scheduled_time=sched_time,
            published_at=published_at,
        )

        return {
            "success": True,
            "ig_post_id": ig_post_id,
            "ig_permalink": permalink,
            "status": new_status,
            "scheduled_publish_time": sched_time,
        }

    except Exception as e:
        # Store error on the calendar entry
        from src.services.editorial_queries import update_calendar_publish_error
        try:
            update_calendar_publish_error(entry["id"], str(e))
        except Exception:
            pass
        return {"success": False, "error": str(e)}

    finally:
        # 11. Cleanup temp file from Storage
        if storage_filename:
            try:
                delete_from_supabase_storage(storage_filename)
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Publish from V2 posts table
# ---------------------------------------------------------------------------

def _resolve_post_caption(
    post: dict,
    multilingual: bool = True,
    variant: str = "short",
    language: str = "es",
) -> str:
    """Build caption string from a posts row (captions stored directly on row)."""
    if multilingual:
        parts = []
        for lang, flag in [("es", ""), ("en", "\U0001f1ec\U0001f1e7"), ("fr", "\U0001f1eb\U0001f1f7")]:
            text = post.get(f"caption_{lang}", "")
            if text:
                parts.append(f"{flag}\n{text}" if flag else text)
        if not parts:
            raise ValueError(f"No captions on post {post.get('id')}")
        caption_text = "\n\n".join(parts)
    else:
        caption_text = post.get(f"caption_{language}", "")
        if not caption_text:
            # Fallback to ES
            caption_text = post.get("caption_es", "")
        if not caption_text:
            raise ValueError(f"No caption_{language} on post {post.get('id')}")

    hashtags = post.get("hashtags") or []
    if hashtags:
        tag_str = " ".join(f"#{h}" for h in hashtags)
        caption_text = f"{caption_text}\n\n{tag_str}"
    return caption_text


def publish_post(
    post: dict,
    multilingual: bool = True,
    variant: str = "short",
    language: str = "es",
) -> dict:
    """
    Publish a single post from the V2 posts table to Instagram.

    Handles feed images, reels (video), and carousels.
    Updates the posts table on success/failure.

    Returns: {success, ig_post_id, ig_permalink, error}
    """
    from src.services.posts_queries import (
        update_post_publish_info,
        update_post_publish_error,
    )
    from src.services.google_drive import download_file_bytes

    token = _get_ig_token()
    account_id = _get_ig_account_id()
    post_id = post["id"]
    post_type = post["post_type"]
    storage_filenames = []

    try:
        caption = _resolve_post_caption(post, multilingual, variant, language)

        # --- Carousel ---
        if post_type == "carousel":
            return _publish_carousel_post(post, caption, storage_filenames)

        # --- Reel (any model) ---
        if post_type.startswith("reel"):
            return _publish_reel_post(post, caption, storage_filenames)

        # --- Feed (image post) ---
        media = _fetch_post_media(post)
        drive_file_id = media.get("drive_file_id")
        if not drive_file_id:
            raise ValueError("Source media has no drive_file_id")

        file_bytes = download_file_bytes(drive_file_id)
        fname = f"publish_{post_id[:8]}.jpg"
        public_url = upload_to_supabase_storage(file_bytes, fname, "image/jpeg")
        storage_filenames.append(public_url.split(f"{SUPABASE_STORAGE_BUCKET}/")[-1])

        container_id = create_ig_container(
            account_id, token, public_url, caption, media_type="IMAGE",
        )
        poll_container_status(container_id, token, max_wait=60)
        result = publish_container(account_id, token, container_id)
        ig_post_id = result.get("id")
        permalink = get_post_permalink(ig_post_id, token) if ig_post_id else None

        update_post_publish_info(post_id, ig_post_id, permalink)
        return {"success": True, "ig_post_id": ig_post_id, "ig_permalink": permalink}

    except Exception as e:
        update_post_publish_error(post_id, str(e))
        return {"success": False, "error": str(e)}

    finally:
        for sf in storage_filenames:
            try:
                delete_from_supabase_storage(sf)
            except Exception:
                pass


def _fetch_post_media(post: dict) -> dict:
    """Fetch media_library row for a post's media_id."""
    from src.database import get_supabase, TABLE_MEDIA_LIBRARY
    media_id = post.get("media_id")
    if not media_id:
        raise ValueError("Post has no media_id")
    result = (
        get_supabase()
        .table(TABLE_MEDIA_LIBRARY)
        .select("*")
        .eq("id", media_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise ValueError(f"Media {media_id} not found")
    return result.data[0]


def _publish_reel_post(post: dict, caption: str, storage_filenames: list) -> dict:
    """Publish a reel post — fetch video from creative_jobs or composite."""
    from src.services.posts_queries import (
        update_post_publish_info,
        update_post_publish_error,
    )
    from src.services.google_drive import download_file_bytes

    token = _get_ig_token()
    account_id = _get_ig_account_id()
    post_id = post["id"]

    # Find the video URL: prefer composite (video+music), fallback to raw video
    video_url = _get_reel_video_url(post)
    if not video_url:
        raise ValueError("No video found for reel post (no video_job_id or result_url)")

    # Download video bytes (from Drive URL or direct URL)
    if "drive.google.com" in video_url or len(video_url) < 60:
        # It's a Drive file ID
        file_bytes = download_file_bytes(video_url)
    else:
        # It's a direct URL (e.g., Replicate output)
        import httpx as _httpx
        resp = _httpx.get(video_url, timeout=120, follow_redirects=True)
        resp.raise_for_status()
        file_bytes = resp.content

    fname = f"publish_{post_id[:8]}.mp4"
    public_url = upload_to_supabase_storage(file_bytes, fname, "video/mp4")
    storage_filenames.append(public_url.split(f"{SUPABASE_STORAGE_BUCKET}/")[-1])

    container_id = create_ig_container(
        account_id, token, public_url, caption, media_type="REELS",
    )
    poll_container_status(container_id, token, max_wait=180)
    result = publish_container(account_id, token, container_id)
    ig_post_id = result.get("id")
    permalink = get_post_permalink(ig_post_id, token) if ig_post_id else None

    update_post_publish_info(post_id, ig_post_id, permalink)
    return {"success": True, "ig_post_id": ig_post_id, "ig_permalink": permalink}


def _get_reel_video_url(post: dict) -> Optional[str]:
    """Get the publishable video URL for a reel post.
    For Kling/slideshow: use composite (video+music) drive_file_id.
    For Veo: use raw video result_url (has native audio).
    """
    from src.database import get_supabase, TABLE_CREATIVE_JOBS

    video_job_id = post.get("video_job_id")
    if not video_job_id:
        return None

    result = (
        get_supabase()
        .table(TABLE_CREATIVE_JOBS)
        .select("result_url, drive_file_id, job_type")
        .eq("id", video_job_id)
        .limit(1)
        .execute()
    )
    if not result.data:
        return None

    job = result.data[0]
    # Prefer drive_file_id (uploaded to Drive), fallback to result_url
    return job.get("drive_file_id") or job.get("result_url")


def _publish_carousel_post(post: dict, caption: str, storage_filenames: list) -> dict:
    """Publish a carousel post — fetch images from carousel_drafts."""
    from src.services.posts_queries import (
        update_post_publish_info,
        update_post_publish_error,
    )
    from src.services.google_drive import download_file_bytes
    from src.database import get_supabase, TABLE_CAROUSEL_DRAFTS, TABLE_MEDIA_LIBRARY

    post_id = post["id"]
    carousel_draft_id = post.get("carousel_draft_id")
    if not carousel_draft_id:
        raise ValueError("Carousel post has no carousel_draft_id")

    # Fetch the carousel draft to get media_ids
    draft = (
        get_supabase()
        .table(TABLE_CAROUSEL_DRAFTS)
        .select("media_ids")
        .eq("id", carousel_draft_id)
        .limit(1)
        .execute()
    )
    if not draft.data:
        raise ValueError(f"Carousel draft {carousel_draft_id} not found")

    media_ids = draft.data[0].get("media_ids", [])
    if len(media_ids) < 2:
        raise ValueError("Carousel needs at least 2 images")

    # Fetch media records to get drive_file_ids
    media_records = (
        get_supabase()
        .table(TABLE_MEDIA_LIBRARY)
        .select("id, drive_file_id")
        .in_("id", media_ids)
        .execute()
    ).data
    drive_map = {m["id"]: m["drive_file_id"] for m in media_records}

    # Download and upload each image to get public URLs
    image_urls = []
    for mid in media_ids:
        dfid = drive_map.get(mid)
        if not dfid:
            continue
        img_bytes = download_file_bytes(dfid)
        fname = f"carousel_{post_id[:8]}_{len(image_urls)}.jpg"
        pub_url = upload_to_supabase_storage(img_bytes, fname, "image/jpeg")
        storage_filenames.append(pub_url.split(f"{SUPABASE_STORAGE_BUCKET}/")[-1])
        image_urls.append(pub_url)

    if len(image_urls) < 2:
        raise ValueError("Could not resolve enough carousel images")

    result = publish_carousel(image_urls, caption)

    if result.get("success"):
        update_post_publish_info(
            post_id, result.get("ig_post_id"), result.get("ig_permalink"),
        )
    else:
        update_post_publish_error(post_id, result.get("error", "Unknown carousel error"))

    return result


# ---------------------------------------------------------------------------
# Batch publish (legacy calendar-based)
# ---------------------------------------------------------------------------

def batch_publish_validated(
    entries: list[dict],
    content_map: dict,
    media_map: dict,
    variant: str = "short",
    language: str = "es",
    multilingual: bool = True,
) -> list[dict]:
    """
    Publish/schedule all validated slots.
    entries: list of calendar entries with status=="validated"
    content_map: {calendar_id: content_dict}
    media_map: {media_id: media_dict}
    Returns list of result dicts per slot.
    """
    results = []
    for entry in entries:
        content = content_map.get(entry["id"])
        if not content:
            results.append({"entry_id": entry["id"], "success": False, "error": "No content"})
            continue

        media_id = entry.get("manual_media_id") or entry.get("media_id")
        media = media_map.get(media_id) if media_id else None
        if not media:
            results.append({"entry_id": entry["id"], "success": False, "error": "No media"})
            continue

        result = publish_slot(
            entry=entry,
            content=content,
            media=media,
            variant=variant,
            language=language,
            multilingual=multilingual,
        )
        result["entry_id"] = entry["id"]
        result["post_date"] = entry.get("post_date")
        results.append(result)

        # Brief pause between publishes to respect rate limits
        time.sleep(2)

    return results


# ---------------------------------------------------------------------------
# Token refresh (for future use)
# ---------------------------------------------------------------------------

def refresh_token(current_token: str) -> dict:
    """
    Refresh a long-lived IG token (valid for 60 more days from refresh).
    Returns {access_token, token_type, expires_in}.
    """
    url = f"{GRAPH_BASE}/oauth/access_token"
    params = {
        "grant_type": "ig_refresh_token",
        "access_token": current_token,
    }
    resp = httpx.get(url, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()
