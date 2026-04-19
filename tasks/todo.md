# INSTA HOTEL - Task Tracking
# Version: 2.0 - 26 fevrier 2026

---

## Phase 1 : Mediatheque Intelligente (Sem. 1-2) — COMPLETE
- [x] Setup projet (repo GitHub, venv, Supabase, .env, .gitignore)
- [x] Schema DB: table media_library (25+ colonnes, triggers, indexes)
- [x] Service Google Drive (OAuth, listing recursif, download)
- [x] Modeles Pydantic (VisionAnalysis, MediaItem, SceneAnalysis)
- [x] Analyseur Claude Vision (prompt hotel, JSON parsing, validation)
- [x] Analyseur video (detection scenes OpenCV, extraction keyframes, analyse par scene)
- [x] Orchestrateur media_indexer (dedup, rate limiting, error recovery, CLI)
- [x] Indexation complete: 531/532 fichiers analyses (377 images + 155 videos)
- [x] Descriptions bilingues FR/EN pour chaque media et scene
- [x] Support HEIC via pillow-heif
- [x] Commit + push GitHub (repo prive instaHotel)

## Phase 1b : Media Library Explorer — COMPLETE
- [x] Schema: manual_notes column + tag_corrections table
- [x] Service layer: media_queries.py (cached Supabase helpers)
- [x] Service layer: caption_generator.py (Claude caption generation ES/EN/FR)
- [x] App skeleton: main.py entry point + components (ui, media_grid, tag_editor)
- [x] View 1 — Stats & Gaps: metrics, distribution charts, gap alerts
- [x] View 2 — Gallery: filterable photo grid with Drive thumbnails, pagination
- [x] View 3 — Detail: full-size image, tag correction with audit log
- [x] View 4 — Test Lab: caption generation with/without image, 2 variants x 3 languages
- [x] View 5 — Videos: video player, per-scene detail, tag correction

## Phase 2 : Moteur de Strategie Editoriale (Sem. 2-3) — COMPLETE
- [x] Tables: editorial_calendar, editorial_rules, seasonal_themes
- [x] Calendrier editorial parametrable (regles par jour, 9 slots par semaine)
- [x] Contexte saisonnier automatique (6 themes: 4 saisons + 2 evenements)
- [x] Anti-repetition intelligent (exclusion 7 jours + dedup par batch)
- [x] Selection de medias par scoring (100pts: categorie, saison, qualite, fraicheur, theme, format)
- [x] Page Calendar: vue grille + liste, generation, swap media, actions workflow
- [x] Page Rules: regles hebdo + themes saisonniers (CRUD complet)
- [x] Delete & replace bad media from calendar (swap media with top-5 candidates)

## Phase 2.5A : AI Enhancement Testing in AI Lab — COMPLETE
- [x] Multi-backend enhancement (Stability AI upscale/outpaint + Replicate Real-ESRGAN)
- [x] AI Retouch via Nano Banana Pro (Gemini 3 Pro Image)
- [x] Before/after comparison with dimensions + Claude Vision re-analysis
- [x] Download enhanced image as PNG
- [x] Session cost tracker
- [x] Outpaint padding preview
- [x] Fix max_quality slider in media_selector.py
- [→] **User testing**: → see BACKLOG

## Phase 3 : Content Assembly (Sem. 3) — COMPLETE
- [x] Table: generated_content (schema_phase3.sql — migrated)
- [x] Services: content_queries.py (CRUD), content_generator.py (bridge)
- [x] Connect captions to calendar: per-slot + batch generation
- [x] CTA selector (12 options, "Auto from theme" for batch)
- [x] Model selector (Sonnet 4.5/4.6), image inclusion toggle
- [x] Cost estimates per-slot and batch
- [x] Edit/Approve/Regenerate workflow with inline ES/EN/FR tabs
- [x] Status guide with tooltips on all actions
- [x] Expander persistence on widget interaction
- [x] AI Lab hub: 4-step pipeline overview
- [x] Reduced main content margins for wider layout

---

## UPCOMING — Ordered by priority
## Strategy: VALIDATE THE FULL FLOW FIRST, then enrich

---

### >>> PRIORITY 1: End-to-end flow (Calendar → Instagram) <<<

### Phase 3b : IG Post Preview (Sem. 4) — COMPLETE
**Goal**: Visually validate posts before pushing to Instagram.

