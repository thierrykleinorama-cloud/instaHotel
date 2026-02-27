"""
Tone variant definitions for caption generation.
Each tone provides a French instruction injected into the user prompt
and an optional system addendum that adjusts the AI's personality.
"""

TONES = {
    "default": {
        "label": "Default (Chaleureux)",
        "description": "Warm, authentic, welcoming — the hotel's natural voice",
        "instruction_fr": "Ton : chaleureux, authentique, jamais corporate.",
        "system_addendum": "",
    },
    "luxe": {
        "label": "Luxe & Raffiné",
        "description": "Elegant, sophisticated, understated luxury",
        "instruction_fr": (
            "Ton : luxe et raffiné. Vocabulaire soigné, évoque l'élégance, "
            "le raffinement et l'exclusivité. Jamais tape-à-l'œil — "
            "c'est un luxe discret, Art Nouveau, méditerranéen."
        ),
        "system_addendum": (
            "Tu écris comme un rédacteur de magazine haut de gamme. "
            "Phrases élégantes, adjectifs précis, rythme posé."
        ),
    },
    "casual": {
        "label": "Casual & Fun",
        "description": "Relaxed, friendly, approachable — like talking to a friend",
        "instruction_fr": (
            "Ton : décontracté et fun. Comme si tu parlais à un ami. "
            "Phrases courtes, langage simple, énergie positive. "
            "Tu peux utiliser des expressions familières (sans vulgarité)."
        ),
        "system_addendum": (
            "Tu écris comme un ami qui partage ses bons plans. "
            "Naturel, spontané, zéro formalisme."
        ),
    },
    "humorous": {
        "label": "Humour & Décalé",
        "description": "Witty, playful, unexpected twists — makes people smile",
        "instruction_fr": (
            "Ton : humoristique et décalé. Jeux de mots bienvenus, "
            "comparaisons inattendues, autodérision légère. "
            "L'objectif : faire sourire. Reste bienveillant."
        ),
        "system_addendum": (
            "Tu es un copywriter créatif avec un sens de l'humour fin. "
            "Tu trouves l'angle inattendu, le twist qui fait sourire. "
            "Jamais méchant, toujours malin."
        ),
    },
    "romantic": {
        "label": "Romantique & Poétique",
        "description": "Dreamy, sensory, evocative — ideal for couples/sunsets/architecture",
        "instruction_fr": (
            "Ton : romantique et poétique. Évoque les sens (lumière, parfums, textures). "
            "Phrases qui font rêver, métaphores douces. "
            "Idéal pour les couchers de soleil, l'architecture, les moments à deux."
        ),
        "system_addendum": (
            "Tu écris comme un poète amoureux de la Méditerranée. "
            "Chaque mot peint une image, chaque phrase invite au voyage."
        ),
    },
}

TONE_KEYS = list(TONES.keys())

TONE_LABELS = {key: t["label"] for key, t in TONES.items()}

# Reverse: label → key
TONE_LABELS_REVERSE = {v: k for k, v in TONE_LABELS.items()}


def get_tone_instruction(tone_key: str) -> str:
    """Return the French tone instruction line for the given tone key."""
    return TONES.get(tone_key, TONES["default"])["instruction_fr"]


def get_tone_system_addendum(tone_key: str) -> str:
    """Return the system prompt addendum (extra personality) for the given tone."""
    return TONES.get(tone_key, TONES["default"])["system_addendum"]
