"""
CRUD helpers for creative generation tables:
generated_scenarios, generated_music, creative_jobs feedback.
"""
from typing import Optional

from src.database import (
    get_supabase,
    TABLE_MEDIA_LIBRARY,
    TABLE_GENERATED_SCENARIOS,
    TABLE_GENERATED_MUSIC,
    TABLE_CREATIVE_JOBS,
    TABLE_GENERATED_CONTENT,
)


# -----------------------------------------------------------
# Generated Scenarios
# -----------------------------------------------------------

def insert_scenario(data: dict) -> Optional[str]:
    """Insert a generated scenario. Returns the new ID or None."""
    client = get_supabase()
    try:
        result = client.table(TABLE_GENERATED_SCENARIOS).insert(data).execute()
        return result.data[0]["id"] if result.data else None
    except Exception as e:
        print(f"Scenario insert failed: {e}")
        return None


def insert_scenarios_batch(scenarios: list[dict]) -> int:
    """Insert multiple scenarios at once. Returns count of inserted rows."""
    if not scenarios:
        return 0
    client = get_supabase()
    try:
        result = client.table(TABLE_GENERATED_SCENARIOS).insert(scenarios).execute()
        return len(result.data) if result.data else 0
    except Exception as e:
        print(f"Scenario batch insert failed: {e}")
        return 0


def fetch_scenarios_for_media(media_id: str) -> list[dict]:
    """Fetch all scenarios generated for a given source media, newest first."""
    client = get_supabase()
    result = (
        client.table(TABLE_GENERATED_SCENARIOS)
        .select("*")
        .eq("source_media_id", media_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


def update_scenario_feedback(scenario_id: str, status: str, feedback: str = None, rating: int = None) -> bool:
    """Accept or reject a scenario with optional feedback and rating."""
    client = get_supabase()
    try:
        updates = {"status": status}
        if feedback is not None:
            updates["feedback"] = feedback
        if rating is not None:
            updates["rating"] = rating
        client.table(TABLE_GENERATED_SCENARIOS).update(updates).eq("id", scenario_id).execute()
        return True
    except Exception as e:
        print(f"Scenario feedback update failed: {e}")
        return False


# -----------------------------------------------------------
# Generated Music
# -----------------------------------------------------------

def insert_music(data: dict) -> Optional[str]:
    """Insert a generated music track. Returns the new ID or None."""
    client = get_supabase()
    try:
        result = client.table(TABLE_GENERATED_MUSIC).insert(data).execute()
        return result.data[0]["id"] if result.data else None
    except Exception as e:
        print(f"Music insert failed: {e}")
        return None


def fetch_music_for_media(media_id: str) -> list[dict]:
    """Fetch all music generated for a given source media, newest first."""
    client = get_supabase()
    result = (
        client.table(TABLE_GENERATED_MUSIC)
        .select("*")
        .eq("source_media_id", media_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


def update_music_feedback(music_id: str, status: str, feedback: str = None, rating: int = None) -> bool:
    """Accept or reject a music track with optional feedback and rating."""
    client = get_supabase()
    try:
        updates = {"status": status}
        if feedback is not None:
            updates["feedback"] = feedback
        if rating is not None:
            updates["rating"] = rating
        client.table(TABLE_GENERATED_MUSIC).update(updates).eq("id", music_id).execute()
        return True
    except Exception as e:
        print(f"Music feedback update failed: {e}")
        return False


# -----------------------------------------------------------
# Creative Jobs (video) — feedback extension
# -----------------------------------------------------------

def update_job_feedback(job_id: str, status: str = None, feedback: str = None, rating: int = None) -> bool:
    """Add feedback/rating to a creative job (generated video)."""
    client = get_supabase()
    try:
        updates = {}
        if status is not None:
            updates["status"] = status
        if feedback is not None:
            updates["feedback"] = feedback
        if rating is not None:
            updates["rating"] = rating
        if not updates:
            return True
        client.table(TABLE_CREATIVE_JOBS).update(updates).eq("id", job_id).execute()
        return True
    except Exception as e:
        print(f"Job feedback update failed: {e}")
        return False


# -----------------------------------------------------------
# Generated Content (captions) — feedback extension
# -----------------------------------------------------------

def update_content_feedback(content_id: str, feedback: str = None, rating: int = None) -> bool:
    """Add feedback/rating to generated captions."""
    client = get_supabase()
    try:
        updates = {}
        if feedback is not None:
            updates["feedback"] = feedback
        if rating is not None:
            updates["rating"] = rating
        if not updates:
            return True
        client.table(TABLE_GENERATED_CONTENT).update(updates).eq("id", content_id).execute()
        return True
    except Exception as e:
        print(f"Content feedback update failed: {e}")
        return False


# -----------------------------------------------------------
# Feedback aggregation (for prompt improvement)
# -----------------------------------------------------------

# -----------------------------------------------------------
# Draft / review fetchers (for Drafts Review page)
# -----------------------------------------------------------

def fetch_draft_scenarios(status: str = "draft", limit: int = 100) -> list[dict]:
    """Fetch scenarios filtered by status. Default: drafts (unreviewed)."""
    client = get_supabase()
    query = (
        client.table(TABLE_GENERATED_SCENARIOS)
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status and status != "all":
        query = query.eq("status", status)
    return query.execute().data


def fetch_draft_music(status: str = "draft", limit: int = 100) -> list[dict]:
    """Fetch music tracks filtered by status. Default: drafts (unreviewed)."""
    client = get_supabase()
    query = (
        client.table(TABLE_GENERATED_MUSIC)
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status and status != "all":
        query = query.eq("status", status)
    return query.execute().data


def fetch_draft_videos(status: str = "unreviewed", limit: int = 100) -> list[dict]:
    """Fetch video jobs for review.

    Videos use 'completed' status (no 'draft'). 'unreviewed' = completed with no feedback.
    Also supports 'accepted', 'rejected', 'all'.
    """
    client = get_supabase()
    query = (
        client.table(TABLE_CREATIVE_JOBS)
        .select("*")
        .eq("job_type", "photo_to_video")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if status == "unreviewed":
        query = query.eq("status", "completed").is_("feedback", "null")
    elif status and status != "all":
        query = query.eq("status", status)
    return query.execute().data


def fetch_media_names(media_ids: list[str]) -> dict[str, str]:
    """Return {media_id: file_name} for a list of media IDs."""
    if not media_ids:
        return {}
    client = get_supabase()
    unique_ids = list(set(media_ids))
    result = (
        client.table(TABLE_MEDIA_LIBRARY)
        .select("id,file_name")
        .in_("id", unique_ids)
        .execute()
    )
    return {r["id"]: r["file_name"] for r in result.data}


def fetch_rejected_scenarios(limit: int = 50) -> list[dict]:
    """Fetch recently rejected scenarios with feedback, for prompt improvement."""
    client = get_supabase()
    result = (
        client.table(TABLE_GENERATED_SCENARIOS)
        .select("title,description,motion_prompt,mood,feedback,rating")
        .eq("status", "rejected")
        .not_.is_("feedback", "null")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


def fetch_rejected_jobs(limit: int = 50) -> list[dict]:
    """Fetch recently rejected video jobs with feedback."""
    client = get_supabase()
    result = (
        client.table(TABLE_CREATIVE_JOBS)
        .select("job_type,params,feedback,rating")
        .eq("status", "rejected")
        .not_.is_("feedback", "null")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data
