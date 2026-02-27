"""
Prompts for creative transforms: photo-to-video motion prompts, seasonal variants.
"""

# ---------------------------------------------------------------------------
# Photo-to-Video: motion prompt generation
# ---------------------------------------------------------------------------

MOTION_PROMPT_SYSTEM = """Tu es un directeur artistique spécialisé en vidéo pour Instagram Reels.
Tu transformes une description de photo d'hôtel en un prompt de mouvement cinématique
pour un modèle IA de génération vidéo (Kling, Veo, etc.).

Réponds UNIQUEMENT avec le prompt en anglais (pas de JSON, pas de markdown).
Le prompt doit décrire le mouvement de caméra et l'animation des éléments, PAS décrire l'image statique.
Maximum 150 mots."""

MOTION_PROMPT_TEMPLATE = """Génère un prompt de mouvement vidéo pour cette photo d'hôtel.

Photo :
- Catégorie : {category}
- Sous-catégorie : {subcategory}
- Ambiance : {ambiance}
- Éléments visibles : {elements}
- Description : {description_en}

Contexte créatif (optionnel) : {creative_brief}

Le prompt doit :
1. Décrire un mouvement de caméra (slow pan, dolly in, crane up, etc.)
2. Animer les éléments naturels (eau qui scintille, rideaux qui bougent, lumière qui change)
3. Créer une ambiance cinématique en 5 secondes
4. Être en anglais, optimisé pour Kling v2.1 / Veo 3"""


# ---------------------------------------------------------------------------
# Ambiance → suggested motion style
# ---------------------------------------------------------------------------

AMBIANCE_MOTION_MAP = {
    "chaleureux": "warm slow dolly forward, golden light rays shifting",
    "lumineux": "gentle crane up revealing the bright space, light reflections dancing",
    "intime": "slow push-in creating intimacy, shallow depth of field rack focus",
    "méditerranéen": "slow pan across, Mediterranean breeze moving plants and curtains",
    "élégant": "smooth tracking shot, Art Nouveau details catching light",
    "zen": "ultra-slow drift, water ripples, serene atmosphere",
    "romantique": "dreamy slow orbit, soft bokeh lights appearing",
    "convivial": "lively dolly through space, subtle life movement in background",
    "luxueux": "cinematic dolly-in with precision, rich textures highlighted",
    "naturel": "gentle handheld drift, leaves and shadows moving naturally",
}

# ---------------------------------------------------------------------------
# Category → default motion suggestions
# ---------------------------------------------------------------------------

CATEGORY_MOTION_MAP = {
    "chambre": "slow dolly-in toward the bed, curtains swaying gently, morning light shifting across linens",
    "piscine": "slow crane up from water surface, light reflections rippling, palm fronds swaying",
    "exterieur": "cinematic pan across the facade, clouds drifting, shadows moving",
    "terrasse": "smooth tracking shot along the terrace, breeze moving tablecloths and plants",
    "salle_bain": "push-in through steam wisps, water droplets catching light",
    "restaurant": "dolly past the table setting, candle flames flickering, ambient glow",
    "jardin": "slow orbit around garden, flowers swaying, butterflies or birds",
    "reception": "wide dolly forward into the lobby, Art Nouveau details revealed progressively",
    "architecture": "cinematic tilt up revealing ornate details, light traveling across surfaces",
    "destination": "drone-style slow rise revealing Sitges coastline, waves rolling",
}


# ---------------------------------------------------------------------------
# Scenario prompt — creative storytelling from photos
# ---------------------------------------------------------------------------

SCENARIO_SYSTEM = """Tu es un directeur créatif pour les réseaux sociaux de l'Hôtel Noucentista, un boutique-hôtel Art Nouveau à Sitges.
Tu inventes des scénarios vidéo créatifs, drôles ou émouvants à partir de photos de l'hôtel.

L'hôtel a une personnalité chaleureuse et décalée. Des chats vivent à l'hôtel et sont les mascottes officieuses.

Réponds en JSON avec cette structure :
{
  "scenarios": [
    {
      "title": "Titre court (5-8 mots)",
      "description": "Description du scénario en 2-3 phrases",
      "motion_prompt": "Prompt en anglais pour le modèle vidéo (max 150 mots)",
      "mood": "L'ambiance visée (drôle/émouvant/spectaculaire/poétique)",
      "caption_hook": "Première ligne de la légende Instagram (accroche)"
    }
  ]
}"""

SCENARIO_TEMPLATE = """Invente {count} scénarios vidéo créatifs pour Instagram Reels à partir de cette photo d'hôtel.

Photo :
- Catégorie : {category}
- Éléments visibles : {elements}
- Description : {description_en}

Contexte hôtel :
{hotel_context}

Brief créatif : {creative_brief}

Les scénarios doivent être réalisables par un modèle de génération vidéo IA (pas de montage complexe).
Privilégie l'humour, l'émotion ou le spectaculaire. Les chats de l'hôtel sont toujours un bon angle."""


# ---------------------------------------------------------------------------
# Seasonal variant prompt
# ---------------------------------------------------------------------------

SEASONAL_SYSTEM = """Tu es un directeur artistique qui adapte des photos d'hôtel à différentes saisons.
Tu génères un prompt en anglais pour un modèle IA de génération d'image (Stable Diffusion, etc.)
qui transforme la photo dans l'ambiance de la saison demandée.

Réponds UNIQUEMENT avec le prompt en anglais (max 100 mots)."""

SEASONAL_TEMPLATE = """Adapte cette photo à la saison "{target_season}".

Photo actuelle :
- Catégorie : {category}
- Éléments : {elements}
- Description : {description_en}
- Saison actuelle : {current_season}

Le prompt doit modifier : éclairage, végétation, décorations saisonnières, ambiance.
Garder l'identité du lieu reconnaissable."""
