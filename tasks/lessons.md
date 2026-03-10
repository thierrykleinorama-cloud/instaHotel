# INSTA HOTEL - Lessons Learned
# Fichier a mettre a jour apres chaque correction utilisateur

---

## Template de lecon
```
## Lesson YYYY-MM-DD
**Erreur** : Description de l'erreur commise
**Pattern** : Pattern recurrent a eviter
**Regle** : Nouvelle regle a appliquer
```

---

## Lessons transferees du projet Hotel P&L (patterns generaux)

## Lesson — load_dotenv et Streamlit
**Erreur** : `load_dotenv()` sans argument ne trouvait pas `.env` car Streamlit lance chaque page avec un `cwd` different.
**Regle** : Toujours charger `.env` avec un chemin absolu base sur `Path(__file__)`.

## Lesson — st.dataframe() ne rend pas le markdown
**Regle** : Ne jamais mettre de markdown dans les donnees d'un `st.dataframe()`. Utiliser du texte brut ou Unicode.

## Lesson — Playwright timing pour Streamlit
**Regle** : `page.wait_for_load_state("networkidle")` + `time.sleep(15)` minimum pour capturer les dataframes Streamlit en headless.

## Lesson — st.number_input key must include context
**Regle** : Toujours inclure le contexte dynamique dans les widget keys (ex: `f"widget_{year}"`). Utiliser `on_change` callback au lieu de comparaison de valeurs.

## Lesson — Supabase Management API returns 201
**Regle** : Checker `resp.status_code not in (200, 201)` pour les POST.

## Lesson — Streamlit module caching breaks new imports
**Regle** : Apres modification de modules importes, `kill -9` le process Streamlit + `rm -rf __pycache__`. Creer des modules self-contained quand possible.

## Lesson — Keyed disabled widgets cache values
**Regle** : Pour les champs display-only, utiliser `st.number_input(disabled=True)` SANS key.