- [x] Instagram Post Preview mockup via `app/components/ig_preview.py`
- [x] Profile header, 4:5 image (or 9:16 Reel with play overlay), action icons, caption, hashtags
- [x] Language (ES/EN/FR) + Variant selector (Short/Storytelling/Reel/Multilingual)
- [x] Displayed inside calendar list view per slot

### Phase 5a : Direct Instagram Publishing via Graph API (Sem. 4) — COMPLETE
**Goal**: Get validated posts actually published on Instagram.

- [x] **Schema migration**: `schema_phase5a_publish.sql` — ig_post_id, ig_permalink, ig_container_id, scheduled_publish_time, published_at, publish_error columns
- [x] **New service**: `src/services/publisher.py` — Instagram Graph API client + Supabase Storage upload
  - Container creation (IMAGE/REELS), polling, publishing
  - Scheduled publishing (future dates auto-queued by IG)
  - Caption resolution (single language or multilingual stacked)
  - `publish_slot()` orchestrator + `batch_publish_validated()`
  - Supabase Storage temp upload (public bucket) for IG to fetch
- [x] **Editorial queries**: `update_calendar_publish_info()`, `clear_publish_error()`
- [x] **Calendar page**: real "Publish to IG" per-slot button + batch "Schedule All Validated"
  - IG API token status indicator in sidebar
  - Variant/language/multilingual selection for publishing
  - Scheduled/published status display with IG permalink
  - Publish error display + retry support
- [x] **Prerequisites** (manual, user): Meta Developer App, FB↔IG link, long-lived token, `media-publish` Supabase Storage bucket

### Phase 5b : Full Automation (Sem. 5)
**Goal**: Hands-off publishing pipeline. → see BACKLOG

---

### >>> PRIORITY 2: Enrich content quality & variety <<<

### Phase 3c : Tone Variants (Sem. 6) — COMPLETE
- [x] 5 tones: default, luxe, casual, humorous, romantic — `src/prompts/tone_variants.py`
- [x] Tone injected into prompt + system addendum in `caption_generator.py`
- [x] Tone selector in AI Captions page sidebar
- [x] Tone selector in Calendar: batch gen + per-slot gen + per-slot regen
- [x] Stored in `generation_params.tone` JSONB via `content_generator.py`

### Phase 2.5B : Batch Enhancement (Sem. 6) → see BACKLOG

### Phase 2.5C : Creative Transforms (Sem. 7) — PARTIAL
- [x] **DB Migration**: `schema_phase3c_25c.sql` — parent_media_id, generation_method, creative_jobs table
- [x] **Photo-to-Video (Kling v2.1)** — `src/services/creative_transform.py` via Replicate
- [x] **Creative Scenarios** — Claude-generated video concepts from photos + hotel context
- [x] **Motion Prompt Generator** — auto from metadata + AI-enhanced with Claude Vision
- [x] **Music Generation (MusicGen)** — `src/services/music_generator.py` via Replicate
- [x] **Video + Audio Composite** — `src/services/video_composer.py` via FFmpeg
- [x] **AI Creative Studio page** — `app/pages/9_AI_Creative.py` (photo-to-video + scenarios)
- [x] **AI Music page** — `app/pages/10_AI_Music.py` (music gen + video composite)
- [x] **AI Lab hub updated** — new Creative Studio + AI Music cards
- [x] **Prompt quality fix**: action > camera movement, stay in frame, AI-generated as default
- [x] **Kling model ID fix**: `kwaivgi/kling-v2.1` + `start_image` param
- [x] **UI tested end-to-end** via Playwright: scenario gen + video gen + video player + download
- [→] Remaining items → see BACKLOG

### Recently Completed (2026-03-03)
- [x] **Accept/Reject UI** — Inline in Photo-to-Video + dedicated Drafts Review page (11_Drafts_Review.py)
- [x] **Pool/garden cleanup** — removed `piscine` from maps, renamed `jardin` → `patio`
- [x] **Unique Drive filenames** — timestamps appended to all uploaded media names
- [x] **Drive folder strategy** — no /rejected folder; rejected = DB flag only; all media stays in same folder

---

## BACKLOG — Single canonical list of all open work
**RULE: This is the ONE place for all TODOs. Always read this before proposing next steps.**

