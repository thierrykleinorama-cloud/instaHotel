"""
Editorial query helpers for Streamlit dashboard.
CRUD for editorial_rules, seasonal_themes, editorial_calendar.
"""
from datetime import date, timedelta
from typing import Optional

import streamlit as st

from src.database import (
    get_supabase,
    TABLE_EDITORIAL_RULES,
    TABLE_SEASONAL_THEMES,
    TABLE_EDITORIAL_CALENDAR,
    TABLE_MEDIA_LIBRARY,
)


# -----------------------------------------------------------
# Editorial Rules
# -----------------------------------------------------------

@st.cache_data(ttl=120)
def fetch_all_rules() -> list[dict]:
    """Fetch all editorial rules ordered by day + slot."""
    client = get_supabase()
    result = (
        client.table(TABLE_EDITORIAL_RULES)
        .select("*")
        .order("day_of_week")
        .order("slot_index")
        .execute()
    )
    return result.data


@st.cache_data(ttl=120)
def fetch_rules_for_day(day_of_week: int) -> list[dict]:
    """Fetch active rules for a specific day (1=Mon..7=Sun)."""
    client = get_supabase()
    result = (
        client.table(TABLE_EDITORIAL_RULES)
        .select("*")
        .eq("day_of_week", day_of_week)
        .eq("is_active", True)
        .order("slot_index")
        .execute()
    )
    return result.data


def upsert_rule(rule_data: dict) -> bool:
    """Upsert an editorial rule. rule_data must include day_of_week + slot_index."""
    client = get_supabase()
    try:
        client.table(TABLE_EDITORIAL_RULES).upsert(
            rule_data, on_conflict="day_of_week,slot_index"
        ).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Rule upsert failed: {e}")
        return False


