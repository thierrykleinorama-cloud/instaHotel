# INSTA HOTEL - Task Tracking
# Version: 1.2 - 24 fevrier 2026

---

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
- [x] Run: `streamlit run app/main.py`

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

## Phase 2 : Moteur de Strategie Editoriale (Sem. 2-3)
- [ ] Tables: editorial_calendar, editorial_rules, seasonal_themes
- [ ] Calendrier editorial parametrable (regles par jour)
- [ ] Contexte saisonnier automatique
- [ ] Anti-repetition intelligent
- [ ] Selection de medias par scoring

## Phase 2.5 : AI Media Enhancement & Generation (Sem. 3)
### Direction A: Enhance/Modify existing photos
- [ ] **AI quality uplift for ~94 low-quality media (ig_quality < 5)**:
  - Use AI upscaling/enhancement (Real-ESRGAN, Topaz Photo AI API, or Stability AI)
  - Auto-enhance lighting, sharpness, contrast
  - Before/after comparison: re-run Claude Vision on enhanced version to verify ig_quality improved
  - Only keep enhanced version if quality score increases by 2+ points
  - Script: `scripts/enhance_low_quality.py` — batch process, compare, archive originals
- [ ] Auto-retarget: outpaint photos to 4:5 and 9:16 for IG (Stability AI / DALL-E)
- [ ] Quality enhancement: uplift ig_quality 5-6 photos (lighting, sharpness, upscale)
- [ ] Seasonal variants: generate autumn/winter versions of summer shots
- [ ] Object removal: clean up distracting elements (inpainting)
- [ ] Consistent brand style across all enhanced media
### Direction B: Generate video from photos (AI Reels)
- [ ] Photo-to-video: animate static photos with camera motion (Runway Gen-4 / Kling / Veo 3)
- [ ] Add characters: generate people in hotel scenes (guest sipping coffee, walking through lobby)
- [ ] Ambient audio: add sound/music to generated clips
- [ ] Assemble Reels: combine multiple generated clips into 15-30s Reels
- [ ] Avatar presenter: hotel owner intro/outro via HeyGen

## Phase 3 : Generateur de Contenu (Sem. 3-4)
- [ ] Table: generated_content
- [ ] Generation legendes Claude API (ES/EN/FR)
- [ ] Hashtags optimises (mix popularite)
- [ ] Variantes visuelles (Nano Banana Pro API)
- [ ] Reels video (Veo 3 API)

## Phase 4 : Dashboard de Validation (Sem. 4)
- [ ] Interface Streamlit
- [ ] Actions: Valider / Modifier / Regenerer / Rejeter
- [ ] Preview Instagram
- [ ] Metriques mediatheque

## Phase 5 : Publication Automatique (Sem. 5)
- [ ] Table: post_performance
- [ ] Scheduling via Postiz ou SocialBee API
- [ ] Heures optimales (Instagram Graph API)
- [ ] Boucle de feedback (metrics 48h apres publication)
- [ ] Replicabilite multi-hotel (Malaga)

---