### V2 UI Redesign — DONE 2026-04-10
- [x] **V2 Redesign: Generate → Review → Publish** — Complete UI overhaul. Dropped calendar/scheduling. New `posts` table as central entity. New pages: Batch Generate (with content recipe from rules), Review Posts, Ready to Publish. Added "Save as Post" to Image Post, Reel, Carousel pages. `publish_post()` wrapper in publisher.py. Old pages archived to `_archive/`. Navigation: Create / Review / Publish / Media Library / Tools.

### Content Production (enable batch content creation) — LEGACY (pre-V2)
- [x] **Batch calendar creative workflow** — Generate scenarios for all calendar slots in one click → review/accept/reject via Drafts Review → generate videos → music → assemble. Long-running batch pattern. DONE 2026-03-06.
- [x] **Content type routing** — Route system replaces format: feed/carousel/reel-kling/reel-veo/reel-slideshow. Each route defines full production path. Batch Pipeline routes slots by route, no manual model selector. Rules page updated with route selectbox. Calendar shows route badges + generated content preview (video players, carousel thumbnails). DB migration: carousel_drafts gets calendar_id FK. DONE 2026-03-09.
- [x] **Production Workflow UX Redesign** — Stepper pipeline with inline review on Production Pipeline page. Gates between steps, scenarios grouped by slot with accept-one pattern, captions as final step. Calendar shows multi-step pipeline progress badges (Sc/Vid/Mus/Comp). Drafts Review renamed to Content Drafts with slot grouping toggle. Shared review component extracted to `app/components/review_controls.py`. DONE 2026-03-10.
- [x] **Pipeline UX fixes** — Rejected videos/scenarios/music no longer block regeneration. Inline review requires feedback text for rejection. Caption step only counts production-ready slots (feed always, reels after composite, veo after accepted video, carousel excluded). Calendar dot color reflects pipeline progress (green=ready, orange=in-progress, blue=has content). DONE 2026-03-10.
- [x] **Route-based tabs + 1:1 calendar status mapping** — Pipeline page rewritten with 1 tab per route (Image Posts / Carousel / Reel Kling / Reel Veo / Slideshow), each self-contained with settings + pipeline steps. Settings moved from sidebar to inline rows per tab. Shared helpers extracted (`_render_scenario_step`, `_render_video_step`, `_render_music_step`, `_render_composite_step`, `_render_caption_step`). `creative_status` now updated on accept/reject (not just batch generation). Calendar badges read `creative_status` column directly — removed 6 prefetch queries for ~6x faster Calendar page loads. Legacy status mapping for backward compat. DONE 2026-03-10.
- [x] **Pipeline + Calendar UX feedback fixes** — Accepted items show compact detail cards (thumbnail, description, video/audio player, re-reject option). "Composite" renamed to "Video + Music" everywhere. Caption step gated on prerequisite steps completion. Calendar list view re-optimized with batch fetches for content preview. Grid view shows note to switch to List for details. Re-rejection of accepted items with mandatory feedback. `is_excluded` column on `media_library` for blacklisting bad media (IMG_6738.PNG excluded). DONE 2026-03-11.
### Drafts Review UX (short-term polish) — DONE 2026-03-09
- [x] **Scenario thumbnails** — Source photo thumbnail shown next to scenario description in Drafts Review
- [x] **Carousel preview in Drafts Review** — Full IG-style carousel preview with `render_ig_preview_carousel()` inline, side-by-side with captions + hashtags
- [x] **Accept feedback** — Feedback text works on both accept and reject. Placeholder: "what's good or bad about this?"
- [x] **Clarify scenario purpose** — `:violet[Video scenario]` badge in scenario expander headers
- [x] **Rating tooltip** — Help text on rating slider: "Your quality assessment: 1 = poor, 5 = excellent. Used to improve future AI prompts."
- [x] **Video size in Drafts Review** — Constrained video player to 2/3 width for better fit on screen

