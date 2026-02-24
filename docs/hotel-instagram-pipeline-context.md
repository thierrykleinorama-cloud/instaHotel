# Hotel Noucentista — Instagram AI Pipeline: Full Context

> **Date:** February 2026
> **Purpose:** Context document for Claude Code — covers all research, decisions, and architecture for the hotel's AI-powered Instagram content system.

---

## 1. Business Context

### The Hotel
- **Name:** Hotel Noucentista Sitges
- **Instagram:** @hotel_noucentista_sitges
- **Location:** Sitges, near Barcelona, Spain
- **Type:** Art Nouveau boutique hotel, 11 rooms
- **Revenue:** ~300K€/year
- **Current booking:** 90% via Booking.com (17% commission)
- **Objective:** Reduce acquisition cost to <10% via Instagram + SEO → target 30% direct bookings in 12 months
- **Second hotel planned in Malaga** → system must be replicable

### Instagram Audit (Current State)
- 1,229 followers, 54 posts total
- Solid art direction but dysfunctional bio
- Bad following/followers ratio (725/1,229)
- Insufficient volume, no destination content
- Potential: 5-10K followers in 12 months with optimization

### Content Strategy (Validated)
- **Editorial mix:** 30% rooms/building, 30% Sitges destination, 20% client experience, 20% direct offers
- **3 phases:** Foundations → Organic growth → Advertising
- **Posting frequency target:** ~5 posts/week (20/month), including ~8 Reels

### Owner Profile
- Technically competent, learning AI/Python
- Uses Cursor for vibe coding
- Beginner in Python and n8n
- Existing Supabase project (P&L dashboard on Streamlit Cloud)

---

## 2. Technology Research

### 2.1 AI Generation Models

#### Nano Banana Pro (Google Gemini 3 Pro Image)
- **What:** Native image generation/editing model from Google
- **Key advantage for hotel:** Upload up to 14 reference images (logo, palette, style guide) for brand consistency
- **Generates readable text** in images (multilingual EN/ES/FR)
- **Resolution:** Up to 4K
- **API Pricing:**
  - Nano Banana (Gemini 2.5 Flash Image): ~$0.039/image (1024x1024)
  - Nano Banana Pro: ~$0.134/image (2K), ~$0.24/image (4K)
- **Decision:** Replaces GPT-4o Image in architecture. Better brand consistency via multiple reference images.

#### Veo 3 / 3.1 (Google DeepMind)
- **What:** Video generation model — 8-second clips, 720p/1080p, 24fps
- **Key feature:** Native synchronized audio (dialogue, sound effects, music)
- **Capabilities:**
  - Up to 3 reference images for visual consistency between shots
  - Scene extension (videos >1 minute by chaining)
  - Interpolation between two images (smooth transitions)
  - Image-to-video with audio prompt
- **API Pricing:** Veo 3.1 Fast $0.15/sec, Standard $0.40/sec → 8s Reel = $1.20-3.20
- **Decision:** Complementary to pipeline — photos selected → Veo 3 animates → text overlay added → publish

#### Imagen 4 (Google)
- **What:** Latest Google image generation model
- **API Pricing:** Fast $0.02/image, Standard $0.04/image, Ultra $0.06/image
- **Note:** Available on ImagineArt and Google AI Studio

### 2.2 AI Text/Vision

#### Claude API (Anthropic)
- **Role in pipeline:** Photo analysis (Vision) + caption/hashtag generation
- **Model:** Claude Sonnet for cost-efficiency
- **Estimated usage:** ~200 calls/month → ~$5/month

### 2.3 Perplexity AI
- **What:** AI-augmented search engine with RAG (retrieval-augmented generation)
- **Role:** Research/monitoring tool, NOT a content creation component
- **Useful for:** Competitive intelligence, hotel marketing trends, Sitges events
- **Not part of the pipeline**

---

## 3. Tool Landscape (40+ tools researched)

### 3.1 Visual Content Creation (Images + Video)

