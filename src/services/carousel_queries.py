"""
CRUD helpers for the carousel_drafts table.
"""
from datetime import datetime, timezone
from typing import Optional

import streamlit as st

from src.database import get_supabase, TABLE_CAROUSEL_DRAFTS


def _clear_drafts_cache():
    """Clear the cached drafts list after mutations."""
    fetch_carousel_drafts.clear()


def save_carousel_draft(
    title: str,
    media_ids: list[str],
    caption_es: str = "",
    caption_en: str = "",
    caption_fr: str = "",
    hashtags: list[str] | None = None,
) -> Optional[str]:
    """Create a new carousel draft. Returns the new ID or None."""
    client = get_supabase()
    row = {
        "title": title,
        "media_ids": media_ids,
        "caption_es": caption_es,
        "caption_en": caption_en,
        "caption_fr": caption_fr,
        "hashtags": hashtags or [],
        "status": "draft",
    }
    try:
        result = client.table(TABLE_CAROUSEL_DRAFTS).insert(row).execute()
        _clear_drafts_cache()
        return result.data[0]["id"] if result.data else None
    except Exception as e:
        print(f"Carousel draft save failed: {e}")
        return None


@st.cache_data(ttl=120)
def fetch_carousel_drafts(
    status: str = "draft",
    limit: int = 50,
) -> list[dict]:
    """Fetch carousel drafts filtered by status. Use status='all' for everything."""
    client = get_supabase()
    query = (
        client.table(TABLE_CAROUSEL_DRAFTS)
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status and status != "all":
        query = query.eq("status", status)
    return query.execute().data


def update_carousel_status(
    carousel_id: str,
    status: str,
    ig_post_id: Optional[str] = None,
    ig_permalink: Optional[str] = None,
) -> bool:
    """Update status and optional publish info for a carousel draft."""
    client = get_supabase()
    try:
        updates = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if ig_post_id is not None:
            updates["ig_post_id"] = ig_post_id
        if ig_permalink is not None:
            updates["ig_permalink"] = ig_permalink
        if status == "published":
            updates["published_at"] = datetime.now(timezone.utc).isoformat()
        client.table(TABLE_CAROUSEL_DRAFTS).update(updates).eq("id", carousel_id).execute()
        _clear_drafts_cache()
        return True
    except Exception as e:
        print(f"Carousel status update failed: {e}")
        return False


def update_carousel_draft(
    carousel_id: str,
    title: str = None,
    media_ids: list[str] = None,
    caption_es: str = None,
    caption_en: str = None,
    caption_fr: str = None,
    hashtags: list[str] = None,
) -> bool:
    """Update fields on a carousel draft."""
    client = get_supabase()
    try:
        updates = {"updated_at": datetime.now(timezone.utc).isoformat()}
        if title is not None:
            updates["title"] = title
        if media_ids is not None:
            updates["media_ids"] = media_ids
        if caption_es is not None:
            updates["caption_es"] = caption_es
        if caption_en is not None:
            updates["caption_en"] = caption_en
        if caption_fr is not None:
            updates["caption_fr"] = caption_fr
        if hashtags is not None:
            updates["hashtags"] = hashtags
        client.table(TABLE_CAROUSEL_DRAFTS).update(updates).eq("id", carousel_id).execute()
        _clear_drafts_cache()
        return True
    except Exception as e:
        print(f"Carousel draft update failed: {e}")
        return False


def delete_carousel_draft(carousel_id: str) -> bool:
    """Delete a carousel draft."""
    client = get_supabase()
    try:
        client.table(TABLE_CAROUSEL_DRAFTS).delete().eq("id", carousel_id).execute()
        _clear_drafts_cache()
        return True
    except Exception as e:
        print(f"Carousel draft delete failed: {e}")
        return False
