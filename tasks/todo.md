# INSTA HOTEL - Task Tracking
# Version: 1.0 - 23 fevrier 2026

---

## Phase 1 : Mediatheque Intelligente (Sem. 1-2)
- [ ] Setup projet (repo, Supabase, .env)
- [ ] Schema DB: table media_library
- [ ] Script indexeur photos (Claude Vision / Gemini Vision)
- [ ] Tagging multi-niveaux (categorie, ambiance, saison, qualite)
- [ ] Stockage metadonnees Supabase

## Phase 2 : Moteur de Strategie Editoriale (Sem. 2-3)
- [ ] Tables: editorial_calendar, editorial_rules, seasonal_themes
- [ ] Calendrier editorial parametrable (regles par jour)
- [ ] Contexte saisonnier automatique
- [ ] Anti-repetition intelligent
- [ ] Selection de medias par scoring

## Phase 2.5 : AI Media Enhancement & Generation (Sem. 3)
### Direction A: Enhance/Modify existing photos
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
