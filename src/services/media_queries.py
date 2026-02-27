"""
Media query helpers for Streamlit dashboard.
Wraps Supabase calls with Streamlit caching.
"""
import json
from typing import Optional

import streamlit as st

from src.database import get_supabase, TABLE_MEDIA_LIBRARY, TABLE_TAG_CORRECTIONS


@st.cache_data(ttl=60)
def fetch_all_media(media_type: Optional[str] = None) -> list[dict]:
    """Fetch all analyzed media rows. Cached 60s."""
    client = get_supabase()
    query = client.table(TABLE_MEDIA_LIBRARY).select("*").eq("status", "analyzed")
    if media_type:
        query = query.eq("media_type", media_type)
    result = query.order("file_name").execute()
    return result.data


@st.cache_data(ttl=60)
def fetch_media_by_id(media_id: str) -> Optional[dict]:
    """Fetch a single media row by UUID."""
    client = get_supabase()
    result = (
        client.table(TABLE_MEDIA_LIBRARY)
        .select("*")
        .eq("id", media_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def update_media_tags(media_id: str, updates: dict) -> bool:
    """Update media_library row and clear cache."""
    client = get_supabase()
    try:
        client.table(TABLE_MEDIA_LIBRARY).update(updates).eq("id", media_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Update failed: {e}")
        return False


def log_tag_correction(
    media_id: str, field_name: str, old_value: str, new_value: str
) -> None:
    """Log a manual tag correction."""
    client = get_supabase()
    client.table(TABLE_TAG_CORRECTIONS).insert(
        {
            "media_id": media_id,
            "field_name": field_name,
            "old_value": old_value,
            "new_value": new_value,
        }
    ).execute()


def delete_media(media_id: str) -> bool:
    """Delete a media row from the database and clear cache."""
    client = get_supabase()
    try:
        client.table(TABLE_MEDIA_LIBRARY).delete().eq("id", media_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Delete failed: {e}")
        return False


@st.cache_data(ttl=60)
def fetch_derivatives(parent_id: str) -> list[dict]:
    """Fetch all derivative media (children) of a given parent media ID."""
    client = get_supabase()
    result = (
        client.table(TABLE_MEDIA_LIBRARY)
        .select("*")
        .eq("parent_media_id", parent_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


@st.cache_data(ttl=300)
def fetch_distinct_values(field: str) -> list[str]:
    """Fetch distinct non-null values for a field. Cached 5 min."""
    all_media = fetch_all_media()
    values = set()
    for row in all_media:
        val = row.get(field)
        if val is None:
            continue
        if isinstance(val, list):
            values.update(val)
        elif isinstance(val, str) and val:
            values.add(val)
    return sorted(values)
