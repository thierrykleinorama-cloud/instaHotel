# INSTA HOTEL - Task Tracking
# Version: 1.3 - 24 fevrier 2026

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
- [x] Run: `streamlit run app/main.py`

## Phase 2 : Moteur de Strategie Editoriale (Sem. 2-3) — COMPLETE
- [x] Tables: editorial_calendar, editorial_rules, seasonal_themes
- [x] Calendrier editorial parametrable (regles par jour, 9 slots par semaine)
- [x] Contexte saisonnier automatique (6 themes: 4 saisons + 2 evenements)
- [x] Anti-repetition intelligent (exclusion 7 jours + dedup par batch)
- [x] Selection de medias par scoring (100pts: categorie, saison, qualite, fraicheur, theme, format)
- [x] Page Calendar: vue grille + liste, generation, swap media, actions workflow
- [x] Page Rules: regles hebdo + themes saisonniers (CRUD complet)
- [x] Delete & replace bad media from calendar (swap media with top-5 candidates)

## Phase 2.5A : AI Enhancement Testing in AI Lab (Sem. 3) — COMPLETE
- [x] Add httpx + replicate dependencies to requirements.txt
- [x] Create `src/services/image_enhancer.py` (Stability AI upscale/outpaint + Replicate Real-ESRGAN)
- [x] Add Enhancement tab to AI Lab (5_AI_Lab.py) with Captions/Enhancement tabs
- [x] Before/after comparison with dimensions
- [x] Re-analyze with Claude Vision + quality delta
- [x] Download enhanced image as PNG
- [x] Session cost tracker
- [x] Outpaint padding preview (computed symmetric padding)
- [x] **Fix max_quality slider**: wired into filter logic in media_selector.py
- [ ] **User testing**: test with real STABILITY_API_KEY + REPLICATE_API_TOKEN

## Phase 2.5B : Batch Enhancement (Sem. 3) — PLANNED
- [ ] **Batch uplift ~94 low-quality media (ig_quality < 5)**:
  - Script: `scripts/enhance_low_quality.py` — batch process, compare, archive originals
  - Re-run Claude Vision, only keep if quality score increases by 2+ points
  - Add DB columns: enhanced_url, enhanced_quality, enhancement_method
  - Upload enhanced versions to Google Drive subfolder
- [ ] Auto-retarget: outpaint photos to 4:5 and 9:16 for IG
- [ ] Quality enhancement: uplift ig_quality 5-6 photos (lighting, sharpness, upscale)

## Phase 2.5C : AI Generation (Sem. 3-4) — PLANNED
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
- [ ] Table: generated_content (calendar_id, media_id, captions ES/EN/FR, hashtags, status)
- [ ] **Connect captions to calendar**: wire AI Lab generation into each calendar slot
  - Each slot gets: short caption + storytelling caption + 20 hashtags, in 3 languages
  - Batch generate for a full week/month in one click
  - Store generated content linked to editorial_calendar entries
- [ ] Generation legendes Claude API (ES/EN/FR) avec contexte editorial (theme, saison, CTA)
- [ ] Hashtags optimises (mix popularite)
- [ ] **Carousel support**: group related media into multi-image posts
  - Cluster by subcategory / overlapping elements / ambiance
  - Score groups (coherence + individual quality), pick best cover image
  - New preferred_format value "carousel" in editorial_rules
- [ ] Variantes visuelles (Nano Banana Pro API)
- [ ] Reels video (Veo 3 API)

## Phase 4 : Dashboard de Validation (Sem. 4)
- [ ] Interface Streamlit de validation editoriale
- [ ] Actions: Valider / Modifier / Regenerer / Rejeter par post
- [ ] **Post preview**: mockup Instagram (image + caption + hashtags, tel que visible sur IG)
- [ ] **Delete & replace from calendar**: supprimer un media de la bibliotheque + auto-remplacement
  - Bouton "Delete image" sur chaque slot du calendrier
  - Supprime de media_library + reassigne le meilleur candidat suivant
- [ ] Metriques mediatheque (couverture, qualite moyenne, gaps)

## Phase 5 : Publication Automatique (Sem. 5)
- [ ] Table: post_performance
- [ ] **Export / scheduling**: copier le contenu (texte + media) ou connecter a l'API Meta
- [ ] Scheduling via Postiz ou SocialBee API
- [ ] Heures optimales (Instagram Graph API)
- [ ] Boucle de feedback (metrics 48h apres publication)
- [ ] Replicabilite multi-hotel (Malaga)

---
