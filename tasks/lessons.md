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

## Lesson 2026-04-10 — media_library column is file_name not filename
**Erreur** : Review page crashed with `column media_library.filename does not exist`.
**Regle** : The `media_library` table uses `file_name` (with underscore), not `filename`. Always check DB column names before writing queries.

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
13. **Single-column status > N queries** : Reading pipeline progress from a single `creative_status` column is ~6x faster than fetching from 6 creative tables. The column acts as a state machine: each accept/reject/batch action advances it. Legacy values map to new ones.
14. **Route tabs > monolithic page** : When a page serves N content types with different pipelines, use `st.tabs()` with 1 tab per route. Each tab is self-contained (settings + steps), reducing cognitive load. Shared step helpers (`_render_scenario_step`, etc.) avoid duplication across similar routes.
15. **Accepted items must be inspectable** : Never collapse an accepted item to a one-liner badge. Users need to SEE what was accepted — show thumbnail, description, video/audio player. A compact card (thumbnail + title + key details) is the minimum.
16. **Rename technical jargon** : User-facing labels must be understandable without context. "Composite" → "Video + Music". "Scenario" needs `:violet[Video scenario]` badge. Never assume the user knows internal pipeline terminology.
17. **Gate steps on previous completion** : Each pipeline step must check that its prerequisite step succeeded. Show a clear message ("N slots not ready — complete previous steps first") rather than silently including incomplete slots.
18. **Streamlit expanders execute even when collapsed** : ALL code inside `st.expander()` runs on every page load regardless of open/closed state. Never put per-item DB queries inside expanders in a loop — batch fetch BEFORE the loop, then look up from a dict inside the expander.
19. **Status changes must be reversible** : Users must be able to reject a previously accepted item. Show a compact reject option alongside the ACCEPTED badge, requiring feedback text to proceed.
20. **Media exclusion > deletion** : Bad images (screenshots, off-brand content) should be excluded via `is_excluded` flag, not deleted. Excluded media is filtered from all queries (gallery, calendar, selectors) but data is preserved.
21. **Tab counts = remaining work** : Tab labels like "Image Posts (32)" mean "32 things to do" to the user. Show remaining/total (e.g. "2/4") or add a checkmark when done ("(32) ✔"). Never show total-as-label when it could mean "pending".
22. **Name the slot, not just the count** : "1 need review" is useless. Always show WHICH slot: "Review needed: Thu 26/03 S1 | experience". Users need actionable context, not abstract counts.
23. **Rejected = regeneratable** : After rejecting all items for a slot, show a clear message ("All videos rejected: [slot labels]") with instruction to regenerate. The Generate button already handles this (rejected items are treated as unprocessed) but the user needs to SEE the path forward.
24. **Pipeline → Calendar handoff** : The Production Pipeline generates content. The Calendar validates and publishes. Always show a clear "What's next → Go to Calendar" when pipeline work is complete. Users don't know the page flow.
25. **Extract shared IG publish logic** : When multiple pages need the same upload → container → poll → publish flow, extract it into a shared component (`app/components/ig_publish.py`) instead of duplicating the IG Graph API calls inline. The component handles credentials check, caption input, confirmation, upload to Supabase Storage, IG container lifecycle, cleanup — all with unique widget keys via `key_prefix`.
26. **Test API calls yourself before user tests** : When integrating a new API feature (e.g. Veo reference_images), write a throwaway test script and run it BEFORE wiring into the UI. Discovered 3 hidden constraints (duration=8, no negative_prompt, no image= with refs) that would have wasted the user's time and credits. The SDK declaring types/params does NOT mean the API endpoint accepts them — always verify empirically.
27. **Read the actual docs before declaring "doesn't work"** : Veo reference_images DO work on Gemini API — first test failures were caused by wrong duration (4s instead of required 8s). Fetching the docs page (ai.google.dev/gemini-api/docs/video) immediately revealed the constraint. User correctly pushed back. Don't conclude "unsupported" from a 400 error — investigate the specific constraint.

