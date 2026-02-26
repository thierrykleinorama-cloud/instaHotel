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
- [ ] **User testing**: test with real STABILITY_API_KEY + REPLICATE_API_TOKEN

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

### Phase 3b : IG Post Preview (Sem. 4)
**Goal**: Visually validate posts before pushing to Instagram.

- [ ] **Instagram Post Preview mockup**
  - Show image + selected caption as it would appear on IG feed
  - Phone frame mockup (profile pic, hotel name, image, caption, hashtags)
  - Toggle between languages (ES/EN/FR) and variants (short/storytelling)
  - New component: `app/components/ig_preview.py`
  - Displayed inside calendar list view per slot
  - "Ready to publish" confirmation after visual check

### Phase 5a : Postiz Setup + Export to Instagram (Sem. 4)
**Goal**: Get validated posts actually published on Instagram.

- [ ] **Postiz setup** (self-hosted or cloud)
  - Connect Instagram Business account
  - Test manual post creation via Postiz API
- [ ] **Export pipeline**: calendar validated slots → Postiz
  - Download image from Drive (or use enhanced version)
  - Push image + caption (selected language) + hashtags + scheduled date
  - "Publish" button per slot or batch export for a week
  - Track published status back in calendar (status → published)
- [ ] **New service**: `src/services/publisher.py` (Postiz API client)

### Phase 5b : Full Automation (Sem. 5)
**Goal**: Hands-off publishing pipeline.

- [ ] Auto-push validated slots to Postiz queue (no manual export)
- [ ] Optimal posting times (Instagram Graph API insights)
- [ ] Table: `post_performance` (engagement metrics)
- [ ] Feedback loop: pull metrics 48h after publication
- [ ] Dashboard: publication stats, best performing content
- [ ] Replicabilite multi-hotel (Malaga)

---

### >>> PRIORITY 2: Enrich content quality & variety <<<

### Phase 3c : Tone Variants (Sem. 6)
- [ ] Generate alternative caption tones: luxe, casual, humorous, romantic
- [ ] Store as additional `generated_content` candidates (same calendar_id)
- [ ] User picks best candidate → link to calendar
- [ ] New prompt templates in `src/prompts/tone_variants.py`

### Phase 2.5B : Batch Enhancement (Sem. 6)
- [ ] Batch uplift ~94 low-quality media (ig_quality < 5)
- [ ] Re-run Claude Vision, only keep if quality score increases by 2+ points
- [ ] Add DB columns: enhanced_url, enhanced_quality, enhancement_method
- [ ] Upload enhanced versions to Google Drive subfolder
- [ ] Auto-retarget: outpaint photos to 4:5 (feed) and 9:16 (story/reel)

### Phase 2.5C : Creative Transforms (Sem. 7)
- [ ] **Seasonal & Element Variants** — summer → winter, add elements, object removal
- [ ] **Photo-to-Video (AI Reels)** — Runway/Kling/Veo 3, avatar presenter, ambient audio
- [ ] **AI Humor** — creative/funny scenarios from hotel context
- [ ] **Carousel** — group related media into multi-image posts

---

## Pipeline Summary

```
FLOW TO VALIDATE FIRST:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Media Library ──► Calendar ──► AI Captions ──► IG Preview ──► Postiz ──► Instagram
      ✅              ✅            ✅           🔜 Phase 3b   🔜 Phase 5a    🎯
                                                              🔜 Phase 5b

THEN ENRICH:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: PREPROCESS          Step 2: CREATIVE TRANSFORM     Step 3: RETARGET        Step 4: CONTENT ASSEMBLY
✅ AI Retouch               🔜 Seasonal variants           ✅ Outpaint              ✅ AI Captions + CTA
✅ Upscale                  🔜 Add elements                 🔜 Story/Reel crop      ✅ IG Post Preview (3b)
🔜 Batch enhance (2.5B)     🔜 Photo-to-video              🔜 Platform adapt        🔜 Tone variants (3c)
🔜 Object removal           🔜 Avatar presenter                                     🔜 AI Humor
                            🔜 AI Humor scenarios                                   🔜 Carousel
```
