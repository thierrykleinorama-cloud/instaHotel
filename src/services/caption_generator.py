"""
Caption generator — sends media metadata (and optionally the image) to Claude
for Instagram caption generation in ES/EN/FR.
"""
import json
import re
from typing import Optional

import anthropic

MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = """Tu es le community manager de l'Hôtel Noucentista, un hôtel boutique Art Nouveau à Sitges (Barcelone).
Tu écris des légendes Instagram authentiques, chaleureuses, jamais corporate.
Tu maîtrises parfaitement l'espagnol, l'anglais et le français.

Réponds UNIQUEMENT avec un objet JSON valide (sans markdown, sans commentaires)."""

USER_PROMPT_TEMPLATE = """Génère des légendes Instagram pour ce média hôtelier.

Contexte du média :
- Catégorie : {category}
- Sous-catégorie : {subcategory}
- Ambiance : {ambiance}
- Éléments visibles : {elements}
- Description FR : {description_fr}
- Description EN : {description_en}
- Notes manuelles : {manual_notes}

Contexte éditorial :
- Thème : {theme}
- Saison : {season}
- Type de CTA : {cta_type}

Génère un JSON avec cette structure exacte :
{{
  "short": {{
    "es": "Légende courte en espagnol (2-3 lignes, percutante)",
    "en": "Short English caption (2-3 lines, punchy)",
    "fr": "Légende courte en français (2-3 lignes, percutante)"
  }},
  "storytelling": {{
    "es": "Légende storytelling en espagnol (5-6 lignes, émotionnelle)",
    "en": "Storytelling English caption (5-6 lines, emotional)",
    "fr": "Légende storytelling en français (5-6 lignes, émotionnelle)"
  }},
  "hashtags": ["20 hashtags pertinents, mix popularité, sans le #"]
}}

Inclus un CTA naturel ({cta_type}) dans chaque légende.
Ton : chaleureux, authentique, jamais corporate."""


def _parse_json_response(text: str) -> dict:
    """Parse Claude's JSON response, stripping markdown fences if present."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        text = match.group(1).strip()
    return json.loads(text)


def generate_captions(
    media: dict,
    theme: str,
    season: str,
    cta_type: str,
    include_image: bool = False,
    image_base64: Optional[str] = None,
) -> dict:
    """
    Generate Instagram captions via Claude API.

    Args:
        media: dict with category, subcategory, ambiance, elements, descriptions, manual_notes
        theme: editorial theme
        season: target season
        cta_type: CTA type (link_bio, dm, book_now)
        include_image: if True, sends image_base64 for richer output
        image_base64: base64-encoded JPEG (required if include_image=True)

    Returns:
        dict with keys: short, storytelling, hashtags
    """
    # Support st.secrets (Streamlit Cloud) or ANTHROPIC_API_KEY env var
    api_key = None
    try:
        import streamlit as st
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
    except Exception:
        pass
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    prompt_text = USER_PROMPT_TEMPLATE.format(
        category=media.get("category", ""),
        subcategory=media.get("subcategory", ""),
        ambiance=", ".join(media.get("ambiance", [])) if isinstance(media.get("ambiance"), list) else media.get("ambiance", ""),
        elements=", ".join(media.get("elements", [])) if isinstance(media.get("elements"), list) else media.get("elements", ""),
        description_fr=media.get("description_fr", ""),
        description_en=media.get("description_en", ""),
        manual_notes=media.get("manual_notes", "Aucune"),
        theme=theme,
        season=season,
        cta_type=cta_type,
    )

    content = []
    if include_image and image_base64:
        content.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_base64,
                },
            }
        )
    content.append({"type": "text", "text": prompt_text})

    response = client.messages.create(
        model=MODEL,
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    raw_text = response.content[0].text
    return _parse_json_response(raw_text)
