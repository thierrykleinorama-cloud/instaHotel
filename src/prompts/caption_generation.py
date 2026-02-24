"""
Prompt: Instagram Caption Generation
Generates 2 caption variants (short + storytelling) x 3 languages (ES/EN/FR) + hashtags.
"""

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