- [x] **Auto-create post + captions on video generation** — Photo to Video page now auto-creates a draft post with ES/EN/FR captions + hashtags after every successful video generation. Scenario `caption_hook` used as opening line. Manual "Save as Post" section removed. DONE 2026-04-18.
- [x] **Drop Kling v2.1** — Removed from VIDEO_MODELS, replaced by Kling V3 Omni as default. Updated batch_creative.py route mapping. DONE 2026-04-18.
- [x] **Improve batch captions + wire character refs** — All batch content types now produce richer captions: feed uses description_en instead of category, carousel uses description_en, reels use scenario caption_hook + description. Character refs passed to video generation (Kling V3 Omni + Veo). Veo batch auto-forces 8s duration when chars present. Cost estimates updated. DONE 2026-04-18.
- [x] **Force duration=8s in UI when scenario has characters** — Duration slider locked to 8s with info message when Veo + characters active. DONE 2026-04-19.
- [x] **Batch retry failed posts** — `retry_failed_posts()` in batch_generator.py re-runs generation for failed posts in place. Review page has new "Failed" tab with "Retry All Failed" bulk button + per-post "Retry this post" button. Progress bar on bulk retry. DONE 2026-04-19.
- [ ] **Batch photo enhancement (Phase 2.5B)** — Bulk-enhance ~94 low-quality media (ig_quality < 5). Re-run Claude Vision, keep if +2 improvement. Add DB columns: enhanced_url, enhanced_quality, enhancement_method. Upload to `Generated/Enhanced/` in Drive. Folder already created.
- [ ] **Auto-retarget** — Outpaint photos to 4:5 (feed) and 9:16 (story/reel) in batch

### Video & Creative
- [x] **Veo 3.1 integration (B1)** — Google Veo 3.1 Fast/Standard as second video model. `veo_generator.py` service, `VIDEO_MODELS` dispatch, dedicated AI Lab page `12_Veo_Video.py`. Duration 4/6/8s, resolution 720p/1080p. Needs `GOOGLE_GENAI_API_KEY` in `.env`.
- [x] **Carousel support (B2)** — Multi-image IG posts. `carousel_drafts` DB table, `carousel_queries.py` CRUD, `publisher.py` carousel functions, `13_Carousel_Builder.py` AI Lab page with AI-assisted (theme suggestions, image selection, caption generation) + manual picker, reorder, IG preview with dots/arrows, save/publish. Optimized with paginated gallery + dict lookups.
- [x] **Persistent cost tracking** — `cost_log` DB table, `cost_tracker.py` service (`log_cost` fire-and-forget in all 8 services, 13 call sites), `14_Cost_Dashboard.py` with KPI metrics + cost-by-tool breakdown + filterable recent calls table. All API calls auto-logged: Claude, Veo, Kling, Stability AI, Replicate, MusicGen.
- [x] **Creative Scenarios on Veo page** — Added "3 Creative Scenarios" and "From scenario" prompt modes to Veo page. Generate, review, accept/reject scenarios, load prompts directly into video generation.
- [x] **End image support** — Hotel facade (IMG_6723, 9/10) auto-appended as last frame of every reel. Kling V3 Omni uses `end_image` param (tested, works). Veo `last_frame` not supported on Gemini API (Vertex-only) — logs warning and skips. `FACADE_MEDIA_ID` constant in creative_transform.py, cached after first load. DONE 2026-04-19.
- [ ] **Auto-retarget on generation** — When source photo ratio doesn't match target (4:5 for feed, 9:16 for reel), auto-outpaint via Stability AI before generating content. Should happen automatically in `batch_generator.py` and `photo_to_video()` — no manual step.
- [ ] **Translate AI prompts to English** — System/user prompt templates in `src/prompts/caption_generation.py`, `creative_transform.py`, `tone_variants.py` are in French. Move to English for better model performance. Output captions stay ES (primary) / EN / FR.
- [ ] **Separate HOTEL_CONTEXT** — Split `HOTEL_CONTEXT` in `src/prompts/creative_transform.py` into (1) hotel identity/facts (Art Nouveau, 1889, 12 rooms, cats) and (2) Instagram content strategy ideas ("show behind-the-scenes", "golden hour"). Identity used in all prompts, strategy only in scenario generation.
- [ ] **Enrich DESTINATION_CONTEXT** — Add Daniela's restaurant picks, local tips, seasonal events to `src/prompts/destination_content.py`. Currently a placeholder. Not editable from app — see Sitges KB page task.
- [ ] **Seasonal & Element Variants** — Transform existing photos to different seasons (summer terrace → winter with cozy lighting, autumn leaves). Add elements to empty scenes (guests, flowers). Uses image-to-image models. `SEASONAL_TEMPLATE` prompt exists in creative_transform.py but not wired. Task: wire to AI Enhancement page as "Seasonal Variants" tab, select photo + target season/elements, generate variant, save to media_library with parent_media_id.
- [ ] **AI Humor** — Dedicated humor scenario mode. Force all scenarios to be comedic (cats doing human things, unexpected situations, visual puns). Add "Humor Mode" toggle to Photo to Video page that changes the scenario prompt to prioritize comedy. Funny pet content performs very well on Instagram engagement.

