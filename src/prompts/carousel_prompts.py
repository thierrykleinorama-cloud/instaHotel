"""
Prompts for AI-powered carousel generation.
- Theme suggestions from media library
- Image selection + ordering for a given theme
- Multilingual carousel captions
"""

CAROUSEL_THEME_SYSTEM = """You are the social media strategist for Hôtel Noucentista, a boutique Art Nouveau hotel in Sitges (Barcelona).
You specialize in Instagram carousel posts that drive engagement through storytelling, listicles, and visual sequences.
Respond ONLY with valid JSON (no markdown, no comments)."""

CAROUSEL_THEME_TEMPLATE = """Based on the available media library, suggest {count} carousel themes that would perform well on Instagram.

Available media summary:
- Categories: {categories}
- Total images: {total_images}
- Top elements: {top_elements}
- Seasons covered: {seasons}

Hotel context: Boutique Art Nouveau hotel in Sitges, near Barcelona. Mediterranean charm, personalized service, gastronomic experiences, beach proximity.

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

CAROUSEL_CAPTION_SYSTEM = """You are the community manager for Hôtel Noucentista, a boutique Art Nouveau hotel in Sitges (Barcelona).
You write authentic, warm, never-corporate Instagram captions. You are fluent in Spanish, English, and French.
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
