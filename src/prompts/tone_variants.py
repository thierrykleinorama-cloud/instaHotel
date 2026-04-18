"""
Tone variant definitions for caption generation.
Each tone provides an English instruction injected into the user prompt
and an optional system addendum that adjusts the AI's personality.
"""

TONES = {
    "default": {
        "label": "Default (Warm)",
        "description": "Warm, authentic, welcoming — the hotel's natural voice",
        "instruction": "Tone: warm, authentic, never corporate.",
        "system_addendum": "",
    },
    "luxe": {
        "label": "Luxe & Refined",
        "description": "Elegant, sophisticated, understated luxury",
        "instruction": (
            "Tone: luxurious and refined. Polished vocabulary, evoking elegance, "
            "refinement, and exclusivity. Never flashy — this is quiet luxury, "
            "Art Nouveau, Mediterranean."
        ),
        "system_addendum": (
            "You write like a high-end magazine editor. "
            "Elegant sentences, precise adjectives, measured rhythm."
        ),
    },
    "casual": {
        "label": "Casual & Fun",
        "description": "Relaxed, friendly, approachable — like talking to a friend",
        "instruction": (
            "Tone: casual and fun. As if talking to a friend. "
            "Short sentences, simple language, positive energy. "
            "Familiar expressions are welcome (without vulgarity)."
        ),
        "system_addendum": (
            "You write like a friend sharing tips. "
            "Natural, spontaneous, zero formalism."
        ),
    },
    "humorous": {
        "label": "Humorous & Offbeat",
        "description": "Witty, playful, unexpected twists — makes people smile",
        "instruction": (
            "Tone: humorous and offbeat. Wordplay welcome, "
            "unexpected comparisons, light self-deprecation. "
            "Goal: make people smile. Stay kind."
        ),
        "system_addendum": (
            "You are a creative copywriter with sharp humor. "
            "You find the unexpected angle, the twist that makes people smile. "
            "Never mean, always clever."
        ),
    },
    "romantic": {
        "label": "Romantic & Poetic",
        "description": "Dreamy, sensory, evocative — ideal for couples/sunsets/architecture",
        "instruction": (
            "Tone: romantic and poetic. Evoke the senses (light, scents, textures). "
            "Sentences that inspire dreams, soft metaphors. "
            "Ideal for sunsets, architecture, moments together."
        ),
        "system_addendum": (
            "You write like a poet in love with the Mediterranean. "
            "Every word paints an image, every sentence invites a journey."
        ),
    },
}

TONE_KEYS = list(TONES.keys())

TONE_LABELS = {key: t["label"] for key, t in TONES.items()}

# Reverse: label → key
TONE_LABELS_REVERSE = {v: k for k, v in TONE_LABELS.items()}


def get_tone_instruction(tone_key: str) -> str:
    """Return the English tone instruction line for the given tone key."""
    return TONES.get(tone_key, TONES["default"])["instruction"]


def get_tone_system_addendum(tone_key: str) -> str:
    """Return the system prompt addendum (extra personality) for the given tone."""
    return TONES.get(tone_key, TONES["default"])["system_addendum"]