## Lesson 2026-05-16 — Supabase OAuth PKCE in Streamlit
**Erreur** : `sign_in_with_oauth()` is called on every Streamlit rerun, regenerating the `code_verifier` / `code_challenge` pair. By the time the user returns from Google, the stored verifier no longer matches the challenge in the URL — exchange fails silently.
**Regle** : Generate the OAuth URL + verifier ONCE per login attempt and cache them in `st.cache_resource`. Restore the verifier into the client's `_storage` before calling `exchange_code_for_session()`. After exchange (success or fail), clear the cache so the next login gets a fresh pair. See `src/auth.py`.

## Lesson 2026-05-16 — Supabase Site URL is the silent OAuth fallback
**Regle** : If `redirect_to` in the OAuth URL is not in the Supabase project's allowlist (Auth → URL Configuration → Redirect URLs), Supabase falls back to the **Site URL** without warning. Symptom: user logs in via Google and lands on the wrong app. Always add every `APP_URL` (local + every Streamlit Cloud URL) to the Redirect URLs allowlist.

## Lesson 2026-05-16 — `st.navigation` must be declared on the login screen too
**Erreur** : Adding `if not check_auth(): login_form(); st.stop()` BEFORE calling `st.navigation(...)` causes Streamlit's file-based page discovery to kick in and leak the entire `app/pages/` listing into the sidebar of the unauthenticated login screen.
**Regle** : When gating a multi-page app, wrap the login form in its own `st.navigation([st.Page(login_fn, title="Sign in")]).run()` before `st.stop()`. That suppresses the auto-discovered pages/ list.

## Lesson 2026-05-16 — Supabase client must use PKCE for browser OAuth
**Regle** : `create_client(url, key)` defaults to the implicit flow, which can't run in a server-rendered Streamlit app. Pass `ClientOptions(flow_type="pkce")` so `exchange_code_for_session()` works. Apply this in `src/database.py` even if other modules only do reads — auth piggybacks on the same singleton.

## Lesson 2026-05-16 — Streamlit Cloud wraps the app in a `/~/+/` iframe
**Erreur** : Playwright tests against `*.streamlit.app` URLs returned empty bodies / missing selectors even though screenshots clearly showed the app rendered. Symptom: `pg.locator(...)`, `pg.content()`, and `body.inner_text()` all returned nothing, but the visual screenshot was correct.
**Regle** : Streamlit Cloud serves the actual app DOM inside a sandboxed iframe at `https://<app>.streamlit.app/~/+/`. The top-level page is just Cloud chrome (Fork, GitHub, status badge). Iterate `pg.frames` and call `f.evaluate("() => document.querySelectorAll(...)")` inside the target frame instead of using top-level locators. Browsers render iframes natively, which is why screenshots looked fine. Only matters for deployed apps — local `streamlit run` has no iframe wrapping.

## Lesson 2026-05-16 — Streamlit Cloud secrets are TOML — section headers swallow following keys
**Erreur** : `APP_URL` defined in Cloud secrets but `st.secrets.get("APP_URL")` returned `None`. OAuth then silently fell back to `localhost:8501`. Cause: the secrets editor is parsed as TOML, so any key written BELOW a `[section]` header (e.g. `[gcp_service_account]`) becomes a sub-key of that section — `st.secrets["gcp_service_account"]["APP_URL"]`, not `st.secrets["APP_URL"]`.
**Regle** : Top-level secrets MUST appear at the very top of the editor, BEFORE any `[section]` header. The order in the Cloud secrets editor matters even though regular Python dicts don't care. Rule of thumb: scalar keys first, sections last.

