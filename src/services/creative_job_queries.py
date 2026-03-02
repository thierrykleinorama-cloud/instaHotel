"""
Creative job CRUD — persist scenario/video/music generation results for crash recovery.
Also saves individual items to generated_scenarios / generated_music tables.
"""
import json
from typing import Optional

from src.database import get_supabase, TABLE_CREATIVE_JOBS, TABLE_GENERATED_SCENARIOS, TABLE_GENERATED_MUSIC


def save_scenario_job(
    source_media_id: str,
    scenarios: list[dict],
    cost_usd: float = 0,
    params: dict | None = None,
    model: str = "claude-sonnet-4-6",
) -> dict:
    """Persist scenario generation results. Returns the created creative_jobs row.
    Also saves individual scenarios to generated_scenarios table."""
    client = get_supabase()
    row = {
        "source_media_id": source_media_id,
        "job_type": "scenario_generation",
        "provider": "anthropic",
        "status": "completed",
        "params": json.dumps(params or {}),
        "cost_usd": cost_usd,
        "result_url": json.dumps(scenarios),  # store scenario JSON in result_url
    }
    result = client.table(TABLE_CREATIVE_JOBS).insert(row).execute()

    # Also save individual scenarios to generated_scenarios
    per_cost = cost_usd / max(len(scenarios), 1)
    scenario_rows = []
    for s in scenarios:
        scenario_rows.append({
            "source_media_id": source_media_id,
            "title": s.get("title", ""),
            "description": s.get("description", ""),
            "motion_prompt": s.get("motion_prompt", ""),
            "mood": s.get("mood", ""),
            "caption_hook": s.get("caption_hook", ""),
            "generation_params": params or {},
            "model": model,
            "cost_usd": per_cost,
        })
    if scenario_rows:
        try:
            client.table(TABLE_GENERATED_SCENARIOS).insert(scenario_rows).execute()
        except Exception:
            pass  # Don't fail the main save if individual inserts fail

    return result.data[0] if result.data else {}


def save_video_job(
    source_media_id: str,
    video_url: str,
    prompt: str,
    cost_usd: float = 0,
    provider: str = "replicate",
    params: dict | None = None,
) -> dict:
    """Persist video generation result. Returns the created row."""
    client = get_supabase()
    job_params = {"prompt": prompt}
    if params:
        job_params.update(params)
    row = {
        "source_media_id": source_media_id,
        "job_type": "photo_to_video",
        "provider": provider,
        "status": "completed",
        "params": json.dumps(job_params),
        "cost_usd": cost_usd,
        "result_url": video_url,
    }
    result = client.table(TABLE_CREATIVE_JOBS).insert(row).execute()
    return result.data[0] if result.data else {}


def save_music_job(
    source_media_id: str,
    audio_url: str,
    prompt: str,
    cost_usd: float = 0,
    params: dict | None = None,
) -> dict:
    """Persist music generation result. Returns the created row.
    Also saves to generated_music table."""
    client = get_supabase()
    job_params = {"prompt": prompt}
    if params:
        job_params.update(params)
    row = {
        "source_media_id": source_media_id,
        "job_type": "music_gen",
        "provider": "replicate",
        "status": "completed",
        "params": json.dumps(job_params),
        "cost_usd": cost_usd,
        "result_url": audio_url,
    }
    result = client.table(TABLE_CREATIVE_JOBS).insert(row).execute()

    # Also save to generated_music table
    try:
        client.table(TABLE_GENERATED_MUSIC).insert({
            "source_media_id": source_media_id,
            "prompt": prompt,
            "preset": (params or {}).get("preset"),
            "duration_seconds": (params or {}).get("duration"),
            "audio_url": audio_url,
            "generation_params": job_params,
            "model": "musicgen",
            "cost_usd": cost_usd,
        }).execute()
    except Exception:
        pass

    return result.data[0] if result.data else {}


def fetch_jobs_for_media(
    source_media_id: str,
    job_type: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """Fetch recent completed jobs for a media item. Most recent first."""
    client = get_supabase()
    query = (
        client.table(TABLE_CREATIVE_JOBS)
        .select("*")
        .eq("source_media_id", source_media_id)
        .eq("status", "completed")
        .order("created_at", desc=True)
        .limit(limit)
    )
    if job_type:
        query = query.eq("job_type", job_type)
    result = query.execute()
    return result.data


def fetch_latest_scenarios(source_media_id: str) -> Optional[list[dict]]:
    """Get the most recent scenario generation for a media item."""
    jobs = fetch_jobs_for_media(source_media_id, job_type="scenario_generation", limit=1)
    if not jobs:
        return None
    try:
        return json.loads(jobs[0]["result_url"])
    except (json.JSONDecodeError, KeyError):
        return None


def fetch_video_jobs(source_media_id: str, limit: int = 5) -> list[dict]:
    """Get recent video generation jobs for a media item."""
    return fetch_jobs_for_media(source_media_id, job_type="photo_to_video", limit=limit)
