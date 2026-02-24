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

---

## Regles du projet
1. **Simplicity First** : Quand la logique devient complexe, preferer le code Python clair
2. **Performance** : Minimiser les appels DB, batch fetch, pas de N+1
3. **Plan mode** : Pour les features non triviales, planifier avant d'implementer
