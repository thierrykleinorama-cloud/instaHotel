"""
Prompt: Instagram Caption Generation
Generates 2-3 caption variants (short + storytelling + reel for videos) x 3 languages (ES/EN/FR) + hashtags.
"""
from src.prompts.sitges_context import SITGES_OVERVIEW, SITGES_PRACTICAL

VIDEO_INSTRUCTION = "IMPORTANT: This media is a video. For the 'reel' variant, write an ultra-short hook that grabs attention in the first second. Focus on movement, action, POV. For other variants, evoke the movement and visual experience."

SYSTEM_PROMPT = f"""You are the community manager of Hotel Noucentista, a boutique Art Nouveau hotel in Sitges (Barcelona).
You write authentic, warm Instagram captions — never corporate.
You are fluent in Spanish, English, and French.

SITGES CONTEXT (use these details to write locally-grounded captions):
{SITGES_OVERVIEW}

HOTEL CONNECTION:
{SITGES_PRACTICAL.split("HOTEL NOUCENTISTA CONNECTION:")[1].strip() if "HOTEL NOUCENTISTA CONNECTION:" in SITGES_PRACTICAL else "Boutique Art Nouveau hotel in the heart of Sitges, Carrer de l'Illa de Cuba 21."}

Respond ONLY with a valid JSON object (no markdown, no commentary)."""

USER_PROMPT_TEMPLATE = """Generate Instagram captions for this hotel media.

Media context:
- Media type: {media_type}
- Category: {category}
- Subcategory: {subcategory}
- Ambiance: {ambiance}
- Visible elements: {elements}
- FR description: {description_fr}
- EN description: {description_en}
- Manual notes: {manual_notes}

Editorial context:
- Theme: {theme}
- Season: {season}
- CTA type: {cta_type}

Generate a JSON object with this exact structure:
{{
  "short": {{
    "es": "Short Spanish caption (2-3 punchy lines)",
    "en": "Short English caption (2-3 punchy lines)",
    "fr": "Short French caption (2-3 punchy lines)"
  }},
  "storytelling": {{
    "es": "Spanish storytelling caption (5-6 emotional lines)",
    "en": "English storytelling caption (5-6 emotional lines)",
    "fr": "French storytelling caption (5-6 emotional lines)"
  }},
  "reel": {{
    "es": "Spanish reel caption (1-2 lines max, instant hook, hook-first, POV/action style)",
    "en": "English reel caption (1-2 lines max, instant hook, hook-first, POV/action style)",
    "fr": "French reel caption (1-2 lines max, instant hook, hook-first, POV/action style)"
  }},
  "hashtags": ["20 relevant hashtags, mix of popularity levels, without the #"]
}}

Include a natural CTA ({cta_type}) in each caption.
{tone_instruction}
{video_instruction}"""
