"""
Prompts for AI music generation — maps hotel ambiance/category to music styles.
"""

# ---------------------------------------------------------------------------
# Ambiance → music style mapping
# ---------------------------------------------------------------------------

AMBIANCE_MUSIC_MAP = {
    "chaleureux": "warm acoustic guitar, soft bossa nova, cozy cafe atmosphere",
    "lumineux": "upbeat acoustic pop, bright ukulele, morning sunshine vibes",
    "intime": "soft piano, intimate jazz trio, whispered percussion",
    "méditerranéen": "Spanish guitar, light flamenco rhythm, sea breeze feeling",
    "élégant": "smooth jazz piano, subtle strings, sophisticated lounge",
    "zen": "ambient pads, soft water sounds, meditation bells, peaceful",
    "romantique": "romantic piano melody, soft strings, sunset warmth",
    "convivial": "upbeat latin acoustic, gentle percussion, happy terrace vibes",
    "luxueux": "cinematic strings, elegant piano, luxury hotel lobby ambiance",
    "naturel": "nature-inspired ambient, soft wind instruments, organic textures",
}

# ---------------------------------------------------------------------------
# Category → music style mapping
# ---------------------------------------------------------------------------

CATEGORY_MUSIC_MAP = {
    "chambre": "soft piano, warm ambient pads, cozy bedroom atmosphere",
    "piscine": "chill tropical house, soft beat, poolside lounge vibes",
    "exterieur": "Mediterranean acoustic guitar, warm breeze atmosphere",
    "terrasse": "bossa nova, light percussion, outdoor cafe in the sun",
    "salle_bain": "spa ambient, water sounds, peaceful minimalist piano",
    "restaurant": "jazz trio, upright bass, candlelit dinner atmosphere",
    "jardin": "acoustic guitar, birdsong elements, garden serenity",
    "reception": "elegant lobby music, soft jazz piano, welcoming warmth",
    "architecture": "cinematic ambient, subtle reverb piano, awe and wonder",
    "destination": "Mediterranean world music, acoustic guitar, travel adventure",
}

# ---------------------------------------------------------------------------
# Mood → music style (for scenario-driven generation)
# ---------------------------------------------------------------------------

MOOD_MUSIC_MAP = {
    "drôle": "playful pizzicato strings, quirky percussion, cartoon-like whimsy",
    "émouvant": "emotional piano, gentle strings crescendo, touching warmth",
    "spectaculaire": "epic cinematic orchestra, building drums, reveal moment",
    "poétique": "dreamy ambient piano, soft reverb, floating atmosphere",
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
