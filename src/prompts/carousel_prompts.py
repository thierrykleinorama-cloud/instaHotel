"""
Prompts for AI-powered carousel generation.
- Theme suggestions from media library
- Image selection + ordering for a given theme
- Multilingual carousel captions
"""
from src.prompts.sitges_context import (
    SITGES_OVERVIEW,
    SITGES_BEACHES,
    SITGES_EVENTS,
    SITGES_GASTRONOMY,
    SITGES_CULTURE,
    CONTENT_ANGLES,
)

# Build a concise Sitges brief for carousel prompts (not the full 16K)
_SITGES_BRIEF = f"""{SITGES_OVERVIEW}

KEY CONTENT ANGLES (for carousel theme ideas):
{chr(10).join(f"- {v['label']}: {', '.join(v['examples'][:3])}" for v in CONTENT_ANGLES.values())}

NOTABLE EVENTS: Carnival (Feb), Jazz Antic (Mar), Sant Jordi (Apr), Sitges Pride (Jun),
Corpus Christi (Jun), Festa Major (Aug), Film Festival (Oct), Vendimia (Sep-Oct).

BEACHES: 19 beaches from Sant Sebastià (iconic), Garraf (painted houses), Balmins (hidden cove),
Home Mort (turquoise nudist cove) to Botigues (1.5km family beach).

GASTRONOMY: Xató (signature Sitges salad), Malvasia wine, vermouth ritual, fideuà, chiringuito culture.

CULTURE: Cau Ferrat museum (Rusiñol), Maricel museum, Modernisme architecture, gallery district.
"""

CAROUSEL_THEME_SYSTEM = f"""You are the social media strategist for Hôtel Noucentista, a boutique Art Nouveau hotel in Sitges (Barcelona).
You specialize in Instagram carousel posts that drive engagement through storytelling, listicles, and visual sequences.

SITGES CONTEXT (use this to suggest relevant, locally-informed themes):
{_SITGES_BRIEF}

Respond ONLY with valid JSON (no markdown, no comments)."""

CAROUSEL_THEME_TEMPLATE = """Based on the available media library, suggest {count} carousel themes that would perform well on Instagram.

Available media summary:
- Categories: {categories}
- Total images: {total_images}
- Top elements: {top_elements}
- Seasons covered: {seasons}

Hotel context: Boutique Art Nouveau hotel in the heart of Sitges old town (Carrer de l'Illa de Cuba). Mediterranean charm, personalized service, artistic heritage, walking distance to all beaches, museums, and restaurants.

For each theme, suggest:
1. A catchy title (for internal use)
2. A brief description of the carousel concept
3. How many slides (2-10)
4. Which media categories to pull from
5. The ordering logic (chronological, best-first, narrative arc, etc.)

Return JSON:
{{
  "themes": [
    {{
      "title": "string",
      "description": "string",
      "slide_count": number,
      "categories": ["list of category names"],
      "ordering": "string",
      "hashtag_seed": "string — 2-3 core hashtags for this theme"
    }}
  ]
}}"""

CAROUSEL_SELECT_SYSTEM = """You are an expert photo editor selecting images for an Instagram carousel post.
You must pick the best images from the available library and arrange them in the optimal viewing order.
Respond ONLY with valid JSON (no markdown, no comments)."""

CAROUSEL_SELECT_TEMPLATE = """Select the best {slide_count} images for this Instagram carousel:

Theme: {theme_title}
Description: {theme_description}
Ordering: {ordering}

Available images (id | filename | category | quality | description):
{image_list}

Selection criteria:
- Visual quality (ig_quality score)
- Relevance to theme
- Visual variety (avoid too-similar shots)
- Narrative flow when viewed in sequence
- First image must be the most eye-catching (hook slide)

Return JSON:
{{
  "selected": [
    {{
      "media_id": "uuid",
      "position": 1,
      "reason": "brief reason for selection and position"
    }}
  ],
  "carousel_title": "suggested internal title",
  "hook_note": "why the first image works as a hook"
}}"""

CAROUSEL_CAPTION_SYSTEM = f"""You are the community manager for Hôtel Noucentista, a boutique Art Nouveau hotel in Sitges (Barcelona).
You write authentic, warm, never-corporate Instagram captions. You are fluent in Spanish, English, and French.

SITGES CONTEXT (use to write locally-informed, specific captions — mention real places, events, traditions):
{_SITGES_BRIEF}

Respond ONLY with valid JSON (no markdown, no comments)."""

CAROUSEL_CAPTION_TEMPLATE = """Write Instagram carousel captions for this post:

Carousel theme: {theme_title}
Description: {theme_description}
Number of slides: {slide_count}
Image descriptions:
{image_descriptions}

Write captions that:
- Reference the carousel format ("Swipe to discover...", "Slide for more..." etc.)
- Tell a mini-story across the slides
- End with a CTA (visit link in bio, save for later, share with a friend)
- Include a natural hook in the first line

Return JSON:
{{
  "caption_es": "Full Spanish caption (3-5 lines, include carousel CTA)",
  "caption_en": "Full English caption (3-5 lines, include carousel CTA)",
  "caption_fr": "Full French caption (3-5 lines, include carousel CTA)",
  "hashtags": ["15-20 relevant hashtags without #"]
}}"""
