"""
CRUD helpers for the generated_content table.
Manages AI-generated captions linked to editorial calendar slots.
"""
from typing import Optional

import streamlit as st

from src.database import (
    get_supabase,
    TABLE_GENERATED_CONTENT,
    TABLE_EDITORIAL_CALENDAR,
)


# -----------------------------------------------------------
# Fetch
# -----------------------------------------------------------

def fetch_content_for_calendar(calendar_id: str) -> Optional[dict]:
    """Get the latest content for a calendar slot."""
    client = get_supabase()
    try:
        result = (
            client.table(TABLE_GENERATED_CONTENT)
            .select("*")
            .eq("calendar_id", calendar_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception:
        return None


def fetch_content_for_calendar_range(calendar_ids: list[str]) -> dict[str, dict]:
    """Batch fetch latest content for multiple calendar slots.
    Returns {calendar_id: content_dict}.
    """
    if not calendar_ids:
        return {}
    client = get_supabase()
    try:
        result = (
            client.table(TABLE_GENERATED_CONTENT)
            .select("*")
            .in_("calendar_id", calendar_ids)
            .order("created_at", desc=True)
            .execute()
        )
    except Exception:
        # Table doesn't exist yet (pre-migration)
        return {}

    # Keep only latest per calendar_id
    by_cal: dict[str, dict] = {}
    for row in result.data:
        cal_id = row["calendar_id"]
        if cal_id not in by_cal:
            by_cal[cal_id] = row
    return by_cal


# -----------------------------------------------------------
# Insert / Link
# -----------------------------------------------------------

def insert_content(data: dict) -> Optional[str]:
    """Insert a new generated_content row. Returns the new ID or None on error."""
    client = get_supabase()
    try:
        result = client.table(TABLE_GENERATED_CONTENT).insert(data).execute()
        if result.data:
            st.cache_data.clear()
            return result.data[0]["id"]
        return None
    except Exception as e:
        st.error(f"Content insert failed: {e}")
        return None


def link_content_to_calendar(calendar_id: str, content_id: str) -> bool:
    """Set the content_id FK on a calendar entry and update status to content_ready."""
    client = get_supabase()
    try:
        client.table(TABLE_EDITORIAL_CALENDAR).update({
            "content_id": content_id,
            "status": "content_ready",
        }).eq("id", calendar_id).execute()
        st.cache_data.clear()
        return True
    except Exception:
        # content_id column may not exist yet (pre-migration) — just update status
        try:
            client.table(TABLE_EDITORIAL_CALENDAR).update({
                "status": "generated",
            }).eq("id", calendar_id).execute()
            st.cache_data.clear()
            return True
        except Exception as e:
            st.error(f"Content link failed: {e}")
            return False


# -----------------------------------------------------------
# Update
# -----------------------------------------------------------

def update_content(content_id: str, updates: dict) -> bool:
    """Update fields on a generated_content row."""
    client = get_supabase()
    try:
        client.table(TABLE_GENERATED_CONTENT).update(updates).eq("id", content_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Content update failed: {e}")
        return False


def update_content_status(content_id: str, status: str) -> bool:
    """Update content_status (draft/edited/approved)."""
    return update_content(content_id, {"content_status": status})