| Tool | What it does | Pricing | Notes |
|------|-------------|---------|-------|
| **Canva** | Templates, Magic Write/Edit, direct publishing | Free generous, Pro ~$12/mo | 150M+ users, "template look" |
| **Predis.ai** | Instagram specialist, predicts performance | $27/mo | Generates carousels, videos, captions from prompt. 4.8/5 rating |
| **Picsart** | Photo/video AI editing | Freemium | 150M+ users, quick retouches |
| **Adobe Firefly/Express** | Premium AI generation + templates | Free available | Adobe ecosystem integration |
| **ImagineArt** | Multi-model hub (Imagen 4, Nano Banana, Veo 3, Sora 2, Runway, Kling) | Free: 100 tokens/day, Pro: $15/mo | Good for TESTING models, not for pipeline (no API, more expensive per image) |

### 3.2 AI Video Creation (Reels)

| Tool | What it does | Pricing | Notes |
|------|-------------|---------|-------|
| **Zebracat** | Text → social media video | Paid | Auto-selects visuals, transitions, music, voiceover |
| **OpusClip** | Long video → short clips | Paid | Detects key moments, auto-subtitles, vertical crop |
| **Lumen5** | Blog → video | $19/mo | Stock visuals + music, beginner-friendly |
| **InVideo** | Scripts → Reels | Budget-friendly | |
| **Runway ML** | Gen-3 Alpha, image → video | Higher price | Pro quality |
| **Descript** | Video editing as text editing | Paid | Removes filler words, auto-transcribe |

### 3.3 Scheduling & Publishing

| Tool | Pricing | Key Feature |
|------|---------|-------------|
| **Later** | ~$18/mo | Visual drag-and-drop, Instagram feed preview |
| **Buffer** | ~$6/mo/channel | Simplest. AI rewriting. Free: 3 channels, 10 posts |
| **SocialBee** | ~$24/mo | Category organization, AI Copilot, evergreen recycling |
| **Hootsuite** | Expensive | Enterprise. OwlyWriter AI. For agencies |
| **Metricool** | ~$18/mo | Strong analytics + competitive analysis. Free: 50 posts/mo |
| **Pallyy** | ~$18/mo | Lightweight, great mobile UX. Free: 15 posts/mo |
| **Publer** | Free tier | Calendar drag-and-drop, unlimited free scheduling |
| **Planoly** | Paid | Visual specialist Instagram/Pinterest |
| **Postiz** | Open-source OR $23/mo cloud | Self-hosted free, API complete, 19+ platforms |

### 3.4 All-in-One (Creation + Scheduling + Analytics)

| Tool | Pricing | Key Feature |
|------|---------|-------------|
| **Blaze.ai** | ~$26/mo | Analyzes website → auto-creates brand kit → generates aligned content |
| **Ocoya** | ~$15/mo | AI creation + scheduling + analytics. Entry-level |
| **Narrato** | Paid | AI Content Genie auto-generates posts weekly |
| **ContentStudio** | ~$25/mo | Content discovery + AI creation + scheduling |
| **Sprout Social** | ~$249/mo | Enterprise. Oversized for boutique hotel |

### 3.5 DM Automation & Engagement

| Tool | Pricing | Key Feature |
|------|---------|-------------|
| **ManyChat** | Free (1K contacts), Pro $15/mo | Official Meta partner. AI handles typos, recognizes intent. Essential. |
| **Chatfuel** | Paid | ManyChat alternative, simpler |

### 3.6 Complementary Tools

| Tool | What it does |
|------|-------------|
| **Flick** | Hashtag specialist + AI captions |
| **Tailwind** | Smart scheduling based on audience engagement |
| **Iconosquare** | Advanced Instagram analytics |
| **Repurpose.io** | Auto cross-posting Instagram → TikTok, YouTube Shorts, Facebook |

---

## 4. Key Decisions & Philosophy

