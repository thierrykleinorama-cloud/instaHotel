"""
Posts query helpers — CRUD for the V2 posts table.
Central entity for Generate -> Review -> Publish flow.
"""
from datetime import datetime
from typing import Optional

import streamlit as st

from src.database import get_supabase, TABLE_POSTS


# -----------------------------------------------------------
# Create
# -----------------------------------------------------------

def create_post(data: dict) -> str:
    """Insert a new post, return its UUID."""
    client = get_supabase()
    result = client.table(TABLE_POSTS).insert(data).execute()
    return result.data[0]["id"]


def create_posts_batch(posts: list[dict]) -> list[str]:
    """Bulk insert posts, return list of UUIDs."""
    if not posts:
        return []
    client = get_supabase()
    result = client.table(TABLE_POSTS).insert(posts).execute()
    return [row["id"] for row in result.data]


# -----------------------------------------------------------
# Read
# -----------------------------------------------------------

def fetch_posts(
    status: Optional[str] = None,
    post_type: Optional[str] = None,
    batch_id: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """Fetch posts with optional filters, newest first."""
    client = get_supabase()
    query = client.table(TABLE_POSTS).select("*")
    if status:
        query = query.eq("status", status)
    if post_type:
        query = query.eq("post_type", post_type)
    if batch_id:
        query = query.eq("batch_id", batch_id)
    query = query.order("created_at", desc=True).limit(limit)
    return query.execute().data


def fetch_posts_multi_status(statuses: list[str], limit: int = 50) -> list[dict]:
    """Fetch posts matching any of the given statuses."""
    if not statuses:
        return []
    client = get_supabase()
    query = (
        client.table(TABLE_POSTS)
        .select("*")
        .in_("status", statuses)
        .order("created_at", desc=True)
        .limit(limit)
    )
    return query.execute().data


def fetch_post(post_id: str) -> Optional[dict]:
    """Fetch a single post by ID."""
    client = get_supabase()
    result = (
        client.table(TABLE_POSTS)
        .select("*")
        .eq("id", post_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


# -----------------------------------------------------------
# Update
# -----------------------------------------------------------

def update_post(post_id: str, updates: dict) -> bool:
    """Generic update — pass any columns to change."""
    client = get_supabase()
    try:
        client.table(TABLE_POSTS).update(updates).eq("id", post_id).execute()
        return True
    except Exception as e:
        st.error(f"Post update failed: {e}")
        return False


def update_post_status(
    post_id: str, status: str, feedback: Optional[str] = None
) -> bool:
    """Update post workflow status. For 'discarded', saves feedback."""
    updates = {"status": status}
    if status == "discarded" and feedback:
        updates["discard_feedback"] = feedback
    if status == "failed":
        pass  # publish_error set separately
    return update_post(post_id, updates)


def update_post_publish_info(
    post_id: str,
    ig_post_id: str,
    ig_permalink: str,
    published_at: Optional[datetime] = None,
) -> bool:
    """Update post after successful IG publish."""
    updates = {
        "status": "published",
        "ig_post_id": ig_post_id,
        "ig_permalink": ig_permalink,
        "published_at": (published_at or datetime.utcnow()).isoformat(),
        "publish_error": None,
    }
    return update_post(post_id, updates)


def update_post_publish_error(post_id: str, error: str) -> bool:
    """Update post after failed IG publish."""
    return update_post(post_id, {"status": "failed", "publish_error": error})


# -----------------------------------------------------------
# Delete
# -----------------------------------------------------------

def delete_post(post_id: str) -> bool:
    """Permanently delete a post."""
    client = get_supabase()
    try:
        client.table(TABLE_POSTS).delete().eq("id", post_id).execute()
        return True
    except Exception as e:
        st.error(f"Post delete failed: {e}")
        return False