### AI Lab Direct Publish — DONE 2026-03-11
- [x] **Standalone IG publish from AI Lab pages** — Shared `render_publish_to_ig()` component in `app/components/ig_publish.py`. Caption + hashtags input, confirmation dialog, upload → IG Graph API flow with cleanup. Added to: Veo Video (after video generation), Photo-to-Video (Tab 1 video + Tab 3 composite), Carousel Builder (reel export, replacing inline code). Credentials check shows warning if `INSTAGRAM_ACCESS_TOKEN` not configured.

### Publishing & Analytics (Phase 5b)
- [ ] **Optimal posting times** — Call IG Graph API `/media/insights` to analyze when existing posts got most engagement. Recommend best hours per day of week.
- [ ] **Post performance table** — New `post_performance` DB table. After publishing, store: impressions, reach, likes, comments, saves, shares, video views. Pulled via IG API.
- [ ] **Feedback loop** — Automated job (or manual button) that runs 48h after publication, pulls IG metrics, stores them. Feed back into media scoring — photos that perform well get higher scores, flops get deprioritized.
- [ ] **Publication dashboard** — Streamlit page: total posts published, avg engagement rate, best-performing posts, trend over time, cost-per-engagement.
- [ ] **Auto-push validated slots** — Scheduler that publishes approved posts at optimal times automatically. No manual Publish page click needed.
- [ ] **Replicabilite multi-hotel** — Malaga property support

### UX Polish (low priority)
- [ ] **Rethink Content Drafts page** — Mostly redundant now that Production Pipeline has inline review. Consider: remove entirely (AI Lab pages have their own accept/reject), or repurpose as "Prompt Improvement" page showing rejected items grouped by reason.

### Prompts & Content Quality
- [ ] **Sitges Knowledge Base page** — Streamlit admin page where Daniela can manage local knowledge (restaurants, activities, insider tips, seasonal events) without editing Python files. Stored in a Supabase table (`sitges_knowledge`). Caption generator queries this table instead of static `DESTINATION_CONTEXT` string. Benefit: Daniela updates a restaurant → captions immediately reflect it.

### Monitoring & Ops
- [ ] **API change monitor agent** — Weekly automated check of all tool providers (Replicate, Google Gemini, Stability AI, Anthropic) for new models, pricing changes, new API capabilities. Report via WhatsApp.

### Testing & Maintenance
- [ ] **Test Streamlit Cloud after deploy** — Reboot app from dashboard, verify music playback works in Drafts Review (Drive token refresh). Also check Batch Pipeline route summary + Calendar route badges.
- [ ] **User testing Phase 2.5A** — Test AI enhancement with real STABILITY_API_KEY + REPLICATE_API_TOKEN

---

## Pipeline Summary

```
FLOW TO VALIDATE FIRST:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Media Library ──► Calendar ──► AI Captions ──► IG Preview ──► IG Graph API ──► Instagram
      ✅              ✅            ✅              ✅            ✅ Phase 5a    🎯
                                                                🔜 Phase 5b (automation)

THEN ENRICH:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: PREPROCESS          Step 2: CREATIVE TRANSFORM     Step 3: RETARGET        Step 4: CONTENT ASSEMBLY
✅ AI Retouch               ✅ Photo-to-video (Kling+Veo)  ✅ Outpaint              ✅ AI Captions + CTA
✅ Upscale                  ✅ Creative scenarios (Claude)  🔜 Story/Reel crop      ✅ IG Post Preview (3b)
🔜 Batch enhance (2.5B)    ✅ Background music (MusicGen)  🔜 Platform adapt       ✅ Tone variants (3c)
🔜 Object removal          ✅ Video+Audio composite                                ✅ Carousel
                            🔜 Seasonal variants                                    🔜 AI Humor
```