## Lesson — Use plan mode for complex features
**Regle** : Pour les features complexes (multiples fichiers, decisions d'architecture), TOUJOURS utiliser le plan mode d'abord.

## Lesson — __pycache__ stale bytecode
**Regle** : Apres modification de modules service, toujours `find . -type d -name __pycache__ -exec rm -rf {} +` avant restart.

## Lesson — Streamlit Cloud stale module cache
**Regle** : Apres deploy de code modifiant des service modules, toujours Reboot l'app depuis le dashboard Streamlit Cloud.

## Lesson 2026-02-24 — HEIC files need pillow-heif
**Erreur** : 6 HEIC files failed with `UnidentifiedImageError` because Pillow doesn't natively decode HEIC.
**Regle** : Install `pillow-heif` and call `register_heif_opener()` before processing HEIC images.

## Lesson 2026-02-24 — Anthropic API credit balance
**Erreur** : Indexer ran out of credits at 95% (503/527), causing ~90 files to fail.
**Pattern** : Long-running batch jobs with paid APIs can exhaust credits mid-run.
**Regle** : Check credit balance before large batch runs. Use `--reindex-errors` to retry failures after topping up.

## Lesson 2026-02-24 — Video scene analysis cost
**Observation** : Videos cost ~3x more than images (multiple scenes × multiple frames per Claude call). 155 videos with ~3 scenes avg = ~465 Claude calls.
**Regle** : Budget video analysis separately from image analysis.

## Lesson 2026-02-24 — Update todo.md as you go
**Erreur** : Completed all Phase 1 steps but forgot to mark them done in `tasks/todo.md` along the way.
**Regle** : Update `tasks/todo.md` after completing each step, not just at the end. The user expects real-time progress tracking.

## Lesson 2026-02-24 — Stability AI async vs sync upscale
**Observation** : Stability AI `fast` upscale returns the image directly (sync, Accept: image/*). `conservative` and `creative` return a JSON `{id: "..."}` and require polling at `/result/{id}` with 5s intervals.
**Regle** : Always check the method type before calling Stability — sync returns image bytes, async returns JSON. Two different code paths needed.

## Lesson 2026-02-24 — Replicate input format
**Observation** : Replicate SDK expects a data URI (`data:image/png;base64,...`) for image input, not raw bytes or a file path.
**Regle** : Convert to base64 data URI when calling Replicate models. The output is a URL string that must be downloaded separately.

## Lesson 2026-02-24 — Streamlit tabs + sidebar interaction
**Observation** : Sidebar widgets can be placed inside a tab's `with` block to associate them contextually, but they still render in the sidebar globally. This works for editorial context widgets that only matter for captions.
**Regle** : For tab-specific sidebar sections, nest the sidebar `with` block inside the tab `with` block.

## Lesson 2026-02-24 — Always convert to PNG for enhancement APIs
**Observation** : Both Stability AI and Replicate expect PNG input. HEIC, JPEG, and other formats may fail or produce unexpected results.
**Regle** : Use `_ensure_png()` to convert any image format to PNG before sending to enhancement APIs. This also handles HEIC via pillow-heif.

## Lesson 2026-02-24 — Test before batch: AI Lab approach
**Observation** : Instead of building a batch enhancement script immediately, adding a testing tab to AI Lab lets the user evaluate API quality and cost manually first.
**Regle** : For new AI integrations, always build a single-image testing UI first. Batch processing comes after the user validates the approach.

## Lesson 2026-02-25 — Test before user
**Erreur** : Asked user to test outpaint multiple times with back-and-forth debugging instead of testing myself first.
**Regle** : Always test changes yourself first: 1) Python script on the actual image, 2) Playwright browser check. Save outputs with meaningful names (e.g. `IMG_4176_Outpaint_9_16.png`) in `test_outputs/`. Only ask user to test after confirming it works.

## Lesson 2026-02-25 — Stability AI outpaint parameter names
**Erreur** : Used `top`/`bottom` for padding but API expects `up`/`bottom`/`left`/`right` (inconsistent naming).
**Regle** : Stability AI outpaint uses `up` (not `top`), but keeps `bottom` as-is. Always check actual API error messages for parameter names.

## Lesson 2026-02-25 — Streamlit caches imported modules
**Erreur** : Changed service files but Streamlit kept serving old code despite clearing `__pycache__`.
**Regle** : Streamlit hot-reloads page files but keeps service modules cached in the Python process. Must `taskkill //F //IM streamlit.exe` and restart — `pkill` may not kill all instances on Windows/MINGW.

## Lesson 2026-02-28 — Replicate model IDs change over time
**Erreur** : Hardcoded `kwaivgi/kling-v2.1-image-to-video` but the actual model ID is `kwaivgi/kling-v2.1`. Got 404 errors.
**Regle** : Always verify model IDs with `client.models.get()` or `client.models.search()` before hardcoding. Model IDs and input param names can change without notice.

## Lesson 2026-02-28 — Video prompts: action > camera movement
**Erreur** : Initial prompts described only camera movement ("slow dolly forward", "gentle pan") → boring unusable videos (just a zoom on a static image).
**Pattern** : The video model (Kling) needs concrete ACTION to animate. Camera-only prompts produce near-static output.
**Regle** : Video prompts MUST describe what HAPPENS (cat jumping, person entering, wind blowing, objects falling) — not just camera movement. Update system prompts to enforce this.

## Lesson 2026-02-28 — Stay in frame for video generation
**Erreur** : Prompts asking for pullback/crane-up to "reveal the hotel" caused Kling to hallucinate random buildings.
**Regle** : Never ask the video model to reveal areas outside the original photo. Keep all action within the visible frame. Use `end_image` param if you need to show a specific destination.

## Lesson 2026-02-28 — Replicate rate limiting with low credit
**Erreur** : Launched 3 video generations in parallel but got 429 (rate limited — burst of 1 with < $5 credit).
**Regle** : With low Replicate credit, submit predictions sequentially with 15s delays between each.

## Lesson 2026-02-28 — Always restart Streamlit after code changes
**Erreur** : Fixed model ID in service but Streamlit UI still used old code (module cached in memory). UI returned 404, API worked fine.
**Regle** : After changing service/prompt files, ALWAYS kill and restart Streamlit before testing the UI.

## Lesson 2026-02-28 — Test via UI, not just API
**Erreur** : Tested video generation via Python API only. When user tested the UI, it failed (stale module cache + wrong model ID).
**Regle** : Always test through the actual Streamlit UI (via Playwright or manual) after code changes, not just via Python scripts.

## Lesson 2026-03-09 — Route system replaces format
**Erreur** : `preferred_format` held simple values (feed/story/reel) but the batch pipeline needed to know both the content type AND the production model (Kling vs Veo).
**Pattern** : A single "route" value (e.g. `reel-kling`, `reel-veo`) fully defines the production path, eliminating ambiguity.
**Regle** : Use route = full production path. No separate model selector needed — the route determines everything. Always handle legacy values (`reel` → `reel-kling`, `story` → `feed`).

## Lesson 2026-03-09 — Veo skips music+composite
**Observation** : Veo 3.1 generates video with native audio. Adding MusicGen + FFmpeg composite would overwrite the native audio and add unnecessary cost.
**Regle** : Route determines which pipeline steps apply. `reel-veo` = scenario → video → done. `reel-kling` + `reel-slideshow` = need music + composite.

## Lesson 2026-03-09 — Batch fetch before per-slot loop
**Erreur** : Early batch code fetched scenarios/videos per-slot in a loop = N+1 queries.
**Regle** : Always `fetch_*_for_calendar_ids(all_ids)` once before the loop, then look up from the dict. Critical for performance with 20+ slots.

## Lesson 2026-03-09 — Keep memory files synchronized
**Erreur** : MEMORY.md, architecture.md, and tasks/todo.md drifted apart — services/pages added without updating architecture, completed items not reflected in MEMORY status.
**Regle** : When completing a feature, update ALL 3: (1) `tasks/todo.md` BACKLOG (mark done), (2) MEMORY.md status section, (3) architecture.md if new files/services were added. Do it incrementally, not at end of session.

---

## Regles du projet
1. **Simplicity First** : Quand la logique devient complexe, preferer le code Python clair
2. **Performance** : Minimiser les appels DB, batch fetch, pas de N+1
3. **Plan mode** : Pour les features non triviales, planifier avant d'implementer
4. **Memory sync** : Update todo.md + MEMORY.md + architecture.md together when completing features
5. **Route = path** : Content type routing defines full production pipeline per slot
6. **Stepper > flat buttons** : Multi-step pipelines work better as guided steppers with gates (disabled buttons + messages when prereqs not met) than flat button grids
7. **Inline review > page bounce** : Reviewing content on the same page where it's generated eliminates page switching. Accept-one pattern (accept variant A, auto-reject B/C) reduces decisions
8. **Extract shared components** : When the same widget (review controls) appears in multiple pages, extract to `app/components/` — keeps behavior consistent and code DRY
9. **Group by slot** : Flat lists of scenarios/videos are meaningless without slot context. Always group creative items by their calendar slot for user clarity
10. **Rejected ≠ processed** : When checking "already processed" in batch operations, ALWAYS filter out rejected items. `status != "rejected"` is the correct check. A rejected video should be regeneratable, not treated as done.
11. **Smart caption gating** : Don't offer to generate captions for ALL slots — only slots whose creative pipeline is complete (feed=always, reel=after composite, veo=after accepted video, carousel=skip because captions come with carousel generation)
12. **Pipeline color > editorial status** : The dot color in Calendar should reflect pipeline progress (green=production-ready, orange=in-progress), not just the editorial status (planned/generated). Users see "all blue" otherwise.
