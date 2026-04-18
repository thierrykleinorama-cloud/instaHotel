"""
Character registry query helpers.
Characters are recurring entities (cats, owner, etc.) used as reference images
for consistent video generation.
"""
from typing import Optional

from src.database import get_supabase

TABLE_CHARACTERS = "characters"


def fetch_active_characters() -> list[dict]:
    """Fetch all active characters with their metadata."""
    client = get_supabase()
    result = (
        client.table(TABLE_CHARACTERS)
        .select("id, name, species, description, reference_media_id, notes")
        .eq("is_active", True)
        .order("species")
        .order("name")
        .execute()
    )
    return result.data


def fetch_character(character_id: str) -> Optional[dict]:
    """Fetch one character by ID."""
    client = get_supabase()
    result = (
        client.table(TABLE_CHARACTERS)
        .select("*")
        .eq("id", character_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def fetch_characters_by_ids(character_ids: list[str]) -> list[dict]:
    """Fetch multiple characters by their IDs, preserving order."""
    if not character_ids:
        return []
    client = get_supabase()
    result = (
        client.table(TABLE_CHARACTERS)
        .select("id, name, species, description, reference_media_id, extra_reference_drive_ids")
        .in_("id", character_ids)
        .execute()
    )
    by_id = {c["id"]: c for c in result.data}
    return [by_id[cid] for cid in character_ids if cid in by_id]


def load_character_reference_images(character_ids: list[str]) -> list[tuple[dict, bytes]]:
    """Load ALL reference images for a list of character IDs.

    Sources (per character):
      1. reference_media_id → single primary ref from media_library
      2. media_library.character_ids → all hotel photos tagged with this character
      3. extra_reference_drive_ids → dedicated character ref photos in Drive (not in media_library)

    Returns: list of (character_dict, image_bytes) tuples.
    A character with multiple reference photos produces multiple tuples.
    """
    from src.database import TABLE_MEDIA_LIBRARY
    from src.services.google_drive import download_file_bytes

    chars = fetch_characters_by_ids(character_ids)
    if not chars:
        return []

    client = get_supabase()

    # Batch-fetch all media tagged with any of these character IDs
    tagged_rows = (
        client.table(TABLE_MEDIA_LIBRARY)
        .select("id, drive_file_id, character_ids")
        .overlaps("character_ids", character_ids)
        .execute()
    ).data
    # Map: character_id → list of drive_file_ids
    tagged_drive_map: dict[str, list[str]] = {cid: [] for cid in character_ids}
    for row in tagged_rows:
        for cid in (row.get("character_ids") or []):
            if cid in tagged_drive_map:
                tagged_drive_map[cid].append(row["drive_file_id"])

    # Also fetch the primary reference_media_id drive_file_ids
    primary_media_ids = [c["reference_media_id"] for c in chars if c.get("reference_media_id")]
    primary_drive_map = {}
    if primary_media_ids:
        media_rows = (
            client.table(TABLE_MEDIA_LIBRARY)
            .select("id, drive_file_id")
            .in_("id", primary_media_ids)
            .execute()
        ).data
        primary_drive_map = {m["id"]: m["drive_file_id"] for m in media_rows}

    result = []
    for char in chars:
        seen_drive_ids = set()

        # Source 1: primary reference_media_id
        ref_id = char.get("reference_media_id")
        if ref_id and ref_id in primary_drive_map:
            did = primary_drive_map[ref_id]
            seen_drive_ids.add(did)
            try:
                result.append((char, download_file_bytes(did)))
            except Exception:
                pass

        # Source 2: media_library items tagged with this character
        for did in tagged_drive_map.get(char["id"], []):
            if did in seen_drive_ids:
                continue
            seen_drive_ids.add(did)
            try:
                result.append((char, download_file_bytes(did)))
            except Exception:
                continue

        # Source 3: extra_reference_drive_ids (not in media_library)
        for did in (char.get("extra_reference_drive_ids") or []):
            if did in seen_drive_ids:
                continue
            seen_drive_ids.add(did)
            try:
                result.append((char, download_file_bytes(did)))
            except Exception:
                continue

    return result


def build_character_roster_prompt(characters: list[dict]) -> str:
    """Build a text block listing available characters for injection into scenario prompts.

    Used by the scenario generator so it knows which characters exist and can
    intelligently include them in motion_prompts based on creative intent.
    """
    if not characters:
        return ""
    lines = ["AVAILABLE CHARACTERS (use when a scenario naturally involves them):"]
    for c in characters:
        desc = c.get("description", "")
        lines.append(f"- {c['name']} ({c['species']}): {desc}")
    return "\n".join(lines)
