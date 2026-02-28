"""
Destination content prompts — "beyond the hotel" posts for Instagram reach.
Pillar 2: Sitges destination content (vs Pillar 1: hotel-focused).

Strategy: ~1 post per week. Angle is "alternative / hidden gems" —
NOT tourist clichés. Noucentista is mentioned naturally, never as the main subject.
"""

# ---------------------------------------------------------------------------
# Destination context — Sitges local knowledge for Claude
# ---------------------------------------------------------------------------

DESTINATION_CONTEXT = """Sitges is a cosmopolitan seaside town 35 minutes south of Barcelona on the Mediterranean coast.
Known historically as an artists' colony, it has a creative, open-minded, slightly bohemian identity.

The angle for destination posts is ALWAYS "alternative / insider / hidden gems" —
NOT the obvious tourist attractions. We position Hotel Noucentista as the insider's base
for discovering the real Sitges.

HIDDEN GEMS & ALTERNATIVE EXPERIENCES
- Hike to the Buddhist temple (Palau Novella / Garraf monastery) — stunning hilltop temple above Garraf, unexpected spiritual site
- Nudist beach of Sant Sebastià — the most beautiful and uncrowded beach, locals-only vibe
- Local vineyards: Clos Lentiscus, organic/biodynamic wines, tastings with sea views
- Cycling the coastal promenade (passeig marítim) — flat, scenic, runs from Sitges to Vilanova
- Church museum (Museu de Maricel) at sunrise — Art Nouveau collection, rooftop with sea views, almost empty early morning
- Garraf natural park — hiking trails through limestone cliffs above the sea
- Cau Ferrat museum — the house of painter Santiago Rusiñol, birthplace of Catalan modernisme
- Night swimming at Balmins beach — hidden cove between Sitges and Sant Sebastià
- Local markets: Thursday street market, daily covered market for local products
- Street art walk in the old town — murals and hidden artistic details

CAFÉS, RESTAURANTS & FOOD
- (To be enriched with owner's specific recommendations)
- Typical local dishes: fideuà, suquet de peix, coca de recapte
- Vermouth culture: pre-lunch vermouth on a terrace is a Sitges ritual
- Craft beer scene emerging
- Xató: unique Sitges salad (endive, cod, tuna, anchovies, romesco sauce) — has its own festival

SEASONAL & EVENTS
- Carnival (February): one of the biggest in Spain, extravagant, LGBTQ+-friendly
- Sitges Film Festival (October): international genre/horror film festival
- Festa Major (August 23-24): patron saint festival, fireworks, human towers (castells)
- Sant Jordi (April 23): books and roses tradition, romantic
- Corpus Christi (June): streets carpeted with flowers
- Wine harvest (September-October): vineyard visits, grape stomping
- Summer cinema on the beach
- Christmas lights along the seafront promenade

PRACTICAL LOCAL KNOWLEDGE
- Best sunset spot: the church terrace (Punta de Sitges)
- Best sunrise: Sant Sebastià beach or Terramar gardens
- The train to Barcelona runs every 20 minutes (cheaper and faster than driving)
- Sitges is very walkable — no car needed
- LGBTQ+ community is integral to Sitges identity and culture
- Quiet season (Nov-Feb) is actually lovely — mild weather, empty beaches, locals reclaim the town
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
- Trilingual: write in {language} as primary
- Include 1 subtle hotel mention (e.g., "5 min walk from our door" or "our favorite recommendation for guests")
- End with a save/share CTA
- Hashtags: mix of Sitges-specific + travel discovery tags"""

DESTINATION_CAPTION_TEMPLATE = """Write a {format_type} caption about: {topic}

Destination context:
{destination_context}

Hotel context (for subtle mention):
{hotel_context}

Language: {language}
Variant: {variant}
{additional_instructions}"""
