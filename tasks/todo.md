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

### Content Production (enable batch content creation)
- [ ] **Batch calendar creative workflow** — Generate scenarios for all calendar slots in one click → review/accept/reject via Drafts Review → generate videos → music → assemble. Long-running batch pattern.
- [ ] **Batch photo enhancement (Phase 2.5B)** — Bulk-enhance ~94 low-quality media (ig_quality < 5). Re-run Claude Vision, keep if +2 improvement. Add DB columns: enhanced_url, enhanced_quality, enhancement_method. Upload to `Generated/Enhanced/` in Drive. Folder already created.
- [ ] **Auto-retarget** — Outpaint photos to 4:5 (feed) and 9:16 (story/reel) in batch

### Video & Creative
- [x] **Veo 3.1 integration (B1)** — Google Veo 3.1 Fast/Standard as second video model. `veo_generator.py` service, `VIDEO_MODELS` dispatch, dedicated AI Lab page `12_Veo_Video.py`. Duration 4/6/8s, resolution 720p/1080p. Needs `GOOGLE_GENAI_API_KEY` in `.env`.
- [x] **Carousel support (B2)** — Multi-image IG posts. `carousel_drafts` DB table, `carousel_queries.py` CRUD, `publisher.py` carousel functions, `13_Carousel_Builder.py` AI Lab page with AI-assisted (theme suggestions, image selection, caption generation) + manual picker, reorder, IG preview with dots/arrows, save/publish. Optimized with paginated gallery + dict lookups.
- [x] **Persistent cost tracking** — `cost_log` DB table, `cost_tracker.py` service (`log_cost` fire-and-forget in all 8 services, 13 call sites), `14_Cost_Dashboard.py` with KPI metrics + cost-by-tool breakdown + filterable recent calls table. All API calls auto-logged: Claude, Veo, Kling, Stability AI, Replicate, MusicGen.
- [x] **Creative Scenarios on Veo page** — Added "3 Creative Scenarios" and "From scenario" prompt modes to Veo page. Generate, review, accept/reject scenarios, load prompts directly into video generation.
- [ ] **End image support** — Show hotel facade at end of Kling videos (needs `end_image` param for transitions)
- [ ] **Seasonal & Element Variants** — Transform photos to different seasons (summer → winter), add elements, object removal. Placeholder prompt exists: `SEASONAL_TEMPLATE` in creative_transform.py but not wired.
- [ ] **AI Humor** — Dedicated humor scenario mode for creative transforms

### Publishing & Analytics (Phase 5b)
- [ ] **Optimal posting times** — Instagram Graph API insights for best times to post
- [ ] **Post performance table** — `post_performance` table (engagement metrics)
- [ ] **Feedback loop** — Pull IG metrics 48h after publication, feed back into scoring
- [ ] **Publication dashboard** — Stats, best performing content, trends
- [ ] **Auto-push validated slots** — No manual export, direct queue
- [ ] **Replicabilite multi-hotel** — Malaga property support

### Prompts & Content Quality
- [ ] **Translate prompts to English** — Most prompts in `/src/prompts/` are in French (caption_generation, creative_transform, tone_variants). destination_content is already English.
- [ ] **Separate HOTEL_CONTEXT** — Split into (1) hotel identity/facts and (2) "what works on Instagram" ideas list. Currently both in `HOTEL_CONTEXT` in `src/prompts/creative_transform.py`.
- [ ] **Enrich DESTINATION_CONTEXT** — Add owner's specific restaurant recommendations, favorite spots to `src/prompts/destination_content.py` (placeholder currently)
- [ ] **Sitges Knowledge Base page** — Streamlit admin page to manage Sitges knowledge dynamically instead of static `DESTINATION_CONTEXT`

### Monitoring & Ops
- [ ] **API change monitor agent** — Weekly automated check of all tool providers (Replicate, Google Gemini, Stability AI, Anthropic) for new models, pricing changes, new API capabilities. Report via WhatsApp.

### Testing & Maintenance
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