### Aggregator (ImagineArt) vs Direct API
- **ImagineArt** is useful for **testing and comparing** models (free 100 tokens/day)
- But **~4x more expensive** per image than direct API ($0.16 vs $0.039)
- **No programmatic API** — manual only, can't integrate in pipeline
- **Decision:** Use ImagineArt to test which model works best on hotel photos, then switch to direct API

### Zebracat / OpusClip vs Custom Pipeline
- **Zebracat:** Good for text→video with stock visuals. Does NOT work from YOUR own photos. Generates generic content, not YOUR hotel.
- **OpusClip:** Cutting tool (long→short), not creation. Complementary if producing long videos.
- **Runway ML, Kling, Sora 2:** Same layer as Veo 3 — alternative generation models, not different functions.
- **Decision:** These tools are alternatives to evaluate, not replacements for the custom pipeline. The pipeline's unique value is working from YOUR media library with YOUR editorial strategy.

### Build vs Buy Philosophy
> "If an existing tool does what I need well, I use it. If too many features are missing, I develop."

**Don't build (use existing tools):**
- Scheduling/publishing → SocialBee or Postiz
- DM automation → ManyChat
- Occasional manual photo editing → Canva
- Analytics → Metricool or Iconosquare

**Build (no tool does this well):**
- The "brain" connecting everything: "I have 500 hotel photos → I know what to post, when, with what text, and it goes out automatically"
- No market tool does this from your own media library with your own editorial strategy

### Recommended Approach: Hybrid Start
1. **Week 1:** Start posting manually via SocialBee/Canva (free trial) → learn Instagram, test what works
2. **In parallel:** Test models on ImagineArt (free) to find best results on hotel photos
3. **Week 2-3:** Build first pipeline brick (media library indexer)
4. **Month 2:** Add content generation + connect to scheduler
5. **Month 3+:** Add Reels (Veo 3), ManyChat, iterate

---

## 5. Pipeline Architecture: "The Instagram Brain"

### Overview
```
[Photo/video folder] → Google Drive
    ↓
[Python Indexer] → Claude Vision analyzes + tags
    ↓
[Supabase] → Tagged media library + editorial calendar
    ↓
[Python Generator]:
  • Media selection (tag matching)
  • Nano Banana Pro → visual variants (brand identity loaded)
  • Nano Banana Pro → styled text on images
  • Veo 3.1 → animate photos into 8s Reels with audio
  • Claude → multilingual captions + hashtags
    ↓
[Streamlit Dashboard] → Human validation
    ↓
[Postiz API] → Scheduling + auto-publishing
    ↓
[Instagram Graph API] → Performance feedback loop
```

### Tech Stack
| Component | Technology | Role |
|-----------|-----------|------|
| Orchestrator | Python | Main scripts, business logic, API calls |
| Vision + Text | Claude API (Sonnet) | Photo analysis, caption generation |
| Visuals + Video | Gemini API | Nano Banana Pro (images) + Veo 3 (Reels) |
| Database | Supabase (existing project) | Media library, calendar, performance |
| Dashboard | Streamlit | Validation interface + analytics |
| Publishing | Postiz (self-hosted) | Scheduling + multi-platform publishing |
| DM Automation | ManyChat | Automated booking DMs |

### Phase 1: Intelligent Media Library (Week 1-2)

**Problem:** 500+ unorganized photos. Can't quickly know what exists, what's missing, what's been posted.

**Solution:** Python script scans photo folder → Claude Vision analyzes each image → returns structured metadata → stored in Supabase.

**Data Model:**
```sql
CREATE TABLE media_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path TEXT NOT NULL,
    file_name TEXT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT now(),
    
    -- AI-generated tags
    category TEXT,           -- chambre, commun, destination, food, experience
    subcategory TEXT,        -- chambre_deluxe, terrasse, plage_sitges...
    ambiance TEXT[],         -- [romantique, lumineux, intime]
    season TEXT[],           -- [été, hiver, toute_saison]
    elements TEXT[],         -- [mosaïque, vue_mer, balcon, fer_forgé]
    ig_quality INTEGER,      -- 1-10 Instagram quality score
    aspect_ratio TEXT,       -- portrait, landscape, square
    
    -- Usage tracking
    used_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMP,
    status TEXT DEFAULT 'available'  -- available, used, archived
);
```

