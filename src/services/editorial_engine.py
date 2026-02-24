"""
Editorial Strategy Engine — pure Python, no Streamlit dependency.
Scoring algorithm + calendar generation.
"""
from datetime import date, timedelta
from typing import Optional

from src.database import get_supabase, TABLE_MEDIA_LIBRARY, TABLE_EDITORIAL_CALENDAR


# -----------------------------------------------------------
# Season detection
# -----------------------------------------------------------

SEASON_MAP = {
    1: "hiver", 2: "hiver", 3: "printemps",
    4: "printemps", 5: "printemps", 6: "ete",
    7: "ete", 8: "ete", 9: "automne",
    10: "automne", 11: "automne", 12: "hiver",
}


def get_current_season(d: date) -> str:
    """Return season string for a given date (month-based)."""
    return SEASON_MAP[d.month]


# -----------------------------------------------------------
# Format ↔ aspect ratio mapping
# -----------------------------------------------------------

FORMAT_ASPECT = {
    "feed": {"4:5", "1:1"},
    "story": {"9:16"},
    "reel": {"9:16"},
}


# -----------------------------------------------------------
# Scoring — 100 points max
# -----------------------------------------------------------

def score_media(
    media: dict,
    target_category: Optional[str],
    target_season: str,
    target_format: Optional[str],
    theme: Optional[dict],
    recently_used_ids: set[str],
    today: date,
) -> tuple[float, dict]:
    """
    Score a media item against editorial requirements.
    Returns (total_score, breakdown_dict).
    """
    breakdown = {}

    # 1. Category match (25 pts)
    if target_category and media.get("category") == target_category:
        breakdown["category"] = 25.0
    else:
        breakdown["category"] = 0.0

    # 2. Season match (20 pts)
    media_seasons = media.get("season") or []
    if target_season in media_seasons:
        breakdown["season"] = 20.0
    elif "toute_saison" in media_seasons:
        breakdown["season"] = 12.0
    else:
        breakdown["season"] = 0.0

    # 3. Quality (20 pts) — ig_quality / 10 × 20
    quality = media.get("ig_quality") or 0
    breakdown["quality"] = round((quality / 10) * 20, 2)

    # 4. Freshness (20 pts) — never used = 20, otherwise decay
    last_used = media.get("last_used_at")
    used_count = media.get("used_count") or 0
    if used_count == 0 or last_used is None:
        breakdown["freshness"] = 20.0
    else:
        # Parse last_used_at (ISO string from Supabase)
        if isinstance(last_used, str):
            try:
                last_date = date.fromisoformat(last_used[:10])
            except ValueError:
                last_date = today
        else:
            last_date = today
        days_since = (today - last_date).days
        # Linear ramp: 0 days ago = 4, 30+ days = 18
        freshness = min(18.0, 4.0 + (days_since / 30) * 14)
        breakdown["freshness"] = round(freshness, 2)

    # 5. Theme bonus (10 pts) — overlap of ambiance/elements with theme prefs
    if theme:
        theme_ambiances = set(theme.get("preferred_ambiances") or [])
        theme_elements = set(theme.get("preferred_elements") or [])
        media_ambiances = set(media.get("ambiance") or [])
        media_elements = set(media.get("elements") or [])

        overlap_amb = len(media_ambiances & theme_ambiances)
        overlap_elem = len(media_elements & theme_elements)
        max_possible = max(len(theme_ambiances) + len(theme_elements), 1)
        ratio = (overlap_amb + overlap_elem) / max_possible
        breakdown["theme"] = round(min(10.0, ratio * 10), 2)
    else:
        breakdown["theme"] = 0.0

    # 6. Format bonus (5 pts) — aspect ratio match
    if target_format:
        preferred_aspects = FORMAT_ASPECT.get(target_format, set())
        media_aspect = media.get("aspect_ratio") or ""
        breakdown["format"] = 5.0 if media_aspect in preferred_aspects else 0.0
    else:
        breakdown["format"] = 0.0

    total = round(sum(breakdown.values()), 2)
    return total, breakdown


# -----------------------------------------------------------
# Media selection
# -----------------------------------------------------------

def _fetch_analyzed_media() -> list[dict]:
    """Fetch all analyzed media from DB (no Streamlit cache)."""
    client = get_supabase()
    result = (
        client.table(TABLE_MEDIA_LIBRARY)
        .select("id,category,subcategory,ambiance,season,elements,ig_quality,aspect_ratio,media_type,file_name,drive_file_id,used_count,last_used_at,description_fr")
        .eq("status", "analyzed")
        .execute()
    )
    return result.data