def delete_rule(rule_id: str) -> bool:
    """Delete a rule by ID."""
    client = get_supabase()
    try:
        client.table(TABLE_EDITORIAL_RULES).delete().eq("id", rule_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Rule delete failed: {e}")
        return False


# -----------------------------------------------------------
# Seasonal Themes
# -----------------------------------------------------------

@st.cache_data(ttl=120)
def fetch_all_themes() -> list[dict]:
    """Fetch all seasonal themes ordered by start_date."""
    client = get_supabase()
    result = (
        client.table(TABLE_SEASONAL_THEMES)
        .select("*")
        .order("start_date")
        .execute()
    )
    return result.data


def fetch_active_theme_for_date(target_date: date) -> Optional[dict]:
    """Get the highest-priority active theme covering target_date."""
    client = get_supabase()
    iso = target_date.isoformat()
    result = (
        client.table(TABLE_SEASONAL_THEMES)
        .select("*")
        .eq("is_active", True)
        .lte("start_date", iso)
        .gte("end_date", iso)
        .order("priority", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def upsert_theme(theme_data: dict) -> bool:
    """Insert or update a seasonal theme. Include 'id' key for update."""
    client = get_supabase()
    try:
        if theme_data.get("id"):
            client.table(TABLE_SEASONAL_THEMES).update(theme_data).eq("id", theme_data["id"]).execute()
        else:
            theme_data.pop("id", None)
            client.table(TABLE_SEASONAL_THEMES).insert(theme_data).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Theme upsert failed: {e}")
        return False


def delete_theme(theme_id: str) -> bool:
    """Delete a seasonal theme by ID."""
    client = get_supabase()
    try:
        client.table(TABLE_SEASONAL_THEMES).delete().eq("id", theme_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Theme delete failed: {e}")
        return False


# -----------------------------------------------------------
# Editorial Calendar
# -----------------------------------------------------------

@st.cache_data(ttl=30)
def fetch_calendar_range(start: date, end: date) -> list[dict]:
    """Fetch calendar entries for a date range, ordered by date + slot."""
    client = get_supabase()
    result = (
        client.table(TABLE_EDITORIAL_CALENDAR)
        .select("*")
        .gte("post_date", start.isoformat())
        .lte("post_date", end.isoformat())
        .order("post_date")
        .order("slot_index")
        .execute()
    )
    return result.data


def upsert_calendar_entry(entry: dict) -> bool:
    """Upsert a calendar entry. Uses post_date + slot_index as conflict key."""
    client = get_supabase()
    try:
        client.table(TABLE_EDITORIAL_CALENDAR).upsert(
            entry, on_conflict="post_date,slot_index"
        ).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Calendar upsert failed: {e}")
        return False


def bulk_upsert_calendar(entries: list[dict]) -> bool:
    """Upsert many calendar entries at once."""
    client = get_supabase()
    try:
        client.table(TABLE_EDITORIAL_CALENDAR).upsert(
            entries, on_conflict="post_date,slot_index"
        ).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Calendar bulk upsert failed: {e}")
        return False


def update_calendar_status(entry_id: str, status: str) -> bool:
    """Update status of a calendar entry."""
    client = get_supabase()
    try:
        client.table(TABLE_EDITORIAL_CALENDAR).update(
            {"status": status}
        ).eq("id", entry_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Status update failed: {e}")
        return False


def update_calendar_media(entry_id: str, media_id: str, score: float, breakdown: dict) -> bool:
    """Swap the assigned media on a calendar entry (manual override)."""
    client = get_supabase()
    try:
        client.table(TABLE_EDITORIAL_CALENDAR).update({
            "manual_media_id": media_id,
            "media_score": score,
            "score_breakdown": breakdown,
        }).eq("id", entry_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Media swap failed: {e}")
        return False


def delete_calendar_range(start: date, end: date) -> bool:
    """Delete all calendar entries in a date range."""
    client = get_supabase()
    try:
        client.table(TABLE_EDITORIAL_CALENDAR).delete().gte(
            "post_date", start.isoformat()
        ).lte("post_date", end.isoformat()).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Calendar delete failed: {e}")
        return False


# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------

def update_calendar_publish_info(
    entry_id: str,
    status: str,
    ig_post_id: str = None,
    ig_permalink: str = None,
    ig_container_id: str = None,
    scheduled_time: str = None,
    published_at: str = None,
) -> bool:
    """Set publishing metadata after successful IG API call."""
    client = get_supabase()
    try:
        updates = {"status": status}
        if ig_post_id is not None:
            updates["ig_post_id"] = ig_post_id
        if ig_permalink is not None:
            updates["ig_permalink"] = ig_permalink
        if ig_container_id is not None:
            updates["ig_container_id"] = ig_container_id
        if scheduled_time is not None:
            updates["scheduled_publish_time"] = scheduled_time
        if published_at is not None:
            updates["published_at"] = published_at
        # Clear any previous error on success
        updates["publish_error"] = None
        client.table(TABLE_EDITORIAL_CALENDAR).update(updates).eq("id", entry_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Publish info update failed: {e}")
        return False


def update_calendar_publish_error(entry_id: str, error: str) -> bool:
    """Store a publish error on a calendar entry."""
    client = get_supabase()
    try:
        client.table(TABLE_EDITORIAL_CALENDAR).update(
            {"publish_error": error}
        ).eq("id", entry_id).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Publish error update failed: {e}")
        return False


def clear_publish_error(entry_id: str) -> bool:
    """Clear publish_error when retrying."""
    client = get_supabase()
    try:
        client.table(TABLE_EDITORIAL_CALENDAR).update(
            {"publish_error": None}
        ).eq("id", entry_id).execute()
        return True
    except Exception:
        return False


def fetch_recent_media_ids(lookback_days: int = 7) -> set[str]:
    """Get media IDs used in the calendar within the last N days."""
    client = get_supabase()
    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
    result = (
        client.table(TABLE_EDITORIAL_CALENDAR)
        .select("media_id")
        .gte("post_date", cutoff)
        .not_.is_("media_id", "null")
        .execute()
    )
    return {row["media_id"] for row in result.data if row.get("media_id")}