**Code Example:**
```python
import anthropic
import base64
from supabase import create_client

client = anthropic.Anthropic()

def analyze_photo(image_path):
    """Analyze a photo with Claude Vision"""
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode()
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": image_data
                }},
                {"type": "text", "text": ANALYSIS_PROMPT}
            ]
        }]
    )
    return parse_tags(response)
```

### Phase 2: Editorial Strategy Engine (Week 2-3)

**Problem:** Random posting doesn't work. Need balanced content mix, seasonal adaptation, no photo repetition.

**Solution:** Configurable rules engine that decides WHAT to post and WHEN.

**Data Model:**
```sql
CREATE TABLE editorial_calendar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_date DATE NOT NULL,
    slot_type TEXT,          -- chambre, destination, experience, offre
    theme TEXT,              -- festival_sitges, été_plage...
    season_context TEXT,     -- haute_saison, basse_saison
    status TEXT DEFAULT 'planned'  -- planned, generated, validated, published
);

CREATE TABLE editorial_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    day_of_week INTEGER,    -- 1=Monday...7=Sunday
    default_category TEXT,
    frequency TEXT,          -- weekly, biweekly
    priority INTEGER
);

CREATE TABLE seasonal_themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    start_date DATE,
    end_date DATE,
    theme_name TEXT,         -- festival_cinema_sitges
    hashtags TEXT[],
    mood TEXT,               -- festif, romantique, culturel
    cta_focus TEXT           -- réservez pour le festival
);
```

**Selection Logic:**
```python
def select_next_post(post_date, slot_type):
    """Select best media for a calendar slot"""
    season = get_season_context(post_date)
    
    candidates = supabase.table("media_library") \
        .select("*") \
        .eq("category", slot_type) \
        .gte("ig_quality", 7) \
        .order("used_count", ascending=True) \
        .order("ig_quality", descending=True) \
        .limit(10) \
        .execute()
    
    # Filter by season
    if season in ["été", "hiver"]:
        candidates = [c for c in candidates 
                      if season in c["season"] 
                      or "toute_saison" in c["season"]]
    
    # Avoid recently used photos (< 30 days)
    candidates = [c for c in candidates
                  if days_since(c["last_used_at"]) > 30]
    
    return candidates[0] if candidates else None
```

### Phase 3: Content Generator (Week 3-4)

**Problem:** Need captions, hashtags, visual variants, and Reel videos from selected photos.

**Creative Flow:**
1. **You (once, at setup):** Define creative framework — brand tone, forbidden themes, style examples, allowed CTAs
2. **Editorial engine (automatic):** Decides what/when based on rules + season + usage history
3. **Claude generates everything:** Captions (ES/EN/FR), hashtags, AND Veo 3 prompts — all from seeing the actual photo + context

**Data Model:**
```sql
CREATE TABLE generated_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    calendar_id UUID REFERENCES editorial_calendar(id),
    media_id UUID REFERENCES media_library(id),
    
    caption_es TEXT,
    caption_en TEXT,
    caption_fr TEXT,
    hashtags TEXT[],
    cta_type TEXT,            -- link_bio, dm, book_now
    
    visual_variant TEXT,      -- original, text_overlay, carousel
    variant_url TEXT,
    video_url TEXT,           -- if Reel generated
    
    status TEXT DEFAULT 'draft',  -- draft, validated, published
    created_at TIMESTAMP DEFAULT now(),
    validated_at TIMESTAMP,
    validated_by TEXT
);
```