def _fetch_recent_media_ids(lookback_days: int = 7) -> set[str]:
    """Get media IDs used in calendar within last N days (no Streamlit cache)."""
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


def select_best_media(
    all_media: list[dict],
    target_category: Optional[str],
    target_season: str,
    target_format: Optional[str],
    min_quality: int,
    theme: Optional[dict],
    recently_used_ids: set[str],
    batch_used_ids: set[str],
    today: date,
    top_n: int = 5,
) -> list[tuple[dict, float, dict]]:
    """
    Filter, score, and rank media. Returns up to top_n results as
    [(media_dict, score, breakdown), ...] sorted by score desc.
    """
    candidates = []
    for m in all_media:
        mid = m["id"]
        # Hard exclude: recently used in last 7 days
        if mid in recently_used_ids:
            continue
        # Batch dedup: already assigned in this generation run
        if mid in batch_used_ids:
            continue
        # Quality floor
        if (m.get("ig_quality") or 0) < min_quality:
            continue

        score, breakdown = score_media(
            m, target_category, target_season, target_format, theme, recently_used_ids, today
        )
        candidates.append((m, score, breakdown))

    # Sort by score descending
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[:top_n]


# -----------------------------------------------------------
# Calendar generation
# -----------------------------------------------------------

def generate_calendar(
    start_date: date,
    end_date: date,
    rules: list[dict],
    fetch_theme_fn,
    overwrite_existing: bool = False,
) -> list[dict]:
    """
    Generate editorial calendar entries for a date range.

    Args:
        start_date, end_date: inclusive date range
        rules: list of editorial_rules rows
        fetch_theme_fn: callable(date) -> Optional[dict] to get active theme
        overwrite_existing: if False, skip dates that already have entries

    Returns:
        list of calendar entry dicts ready for bulk upsert
    """
    all_media = _fetch_analyzed_media()
    recently_used = _fetch_recent_media_ids(7)

    # If not overwriting, fetch existing entries to skip
    existing_keys = set()
    if not overwrite_existing:
        client = get_supabase()
        result = (
            client.table(TABLE_EDITORIAL_CALENDAR)
            .select("post_date,slot_index")
            .gte("post_date", start_date.isoformat())
            .lte("post_date", end_date.isoformat())
            .execute()
        )
        existing_keys = {(row["post_date"], row["slot_index"]) for row in result.data}

    # Build rule lookup by day_of_week
    rules_by_day: dict[int, list[dict]] = {}
    for r in rules:
        if r.get("is_active", True):
            rules_by_day.setdefault(r["day_of_week"], []).append(r)

    entries = []
    batch_used: set[str] = set()
    current = start_date

    while current <= end_date:
        dow = current.isoweekday()  # 1=Mon..7=Sun
        day_rules = rules_by_day.get(dow, [])
        season = get_current_season(current)
        theme = fetch_theme_fn(current)

        for rule in day_rules:
            slot = rule["slot_index"]
            # Skip if entry already exists and not overwriting
            if (current.isoformat(), slot) in existing_keys:
                continue

            target_cat = rule.get("default_category")
            target_fmt = rule.get("preferred_format")
            min_q = rule.get("min_quality") or 6

            candidates = select_best_media(
                all_media=all_media,
                target_category=target_cat,
                target_season=season,
                target_format=target_fmt,
                min_quality=min_q,
                theme=theme,
                recently_used_ids=recently_used,
                batch_used_ids=batch_used,
                today=current,
            )

            best_media = None
            best_score = 0.0
            best_breakdown = {}
            if candidates:
                best_media, best_score, best_breakdown = candidates[0]
                batch_used.add(best_media["id"])

            entry = {
                "post_date": current.isoformat(),
                "slot_index": slot,
                "time_slot": rule.get("preferred_time"),
                "rule_id": rule.get("id"),
                "target_category": target_cat,
                "target_format": target_fmt,
                "theme_id": theme["id"] if theme else None,
                "season_context": season,
                "theme_name": theme["theme_name"] if theme else None,
                "media_id": best_media["id"] if best_media else None,
                "media_score": best_score if best_media else None,
                "score_breakdown": best_breakdown if best_media else None,
                "status": "generated" if best_media else "planned",
            }
            entries.append(entry)

        current += timedelta(days=1)

    return entries