## Lesson 2026-05-16 — `st.cache_resource` survives Streamlit Cloud secret changes
**Erreur** : After adding `APP_URL` to Streamlit Cloud secrets, the OAuth `redirect_to` still pointed at `localhost:8501`. The `oauth_url` was built once on first login render and stored in a `@st.cache_resource`-backed dict — that cache survives until the container restarts.
**Regle** : Any value derived from `st.secrets` and stored in `st.cache_resource` will NOT pick up secret changes until you reboot the app from the Cloud dashboard (⋮ → Reboot app). Hot reload only re-runs Python source on file changes, not secret changes.

## Lesson 2026-05-17 — supabase-py ClientOptions: import from package root, not lib path
**Erreur** : A sibling project (hotelPandL) used `from supabase.lib.client_options import ClientOptions` and got `AttributeError: 'ClientOptions' object has no attribute 'storage'` on `create_client(...)`. They monkey-patched the missing fields before tracing the real cause.
**Pattern** : `supabase.lib.client_options` defines both a base `ClientOptions` (missing `storage`/`httpx_client`) and a subclass `SyncClientOptions` (has them). The package-level export `from supabase import ClientOptions` resolves to `SyncClientOptions`. Importing from the `lib` submodule grabs the base class and breaks `Client.__init__`.
**Regle** : Always `from supabase import ClientOptions` (never from `supabase.lib.*`). Verify: `supabase.ClientOptions is supabase.lib.client_options.SyncClientOptions` should be True. InstaHotel's current `src/database.py` already uses the safe import — preserve that on any future refactor.

## Lesson 2026-05-17 — Local OAuth port must match `.env` APP_URL
**Erreur** : Locally, `.env`'s `APP_URL=http://localhost:8501` but stale Streamlit held 8501, so a fresh `streamlit run` fell back to 8502. OAuth URL was generated with `redirect_to=8501`, Google redirected to 8501 (stale process with no matching verifier), surfaced as "code challenge does not match" — a downstream symptom that masked the real port mismatch.
**Pattern** : When OAuth verifier errors appear, the root cause is often the port the live process is on doesn't match the `redirect_to` baked into the OAuth URL.
**Regle** : Right-click "Sign in with Google" → copy link → check the `redirect_to` query param matches the actual running port. If a stale Streamlit holds the desired port, kill that PID first (don't switch ports), so `.env`'s APP_URL stays consistent across local + prod.

## Lesson 2026-05-17 — Avast IDP.HELU.PSD11 false-flags Chrome + CDP automation
**Erreur** : Driving debug Chrome (launched with `--remote-debugging-port=9222`) via Playwright triggered Avast's IDP behavioral engine — `IDP.HELU.PSD11` alert — and blocked the process mid-session. Avast pattern-matches "browser launched with remote debugging + external automation hammering it via CDP" as info-stealer behavior; it doesn't care that the binary is unmodified Chrome.exe.
**Pattern** : Same Avast environment that broke pip + Python HTTPS (`pip-system-certs` lesson) has multiple shields hostile to dev automation.
**Regle** : Add Avast exceptions for: `chrome.exe`, the DebugProfile directory, AND the `python.exe` driving Playwright. Targeted exceptions are safer than disabling Behavior Shield wholesale.

## Lesson 2026-05-16 — Avast TLS interception breaks Python HTTPS on Windows
**Erreur** : All Supabase calls from Python (reads AND auth) failed with `[SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate`. Even passing `verify=certifi.where()` to httpx failed. Cause: Avast Web/Mail Shield does TLS interception and re-signs every HTTPS connection with its own root CA — browsers trust it via Windows cert store, but Python's bundled `certifi` does not. Diagnosed by inspecting the peer cert: `Issuer: CN=Avast Web/Mail Shield Root`.
**Regle** : Pin `pip-system-certs>=5.3` in `requirements.txt`. It monkey-patches ssl/urllib3/httpx to use the Windows cert store on import. Zero code changes needed; harmless on Linux (Streamlit Cloud). Without this, no Python code in the venv can talk to Supabase / Anthropic / any HTTPS endpoint on the dev machine.