**Caption Generation:**
```python
def generate_caption(media, theme, season):
    prompt = f"""Tu es le community manager d'un 
hôtel boutique Art Nouveau à Sitges (Barcelone).

Photo : {media['elements']}
Catégorie : {media['category']}
Ambiance : {media['ambiance']}
Thème du jour : {theme}
Saison : {season}

Génère 2 variantes de légende Instagram :
- Version courte (2-3 lignes, punch)
- Version storytelling (5-6 lignes, émotionnelle)

Chaque variante en ES, EN, FR.
Inclus un CTA naturel.
Ton : chaleureux, authentique, jamais corporate.
Inclus 20 hashtags (mix popularité)."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": encode_image(media["file_path"])
                }},
                {"type": "text", "text": prompt}
            ]
        }]
    )
    return parse_captions(response)
```

### Phase 4: Validation Dashboard (Week 4)

**Problem:** AI must never publish without human approval.

**Solution:** Streamlit dashboard showing upcoming week's posts with validate/edit/regenerate/reject actions.

```python
import streamlit as st

st.title("📅 Instagram Content — Week 24")

posts = get_upcoming_posts(week=24)

for post in posts:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.image(post["photo_url"])
        st.caption(f"📊 Quality: {post['quality']}/10")
    
    with col2:
        st.subheader(f"{post['date']} — {post['theme']}")
        
        lang = st.radio("Language", ["ES","EN","FR"], key=post["id"])
        caption = post[f"caption_{lang.lower()}"]
        edited = st.text_area("Caption", caption, key=f"cap_{post['id']}")
        
        c1, c2, c3 = st.columns(3)
        if c1.button("✅ Validate", key=f"v_{post['id']}"):
            validate_post(post["id"], edited)
        if c2.button("🔄 Regenerate", key=f"r_{post['id']}"):
            regenerate_post(post["id"])
        if c3.button("❌ Reject", key=f"x_{post['id']}"):
            reject_post(post["id"])
```

### Phase 5: Auto-Publishing + Feedback Loop (Week 5)

**Solution:** Validated posts sent to Postiz API → published at optimal time → performance tracked → system learns.

**Data Model:**
```sql
CREATE TABLE post_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content_id UUID REFERENCES generated_content(id),
    ig_post_id TEXT,
    published_at TIMESTAMP,
    
    likes INTEGER,
    comments INTEGER,
    saves INTEGER,
    shares INTEGER,
    reach INTEGER,
    impressions INTEGER,
    engagement_rate FLOAT,
    
    fetched_at TIMESTAMP
);
```

**Feedback Loop:**
```python
def update_media_scoring():
    """Adjust scores based on performance"""
    perfs = supabase.table("post_performance") \
        .select("*, generated_content(media_id)") \
        .gte("published_at", thirty_days_ago) \
        .execute()
    
    for perf in perfs:
        media = get_media(perf["media_id"])
        if perf["engagement_rate"] > avg_engagement:
            boost_similar_media(
                category=media["category"],
                ambiance=media["ambiance"],
                elements=media["elements"],
                boost=+1
            )
```

---

## 6. Infrastructure & Hosting

### Architecture Overview
```
Supabase (free tier)
├── Existing P&L tables
├── NEW: media_library
├── NEW: editorial_calendar
├── NEW: generated_content
└── NEW: post_performance

Streamlit Cloud (free)
└── P&L Dashboard (existing, stays here)

Railway (~$5-10/month)
├── Python pipeline (cron jobs)
│   ├── Weekly: generate editorial calendar
│   ├── Daily: generate content for upcoming posts
│   └── Daily: fetch performance metrics
├── Postiz (self-hosted, open-source)
│   └── Scheduling + auto-publishing
└── Streamlit app (Instagram validation dashboard)
```

### Postiz: Open Source vs Paid
- **Cloud hosted (postiz.com):** $23/month for 5 channels — managed, zero setup
- **Self-hosted (GitHub):** 100% free, identical features, deploy via Docker
- **Self-hosted on Railway:** ~$5-10/month for hosting (PostgreSQL + Redis + app)
- **Decision:** Self-hosted on Railway for pipeline API integration + cost savings

