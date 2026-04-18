"""
Prompts for AI music generation — maps hotel ambiance/category to music styles.
"""

# ---------------------------------------------------------------------------
# Ambiance → music style mapping
# ---------------------------------------------------------------------------

AMBIANCE_MUSIC_MAP = {
    "warm": "warm acoustic guitar, soft bossa nova, cozy cafe atmosphere",
    "bright": "upbeat acoustic pop, bright ukulele, morning sunshine vibes",
    "cozy": "soft piano, intimate jazz trio, whispered percussion",
    "mediterranean": "Spanish guitar, light flamenco rhythm, sea breeze feeling",
    "elegant": "smooth jazz piano, subtle strings, sophisticated lounge",
    "zen": "ambient pads, soft water sounds, meditation bells, peaceful",
    "romantic": "romantic piano melody, soft strings, sunset warmth",
    "friendly": "upbeat latin acoustic, gentle percussion, happy terrace vibes",
    "luxurious": "cinematic strings, elegant piano, luxury hotel lobby ambiance",
    "natural": "nature-inspired ambient, soft wind instruments, organic textures",
    "art_nouveau": "elegant piano with subtle strings, refined Art Nouveau atmosphere",
    "colorful": "upbeat Mediterranean acoustic, lively percussion, vibrant atmosphere",
}

# ---------------------------------------------------------------------------
# Category → music style mapping
# ---------------------------------------------------------------------------

CATEGORY_MUSIC_MAP = {
    "room": "soft piano, warm ambient pads, cozy bedroom atmosphere",
    "exterior": "Mediterranean acoustic guitar, warm breeze atmosphere",
    "common": "elegant lobby music, soft jazz piano, welcoming warmth",
    "food": "jazz trio, upright bass, candlelit dinner atmosphere",
    "experience": "cinematic ambient, uplifting tones, moment of discovery",
    "destination": "Mediterranean world music, acoustic guitar, travel adventure",
    # Subcategory-level fallbacks (kept for finer-grained matching)
    "terrace": "bossa nova, light percussion, outdoor cafe in the sun",
    "bathroom": "spa ambient, water sounds, peaceful minimalist piano",
    "restaurant": "jazz trio, upright bass, candlelit dinner atmosphere",
    "patio": "acoustic guitar, birdsong elements, Mediterranean patio serenity",
    "reception": "elegant lobby music, soft jazz piano, welcoming warmth",
    "architecture": "cinematic ambient, subtle reverb piano, awe and wonder",
}

# ---------------------------------------------------------------------------
# Mood → music style (for scenario-driven generation)
# ---------------------------------------------------------------------------

MOOD_MUSIC_MAP = {
    "funny": "playful pizzicato strings, quirky percussion, cartoon-like whimsy",
    "emotional": "emotional piano, gentle strings crescendo, touching warmth",
    "spectacular": "epic cinematic orchestra, building drums, reveal moment",
    "poetic": "dreamy ambient piano, soft reverb, floating atmosphere",
}


def build_music_prompt(
    media: dict,
    mood: str | None = None,
    custom_prompt: str | None = None,
) -> str:
    """Build a music generation prompt from media metadata.

    Priority: custom_prompt > mood > ambiance > category > default.
    """
    if custom_prompt:
        return custom_prompt

    parts = []

    # Mood-based (from scenario)
    if mood and mood in MOOD_MUSIC_MAP:
        parts.append(MOOD_MUSIC_MAP[mood])

    # Ambiance-based
    ambiance = media.get("ambiance", [])
    if isinstance(ambiance, list):
        for a in ambiance:
            if a in AMBIANCE_MUSIC_MAP:
                parts.append(AMBIANCE_MUSIC_MAP[a])
                break
    elif isinstance(ambiance, str) and ambiance in AMBIANCE_MUSIC_MAP:
        parts.append(AMBIANCE_MUSIC_MAP[ambiance])

    # Category-based
    category = media.get("category", "")
    if category in CATEGORY_MUSIC_MAP:
        parts.append(CATEGORY_MUSIC_MAP[category])

    if not parts:
        parts.append("warm Mediterranean acoustic guitar, hotel boutique atmosphere, relaxed and inviting")

    # Combine and deduplicate
    prompt = ", ".join(parts)

    # Add standard suffix for Instagram Reel context
    prompt += ". Instrumental only, no vocals, suitable for Instagram Reel background music."

    return prompt
