"""
Destination content prompts — "beyond the hotel" posts for Instagram reach.
Pillar 2: Sitges destination content (vs Pillar 1: hotel-focused).

Strategy: ~1 post per week. Angle is "alternative / hidden gems" —
NOT tourist clichés. Noucentista is mentioned naturally, never as the main subject.
"""

# ---------------------------------------------------------------------------
# Destination context — Sitges local knowledge for Claude
# ---------------------------------------------------------------------------

# Import the comprehensive Sitges context from the dedicated module
from src.prompts.sitges_context import SITGES_FULL_CONTEXT

DESTINATION_CONTEXT = SITGES_FULL_CONTEXT + """
CONTENT ANGLE (for destination posts):
The angle for destination posts is ALWAYS "alternative / insider / hidden gems" —
NOT the obvious tourist attractions. We position Hotel Noucentista as the insider's base
for discovering the real Sitges.
"""

# ---------------------------------------------------------------------------
# Content pillar definitions
# ---------------------------------------------------------------------------

CONTENT_PILLARS = {
    "hotel": {
        "label": "Hotel & Experience",
        "frequency": "~70% of posts",
        "description": "Rooms, spaces, cats, ambiance, guest experience. The hotel is the subject.",
        "hotel_mention": "Primary subject",
    },
    "destination": {
        "label": "Sitges Insider",
        "frequency": "~20% of posts (1/week minimum)",
        "description": "Hidden gems, alternative activities, local food, seasonal events. Sitges is the subject, Noucentista is the insider's base.",
        "hotel_mention": "Subtle — 'from our doorstep', 'our guests love', 'ask us for directions'",
        "angle": "Alternative / hidden gems — NOT tourist clichés",
    },
    "community": {
        "label": "Community & Stories",
        "frequency": "~10% of posts",
        "description": "Guest stories, reviews, UGC reposts, behind-the-scenes. People are the subject.",
        "hotel_mention": "Through guest voice, not hotel voice",
    },
}

# ---------------------------------------------------------------------------
# Destination post formats
# ---------------------------------------------------------------------------

DESTINATION_FORMATS = {
    "listicle": {
        "label": "Listicle / Top N",
        "example": "5 alternative things to do in Sitges beyond the obvious",
        "format": "carousel",
        "slides": "1 cover + 1 per item + 1 CTA (visit us / save this post)",
        "caption_style": "Hook question → list with one-line descriptions → soft Noucentista mention at end",
    },
    "single_gem": {
        "label": "Single Hidden Gem",
        "example": "The Buddhist temple above Sitges that nobody talks about",
        "format": "single image or reel",
        "caption_style": "Storytelling — personal discovery tone, 'we send all our guests here'",
    },
    "seasonal_guide": {
        "label": "Seasonal / Event Guide",
        "example": "Carnival in Sitges: the insider's survival guide",
        "format": "carousel or reel",
        "caption_style": "Practical tips mixed with personality, dates and logistics",
    },
    "food_drink": {
        "label": "Food & Drink Spot",
        "example": "Where locals actually eat in Sitges (not the tourist traps)",
        "format": "single image or carousel",
        "caption_style": "Recommendation tone — what to order, when to go, insider tips",
    },
}

# ---------------------------------------------------------------------------
# Prompt for generating destination post captions
# ---------------------------------------------------------------------------

DESTINATION_CAPTION_SYSTEM = """You are a social media director for Hotel Noucentista in Sitges, Spain.
You write destination content — posts about Sitges that reach beyond hotel followers.

Your tone is:
- Insider, not tourist guide. You LIVE here. You know the hidden gems.
- Warm and personal, like recommending a spot to a friend
- Never salesy about the hotel — mention Noucentista once, naturally, at the end
- The "alternative" angle: skip the obvious, show what locals love

Format rules:
- Hook first line (question or surprising statement)
- Trilingual: write ALL THREE languages (ES, EN, FR) in every response
- Include 1 subtle hotel mention (e.g., "5 min walk from our door" or "our favorite recommendation for guests")
- End with a save/share CTA
- Hashtags: mix of Sitges-specific + travel discovery tags

Reply ONLY with a valid JSON object (no markdown, no comments)."""

DESTINATION_CAPTION_TEMPLATE = """Write Instagram captions about this Sitges destination topic.

Topic: {topic}

Photo context:
- Category: {category}
- Elements: {elements}
- Description: {description_en}

Destination context:
{destination_context}

Hotel context (for subtle mention):
{hotel_context}

Editorial context:
- Season: {season}
- Theme: {theme}

{tone_instruction}

Return this exact JSON structure:
{{
  "short": {{
    "es": "Short Spanish caption (2-3 lines, punchy, insider tone)",
    "en": "Short English caption (2-3 lines, punchy, insider tone)",
    "fr": "Short French caption (2-3 lines, punchy, insider tone)"
  }},
  "storytelling": {{
    "es": "Storytelling Spanish caption (5-6 lines, personal discovery, insider voice)",
    "en": "Storytelling English caption (5-6 lines, personal discovery, insider voice)",
    "fr": "Storytelling French caption (5-6 lines, personal discovery, insider voice)"
  }},
  "hashtags": ["20 relevant hashtags, mix of Sitges-specific + travel discovery, without #"]
}}

Remember: Sitges is the subject. Mention Hotel Noucentista once, subtly, at the end.
Include a save/share CTA naturally in each caption."""