### Railway (Hosting Platform)
- **What:** Modern PaaS (Platform as a Service) — the "anti-AWS"
- **How it works:** Connect GitHub repo → push code → app is live with URL in <2 minutes
- **Auto-detects:** Python, Node, etc. — configures build automatically
- **Includes:** PostgreSQL, Redis, SSL, monitoring — all one-click
- **Pricing:** Hobby plan $5/month (includes $5 usage credits) — covers small projects entirely
- **Key advantage:** Hard spending limits (rare for cloud providers), usage-based billing
- **Templates:** Hundreds of pre-built templates including Postiz (one-click deploy)

### Estimated Monthly Costs
| Component | Usage | Cost |
|-----------|-------|------|
| Claude API (Sonnet) | ~200 calls/month | ~$5 |
| Gemini API (Nano Banana Pro) | ~100 images/month | ~$4-13 |
| Gemini API (Veo 3) | ~20 videos/month | ~$25-60 |
| Supabase | Free tier | $0 |
| Streamlit Cloud | 1 app (P&L) | $0 |
| Railway | Pipeline + Postiz | ~$5-10 |
| **Total** | | **~$34-78/month** |

*vs ~$100/month for turnkey tools (SocialBee + Canva Pro + Zebracat)*
*And: replicable for Malaga at near-zero marginal cost*

---

## 7. Development Timeline

| Week | Task | Deliverable |
|------|------|------------|
| **Week 1-2** | Intelligent media library | All photos indexed in Supabase with AI tags |
| **Week 2-3** | Editorial strategy engine | Auto-generated 4-week calendar with rules |
| **Week 3-4** | Content generator | Claude captions + Nano Banana variants |
| **Week 4** | Streamlit dashboard | Validation interface + preview |
| **Week 5** | Publishing + feedback | Postiz connection + performance tracking |
| **Week 6+** | Video Reels (Veo 3) | Animated photos with audio |

**In parallel from Day 1:** Post manually via SocialBee/Canva (free trial) to not lose time during development.

---

## 8. APIs Required

### Anthropic (Claude)
- **Models:** Claude Sonnet (cost-efficient for this use case)
- **Features used:** Vision (photo analysis) + Text generation (captions)
- **SDK:** `pip install anthropic`

### Google Gemini
- **Models:** 
  - Gemini 2.5 Flash Image (Nano Banana) — fast image generation
  - Gemini 3 Pro Image (Nano Banana Pro) — premium quality
  - Veo 3.1 — video generation
- **SDK:** Google AI Python SDK
- **Note:** Need paid tier for Veo 3 API access

### Instagram Graph API
- **Used for:** Fetching post performance metrics (likes, comments, saves, reach)
- **Note:** Required for the feedback loop

### Postiz API
- **Used for:** Programmatic scheduling and publishing
- **Self-hosted:** Full REST API access

---

## 9. Key Files & Resources

### Existing Project
- Supabase project with P&L tables (already deployed)
- Streamlit P&L dashboard (on Streamlit Cloud)
- Instagram: @hotel_noucentista_sitges

### To Create
- `indexer.py` — Media library indexer (Claude Vision + Supabase)
- `editorial_engine.py` — Calendar generation with rules
- `content_generator.py` — Caption + visual generation
- `dashboard.py` — Streamlit validation interface
- `publisher.py` — Postiz API integration
- `feedback.py` — Performance tracking + scoring update
- `config.py` — Hotel-specific settings (brand voice, rules, themes)
- `docker-compose.yml` — For Postiz deployment on Railway

---

## 10. Open Questions & Next Steps

1. **Start with Phase 1:** Build the media library indexer in Cursor
2. **Test models first:** Use ImagineArt free tier to compare Nano Banana vs Flux vs Imagen 4 on actual hotel photos
3. **Evaluate:** After testing, confirm Nano Banana Pro as the best model for hotel visuals
4. **ManyChat setup:** Configure DM automation for direct booking conversion
5. **Brand kit document:** Write the creative framework (tone, style, forbidden themes) that will guide all AI generation
