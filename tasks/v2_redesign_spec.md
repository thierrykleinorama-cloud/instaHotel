# InstaHotel V2 — UI Redesign Spec

## Problem Statement

The current app mixes **media generation** (the core value) with a **complex editorial calendar/scheduling system** that makes the whole thing hard to use. The calendar, rules, slots, routes, pipeline steps, and drafts review create cognitive overhead that blocks the real goal: **generate great Instagram content and publish it**.

## Design Principles

1. **Generation first** — the app exists to create Instagram-ready media
2. **No calendar/scheduling** — skip the editorial planning layer entirely
3. **Simple 3-step flow**: Generate → Review → Publish
4. **Each generated item is a standalone "post"** — not tied to a calendar slot

## Publishing Constraints (confirmed from code)

- **Images** (feed posts): fully automatic via Graph API
- **Reels** (video + optional music): fully automatic via Graph API
- **Carousels** (multi-image): fully automatic via Graph API (images only, 2-10 items)
- **Carousel + music**: NOT possible via API — Instagram doesn't support audio on carousels via Graph API. Music must be added manually in the Instagram app after publishing.
- **All publishing is one-by-one after user selection** — no blind batch publish

---

## Architecture: 3 Sections

### Section 1: GENERATE

Two modes of content generation:

#### A) Batch Mode ("Generate a Week of Content")
Similar to today's Pipeline but **without calendar coupling**. The user sets:
- **How many posts** to generate (e.g., 7)
- **Content mix** — distribution of post types (e.g., 3 image posts, 2 reels, 1 carousel, 1 destination post)
- **Category preferences** — weight toward chambre, exterieur, gastronomie, etc.
- **Season/theme** — current season context for prompts
- **Tone** — default, luxe, casual, humorous, romantic

The system then:
1. Selects media from the library (using existing scoring, anti-repetition)
2. For image posts: generates captions (ES/EN/FR)
3. For reels: generates scenario → video (Kling or Veo) → music → composite
4. For carousels: selects images → generates captions
5. Saves everything as **posts** (new concept, replaces calendar slots)

Each generated item lands in the **Review** section with status `draft`.

#### B) Individual Mode ("Create One Specific Post")
The existing AI Lab tools, slightly reorganized:
- **Image Post** — pick a photo, generate captions, preview
- **Reel** — pick a photo, generate/write scenario, choose model (Kling/Veo), generate video, add music, composite
- **Carousel** — pick photos (AI-assisted or manual), generate captions
- **Enhancement** — upscale, retouch, outpaint a photo before using it

Each tool saves its output as a **post** in `draft` status → appears in Review.

### Section 2: REVIEW

Single page showing all generated posts, newest first. For each post:
- **Preview** — IG-style preview (image, reel with video player, carousel with slides)
- **Captions** — ES/EN/FR tabs, editable
- **Actions**:
  - **Approve** — marks as ready to publish
  - **Discard** — with mandatory comment (for future prompt improvement)
  - **Regenerate** — re-run generation with tweaked params
  - **Edit** — modify captions, swap media

Filters: by status (draft / approved / discarded / published), by type (image / reel / carousel), by date.

### Section 3: PUBLISH

Shows only **approved** posts. For each:
- Final IG preview
- **Publish Now** button → sends to Instagram immediately
- **Status indicator** — pending / published / error
- After publish: shows IG permalink

One-by-one publishing. User picks which post to send. No batch auto-publish.

Note for carousels: if the carousel would benefit from music, show a note saying "Add music manually in Instagram after publishing."

---

## What Gets Removed / Hidden

- **Calendar page** (9_Calendar.py) — removed from main nav
- **Rules page** (10_Rules.py) — removed (no scheduling rules needed)
- **Content Drafts page** (11_Drafts_Review.py) — replaced by Review section
- **Pipeline page** (16_Batch_Creative.py) — replaced by Batch Generate
- **Prompts page** — keep but move to Settings or advanced area

## What Gets Kept

- **Media Library** (Stats, Gallery, Image Details, Video Details) — as-is, it's the source material
- **Cost Dashboard** — useful, move to a utility/settings area
- **All services** — generation, publishing, queries remain. Only the UI layer changes.
- **AI Lab individual tools** — reorganized into "Individual Mode" under Generate

## Data Model Change

New concept: **`posts`** table (or rename/repurpose `generated_content`):
- `id`, `created_at`
- `post_type`: image / reel / carousel
- `status`: draft / approved / discarded / published
- `media_id` (FK to media_library — source photo)
- `caption_es`, `caption_en`, `caption_fr`
- `hashtags`
- `tone`, `generation_params` (JSONB)
- `video_url`, `music_url`, `composite_url` (for reels)
- `carousel_images` (JSONB array of media_ids for carousels)
- `discard_reason` (text — when discarded, for prompt improvement)
- `ig_post_id`, `ig_permalink`, `published_at` (after publish)
- `generation_source`: batch / individual
- Links to existing tables: `creative_jobs.id`, `generated_music.id`, etc.

## New Navigation

```
GENERATE
  ├── Batch Generate        (new — replaces Pipeline + Calendar)
  ├── Create Image Post     (from AI Lab: caption gen)
  ├── Create Reel           (from AI Lab: photo-to-video + music)
  ├── Create Carousel       (from AI Lab: carousel builder)
  └── Enhance Photo         (from AI Lab: enhancement)

REVIEW
  └── All Posts             (new — replaces Drafts Review + Calendar review)

PUBLISH
  └── Ready to Publish      (new — replaces Calendar publish)

LIBRARY
  ├── Stats
  ├── Gallery
  ├── Image Details
  └── Video Details

SETTINGS
  ├── Cost Dashboard
  └── Prompts
```

## Migration Strategy

- **Phase 1**: Build the new UI pages (Generate/Review/Publish) using existing services
- **Phase 2**: Create `posts` table, wire up generation → posts → review → publish flow
- **Phase 3**: Remove old Calendar/Pipeline/Rules pages from navigation
- **Keep old pages** in `app/pages/archive/` temporarily for reference

## Open Questions for User

1. Should we keep the "destination" content focus as a toggle in batch mode, or just make it a category like the others?
2. For batch mode, should the system auto-decide Kling vs Veo for reels, or should the user pick?
3. Do we want to keep the editorial rules concept at all (e.g., "never post 2 gastronomie in a row") as soft constraints in batch mode?
4. The existing `generated_content` + `creative_jobs` + `carousel_drafts` tables — repurpose them or create a clean `posts` table that references them?
