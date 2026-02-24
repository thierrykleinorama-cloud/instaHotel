"""
Claude Vision analyzer — sends hotel photos to Claude and parses structured JSON.
"""
import json
import os
import re
from pathlib import Path
from typing import Optional

import anthropic
from dotenv import load_dotenv

from src.models import VisionAnalysis

_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env")

MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """Tu es un expert en photographie hôtelière et marketing Instagram.
Tu analyses les photos et vidéos de l'Hôtel Noucentista, un hôtel boutique Art Nouveau à Sitges (Barcelone), Espagne.

L'hôtel a ces espaces principaux :
- Chambres (suites, chambres doubles, chambres singles) avec décoration Art Nouveau
- Espaces communs (lobby, salon, terrasse, couloirs, escaliers)
- Extérieurs (façade, jardin, piscine, vue sur mer, rue)
- Gastronomie (petit-déjeuner, bar, salle à manger)
- Expériences (spa, events, activités, vues panoramiques)

Réponds UNIQUEMENT avec un objet JSON valide (sans markdown, sans commentaires)."""

USER_PROMPT = """Analyse cette image d'hôtel et retourne un JSON avec exactement ces champs :

{
  "category": "chambre|commun|exterieur|gastronomie|experience",
  "subcategory": "nom spécifique de l'espace (ex: suite, terrasse, piscine, petit_dejeuner, spa)",
  "ambiance": ["liste de tags d'ambiance: lumineux, chaleureux, romantique, moderne, art_nouveau, mediterraneen, intime, elegant, naturel, colore"],
  "season": ["printemps|ete|automne|hiver|toute_saison — quand cette photo serait idéale pour Instagram"],
  "elements": ["liste des éléments visibles: lit, vue_mer, piscine, terrasse, mobilier, plantes, lumiere_naturelle, decoration, nourriture, etc."],
  "ig_quality": 8,
  "description_fr": "Description courte en français pour usage interne (1 phrase)",
  "description_en": "Short English description for search and retrieval (1 sentence)"
}

Critères pour ig_quality (1-10) :
- 9-10: Photo exceptionnelle, prête pour Instagram (composition, lumière, qualité pro)
- 7-8: Bonne photo, utilisable avec peu de retouche
- 5-6: Photo correcte mais pas idéale (angle, lumière, mise en scène)
- 3-4: Photo médiocre (floue, mal cadrée, peu attrayante)
- 1-2: Photo inutilisable (très floue, sombre, hors sujet)"""


def _parse_json_response(text: str) -> dict:
    """Parse Claude's JSON response, stripping markdown fences if present."""
    text = text.strip()
    # Strip markdown code fences
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def analyze_image(
    image_base64: str,
    media_type: str = "image/jpeg",
    model: str = MODEL,
) -> VisionAnalysis:
    """Send a single image to Claude Vision and return structured analysis."""
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": USER_PROMPT},
                ],
            }
        ],
    )

    raw_text = response.content[0].text
    data = _parse_json_response(raw_text)
    analysis = VisionAnalysis(**data)
    return analysis


def analyze_frames(
    frames_base64: list[str],
    context: str = "",
    model: str = MODEL,
) -> VisionAnalysis:
    """Send multiple video frames to Claude Vision as a single scene analysis."""
    client = anthropic.Anthropic()

    content = []
    for frame_b64 in frames_base64:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": frame_b64,
            },
        })

    prompt = USER_PROMPT
    if context:
        prompt = f"{context}\n\n{USER_PROMPT}"
    content.append({"type": "text", "text": prompt})

    response = client.messages.create(
        model=model,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    raw_text = response.content[0].text
    data = _parse_json_response(raw_text)
    analysis = VisionAnalysis(**data)
    return analysis


def get_raw_response(
    image_base64: str,
    media_type: str = "image/jpeg",
    model: str = MODEL,
) -> dict:
    """Like analyze_image but returns the raw dict (for storage in analysis_raw)."""
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": image_base64,
                        },
                    },
                    {"type": "text", "text": USER_PROMPT},
                ],
            }
        ],
    )

    raw_text = response.content[0].text
    return {
        "raw_text": raw_text,
        "parsed": _parse_json_response(raw_text),
        "model": response.model,
        "usage": {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        },
    }
