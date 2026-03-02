"""
View 9 — Photo to Video
Generate videos from photos, brainstorm creative scenarios, and add music.
Three tabs: Photo-to-Video / Creative Scenarios / Music.
"""
import json
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.ui import sidebar_css, page_title
from src.services.media_queries import fetch_all_media, fetch_media_by_id
from src.services.google_drive import download_file_bytes
from src.utils import encode_image_bytes
from src.services.creative_transform import (
    build_motion_prompt,
    generate_motion_prompt_ai,
    generate_scenarios,
    photo_to_video,
    VIDEO_MODELS,
    DEFAULT_VIDEO_MODEL,
)
from src.prompts.creative_transform import HOTEL_CONTEXT
from src.services.creative_job_queries import (
    save_scenario_job,
    save_video_job,
    fetch_latest_scenarios,
    fetch_video_jobs,
)
from src.services.publisher import upload_to_supabase_storage
from src.prompts.music_generation import build_music_prompt, AMBIANCE_MUSIC_MAP, CATEGORY_MUSIC_MAP
from src.services.music_generator import generate_music, MUSIC_MODELS, DEFAULT_MUSIC_MODEL
from src.services.video_composer import composite_video_audio


@st.cache_data(ttl=300)
def _download_raw(drive_file_id: str) -> bytes:
    return download_file_bytes(drive_file_id)


sidebar_css()
page_title("Photo to Video", "Generate videos, scenarios & add music")

st.page_link("pages/5_AI_Lab.py", label="Back to AI Lab", icon=":material/arrow_back:")

# --- Media selector (images only — source for creative transforms) ---
# Restore media_id from URL params (survives page reload/crash)
_qp = st.query_params
_saved_media_id = _qp.get("media_id")

with st.sidebar:
    st.subheader("Select Source Photo")

    from src.services.media_queries import fetch_distinct_values

    categories = fetch_distinct_values("category")
    sel_cats = st.multiselect("Category", categories, key="cs_cat")

    min_q = st.slider("Min quality", 1, 10, 5, key="cs_minq")
    search = st.text_input("Search filename", key="cs_search")

    all_media = fetch_all_media(media_type="image")
    if sel_cats:
        all_media = [m for m in all_media if m.get("category") in sel_cats]
    all_media = [m for m in all_media if (m.get("ig_quality") or 0) >= min_q]
    if search:
        all_media = [m for m in all_media if search.lower() in m.get("file_name", "").lower()]

    st.caption(f"{len(all_media)} images match")

    media_options = {m["file_name"]: m["id"] for m in all_media}
    if not media_options:
        st.warning("No images match filters.")
        st.stop()

    # Restore previous selection from URL if it's still in the filtered list
    _names = list(media_options.keys())
    _default_idx = 0
    if _saved_media_id:
        _id_to_name = {v: k for k, v in media_options.items()}
        if _saved_media_id in _id_to_name:
            _default_idx = _names.index(_id_to_name[_saved_media_id])

    selected_name = st.selectbox("Select", _names, index=_default_idx, key="cs_select")
    media_id = media_options[selected_name]

    # Persist selection in URL
    st.query_params["media_id"] = media_id

media = fetch_media_by_id(media_id)
if not media or not media.get("drive_file_id"):
    st.error("Media not found or no Drive file linked.")
    st.stop()

try:
    image_bytes = _download_raw(media["drive_file_id"])
except Exception as e:
    st.error(f"Could not download image: {e}")
    st.stop()

# Preview + full metadata
col_preview, col_info = st.columns([1, 2])
with col_preview:
    st.image(image_bytes, width=300)
with col_info:
    st.markdown(f"**{media.get('file_name', '')}**")

    _cat = media.get("category", "—")
    _subcat = media.get("subcategory", "—")
    _quality = media.get("ig_quality", "—")
    st.markdown(f"**Category:** {_cat} / {_subcat}  \n**Quality:** {_quality}/10")

    _ambiance = media.get("ambiance", [])
    _season = media.get("season", [])
    _amb_str = ", ".join(_ambiance) if isinstance(_ambiance, list) else str(_ambiance or "—")
    _sea_str = ", ".join(_season) if isinstance(_season, list) else str(_season or "—")
    st.markdown(f"**Ambiance:** {_amb_str}  \n**Season:** {_sea_str}")

    _elements = media.get("elements", [])
    if _elements:
        st.markdown(f"**Elements:** {', '.join(_elements)}")

    _desc_fr = media.get("description_fr", "")
    _desc_en = media.get("description_en", "")
    if _desc_fr:
        st.caption(f"FR: {_desc_fr}")
    if _desc_en:
        st.caption(f"EN: {_desc_en}")

    _notes = media.get("manual_notes")
    if _notes:
        st.caption(f"Notes: {_notes}")

st.divider()

# --- Restore previous results from DB on page load ---
if st.session_state.get("_cs_loaded_media_id") != media_id:
    st.session_state["_cs_loaded_media_id"] = media_id
    st.session_state.pop("cs_scenarios", None)
    st.session_state.pop("cs_prev_videos", None)
    st.session_state.pop("cs_video_result", None)

if "cs_scenarios" not in st.session_state:
    _saved_scenarios = fetch_latest_scenarios(media_id)
    if _saved_scenarios:
        st.session_state["cs_scenarios"] = {"scenarios": _saved_scenarios}

if "cs_prev_videos" not in st.session_state:
    st.session_state["cs_prev_videos"] = fetch_video_jobs(media_id, limit=5)

# -------------------------------------------------------
# 3 Tabs
# -------------------------------------------------------
tab_video, tab_scenarios, tab_music = st.tabs(["Photo-to-Video", "Creative Scenarios", "Music"])

# -------------------------------------------------------
# Tab 1: Photo-to-Video
# -------------------------------------------------------
with tab_video:
    st.markdown("### Generate Video from Photo")
    st.caption(
        "The video model (Kling) takes your photo + a text prompt describing "
        "**what should move and how the camera behaves**. Duration and aspect ratio "
        "are set separately in the sidebar."
    )

    with st.sidebar:
        st.divider()
        st.subheader("Video Settings")

        video_model = st.selectbox(
            "Video Model",
            list(VIDEO_MODELS.keys()),
            format_func=lambda k: VIDEO_MODELS[k]["label"],
            key="cs_vmodel",
        )

        duration = st.select_slider("Duration (sec)", [5, 10], value=5, key="cs_dur")
        aspect_ratio = st.selectbox("Aspect Ratio", ["9:16", "16:9", "1:1"], key="cs_ar")

        model_info = VIDEO_MODELS[video_model]
        cost = model_info["cost_5s"] if duration <= 5 else model_info["cost_10s"]
        st.caption(f"Estimated cost: ${cost:.2f}")

    # --- Prompt source selector ---
    st.markdown("**How to create the motion prompt:**")
    prompt_method = st.radio(
        "Prompt source",
        [
            "AI-generated (Claude writes a creative prompt — recommended)",
            "From scenario (use Creative Scenarios tab first)",
            "Manual (write your own)",
            "Auto (from metadata — basic, camera-only)",
        ],
        key="cs_prompt_method",
        label_visibility="collapsed",
    )

    auto_prompt = build_motion_prompt(media)

    if prompt_method.startswith("AI-generated"):
        st.info(
            "Claude analyzes the photo + metadata and writes a cinematic motion prompt "
            "tailored to the duration and format. You can add a creative brief to guide the style."
        )
        st.caption("Tools: **Claude Sonnet** (prompt writing) → **Kling v2.1** (video generation)")
        ai_brief = st.text_input(
            "Creative brief (optional)",
            placeholder="e.g., 'dreamy morning light', 'dramatic reveal', 'cats walking through the scene'",
            key="cs_ai_brief",
            help="Guide Claude's creative direction. Leave empty for full creative freedom.",
        )
        ai_include_photo = st.checkbox(
            "Include photo in prompt",
            value=True,
            key="cs_ai_inc_photo",
            help="Send the actual image to Claude for a richer, more accurate prompt (~$0.01 more)",
        )
        with st.expander("View prompt sent to Claude"):
            from src.prompts.creative_transform import MOTION_PROMPT_SYSTEM, MOTION_PROMPT_TEMPLATE
            _preview_user = MOTION_PROMPT_TEMPLATE.format(
                hotel_context=HOTEL_CONTEXT,
                category=media.get("category", ""),
                subcategory=media.get("subcategory", ""),
                ambiance=", ".join(media.get("ambiance", [])) if isinstance(media.get("ambiance"), list) else media.get("ambiance", ""),
                elements=", ".join(media.get("elements", [])) if isinstance(media.get("elements"), list) else media.get("elements", ""),
                description_en=media.get("description_en", ""),
                duration=duration,
                aspect_ratio=aspect_ratio,
                creative_brief=ai_brief or "Liberté créative — propose le mouvement le plus cinématique pour cette photo",
            )
            st.markdown("**System prompt:**")
            st.code(MOTION_PROMPT_SYSTEM, language=None)
            st.markdown("**User prompt:**")
            st.code(_preview_user, language=None)
            if ai_include_photo:
                st.caption("+ the photo will be attached as an image")

        if st.button("Generate AI Prompt", type="primary", key="cs_gen_prompt"):
            with st.spinner("Claude is writing a cinematic motion prompt..."):
                try:
                    b64 = encode_image_bytes(image_bytes) if ai_include_photo else None
                    ai_result = generate_motion_prompt_ai(
                        media,
                        creative_brief=ai_brief,
                        image_base64=b64,
                        duration=duration,
                        aspect_ratio=aspect_ratio,
                    )
                    st.session_state["cs_motion_prompt"] = ai_result["prompt"]
                    st.session_state["_cs_prompt_updated"] = True
                    usage = ai_result["_usage"]
                    st.success(f"AI prompt generated! (${usage['cost_usd']:.4f})")
                except Exception as e:
                    st.error(f"AI prompt generation failed: {e}")
        default_prompt = st.session_state.get("cs_motion_prompt", auto_prompt)

    elif prompt_method.startswith("From scenario"):
        st.caption("Tools: **Claude Sonnet** (scenario brainstorming) → **Kling v2.1** (video generation)")
        scenario_prompt = st.session_state.get("cs_motion_prompt")
        if scenario_prompt and scenario_prompt != auto_prompt:
            default_prompt = scenario_prompt
            st.success("Using scenario prompt loaded from Creative Scenarios tab.")
        else:
            st.warning("No scenario loaded yet. Go to the **Creative Scenarios** tab, generate ideas, and click 'Use this prompt'.")
            default_prompt = auto_prompt

    elif prompt_method.startswith("Manual"):
        st.caption("Tools: **Kling v2.1** (video generation only — you write the prompt)")
        default_prompt = st.session_state.get("cs_motion_prompt", "")
        if not default_prompt:
            st.info(
                "Describe what should happen: camera movement (pan, dolly, crane, orbit), "
                "what animates (water, curtains, light, people), and the mood. "
                "Example: *Slow dolly forward into the room, curtains sway gently in the breeze, "
                "warm golden light shifts across the bed linens.*"
            )
    else:
        # Auto
        st.caption("Tools: **Kling v2.1** (video generation only — prompt from metadata dictionary, no AI)")
        default_prompt = auto_prompt
        st.caption(
            f"Auto-generated from metadata: ambiance ({', '.join(media.get('ambiance', []) or ['—'])}) "
            f"+ category ({media.get('category', '—')}). Edit below to improve."
        )

    # Force-update widget value when a new prompt was loaded (scenario or AI),
    # otherwise initialize with the default prompt on first render
    if st.session_state.pop("_cs_prompt_updated", False):
        st.session_state["cs_prompt_edit"] = st.session_state.get("cs_motion_prompt", "")
    elif "cs_prompt_edit" not in st.session_state:
        st.session_state["cs_prompt_edit"] = default_prompt

    motion_prompt = st.text_area(
        "Motion Prompt (editable)",
        height=120,
        key="cs_prompt_edit",
        help="This is sent to the video model. Describe camera movement + animation, NOT the static image.",
    )

    with st.expander("Negative prompt (technical — usually no need to change)"):
        neg_prompt = st.text_input(
            "Negative prompt",
            value="blurry, distorted, low quality, text overlay, watermark, oversized objects, unrealistic proportions, plastic texture, AI artifacts, magical glow, sparkling effects, giant objects, miniature objects",
            key="cs_neg",
            help="Tells the model what to avoid. Standard defaults work well.",
        )

    # Generate video
    if st.button("Generate Video", type="primary", key="cs_gen_video"):
        with st.spinner(f"Generating {duration}s video... This may take 1-5 minutes."):
            try:
                result = photo_to_video(
                    image_bytes=image_bytes,
                    prompt=motion_prompt,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                    model=video_model,
                    negative_prompt=neg_prompt,
                )
                st.session_state["cs_video_result"] = result
                st.success(f"Video generated! Cost: ${result['_cost']['cost_usd']:.2f}")
                # Persist video to Storage + DB for crash recovery
                try:
                    fname = f"{media.get('file_name', 'video').rsplit('.', 1)[0]}_reel.mp4"
                    video_url = upload_to_supabase_storage(result["video_bytes"], fname, "video/mp4")
                    save_video_job(
                        source_media_id=media_id,
                        video_url=video_url,
                        prompt=motion_prompt,
                        cost_usd=result["_cost"]["cost_usd"],
                        params={"duration": duration, "aspect_ratio": aspect_ratio, "model": video_model},
                    )
                    # Refresh prev_videos list
                    st.session_state["cs_prev_videos"] = fetch_video_jobs(media_id, limit=5)
                except Exception:
                    pass  # non-critical
            except Exception as e:
                st.error(f"Video generation failed: {e}")

    # Display result
    video_result = st.session_state.get("cs_video_result")
    if video_result:
        st.video(video_result["video_bytes"])
        st.caption(f"Duration: {video_result['duration_sec']}s | AR: {video_result.get('aspect_ratio', '?')}")

        st.download_button(
            "Download Video",
            data=video_result["video_bytes"],
            file_name=f"{media.get('file_name', 'video').rsplit('.', 1)[0]}_reel.mp4",
            mime="video/mp4",
            key="cs_dl_video",
        )
        st.info("Switch to the **Music** tab to add background music to this video.")

    # Show previously generated videos from DB
    prev_videos = st.session_state.get("cs_prev_videos", [])
    if prev_videos:
        with st.expander(f"Previous videos for this photo ({len(prev_videos)})", expanded=not video_result):
            for j, vj in enumerate(prev_videos):
                params = vj.get("params", {})
                if isinstance(params, str):
                    params = json.loads(params)
                st.caption(f"**{vj.get('created_at', '?')[:16]}** | ${vj.get('cost_usd', 0):.2f}")
                if params.get("prompt"):
                    st.caption(f"Prompt: {params['prompt'][:120]}...")
                if vj.get("result_url"):
                    st.video(vj["result_url"])
                    if st.button("Use this video", key=f"cs_use_prev_{j}"):
                        try:
                            import httpx as _httpx
                            _resp = _httpx.get(vj["result_url"], timeout=60, follow_redirects=True)
                            _resp.raise_for_status()
                            st.session_state["cs_video_result"] = {
                                "video_bytes": _resp.content,
                                "duration_sec": params.get("duration", 5),
                                "aspect_ratio": params.get("aspect_ratio", "9:16"),
                            }
                            st.rerun()
                        except Exception as _e:
                            st.error(f"Could not download video: {_e}")

# -------------------------------------------------------
# Tab 2: Creative Scenarios
# -------------------------------------------------------
with tab_scenarios:
    st.markdown("### Creative Scenario Ideas")
    st.caption(
        "Claude generates creative video concepts from your photo + hotel context. "
        "Each scenario includes a motion prompt you can use to generate the video."
    )

    with st.expander("Hotel Context (click to view/edit)", expanded=False):
        hotel_context = st.text_area(
            "Hotel identity brief sent to Claude",
            value=HOTEL_CONTEXT,
            height=300,
            key="cs_hotel_ctx",
            help="Rich description of the hotel used by Claude to generate on-brand scenarios. Edit to add seasonal events, promotions, etc.",
        )

    creative_brief = st.text_input(
        "Creative brief (optional)",
        placeholder="e.g., 'cats taking over the breakfast buffet' or 'summer poolside vibes'",
        key="cs_brief",
    )

    scenario_count = st.slider("Number of scenarios", 2, 5, 3, key="cs_scenario_count")

    include_photo = st.checkbox("Include photo for richer scenarios", value=True, key="cs_inc_photo")

    if st.button("Generate Scenarios", type="primary", key="cs_gen_scenarios"):
        with st.spinner("Claude is brainstorming creative scenarios..."):
            try:
                b64 = encode_image_bytes(image_bytes) if include_photo else None
                result = generate_scenarios(
                    media=media,
                    creative_brief=creative_brief,
                    hotel_context=hotel_context,
                    count=scenario_count,
                    image_base64=b64,
                )
                st.session_state["cs_scenarios"] = result
                usage = result.get("_usage", {})
                st.caption(f"Cost: ${usage.get('cost_usd', 0):.4f}")
                # Persist to DB for crash recovery
                try:
                    save_scenario_job(
                        source_media_id=media_id,
                        scenarios=result.get("scenarios", []),
                        cost_usd=usage.get("cost_usd", 0),
                        params={"brief": creative_brief, "count": scenario_count},
                    )
                except Exception:
                    pass
            except Exception as e:
                st.error(f"Scenario generation failed: {e}")

    # Display scenarios
    scenarios = st.session_state.get("cs_scenarios", {}).get("scenarios", [])
    if scenarios:
        for i, s in enumerate(scenarios):
            with st.expander(f"{s.get('mood', '?').upper()} — {s.get('title', f'Scenario {i+1}')}", expanded=i == 0):
                st.markdown(f"**{s.get('description', '')}**")
                st.caption(f"Mood: {s.get('mood', '?')}")

                st.text_area(
                    "Motion prompt",
                    value=s.get("motion_prompt", ""),
                    height=80,
                    key=f"cs_sc_prompt_{i}",
                )

                if s.get("caption_hook"):
                    st.markdown(f"Caption hook: *{s['caption_hook']}*")

                if st.button("Use this prompt for video", key=f"cs_use_scenario_{i}"):
                    st.session_state["cs_motion_prompt"] = s.get("motion_prompt", "")
                    st.session_state["_cs_prompt_updated"] = True
                    st.info("Prompt loaded! Switch to the Photo-to-Video tab to generate.")


# -------------------------------------------------------
# Tab 3: Music
# -------------------------------------------------------
with tab_music:
    st.markdown("### Add Music to Video")
    st.caption(
        "Select a video, generate or upload background music, then merge them into a final MP4."
    )

    # ---- 1. Select Video ----
    st.markdown("**1. Select Video**")

    # Current session video (just generated in Tab 1)
    _music_video_bytes = None
    _music_video_label = None
    cs_result = st.session_state.get("cs_video_result")
    prev_videos_for_music = st.session_state.get("cs_prev_videos", [])

    if cs_result:
        _music_video_bytes = cs_result["video_bytes"]
        _music_video_label = f"Current session video ({cs_result.get('duration_sec', '?')}s)"
        st.video(_music_video_bytes)
        st.caption(_music_video_label)
    elif prev_videos_for_music:
        st.info("No video in current session. Select from previously generated videos below.")
        for j, vj in enumerate(prev_videos_for_music):
            params = vj.get("params", {})
            if isinstance(params, str):
                params = json.loads(params)
            if vj.get("result_url"):
                st.video(vj["result_url"])
                st.caption(f"{vj.get('created_at', '?')[:16]} | {params.get('prompt', '')[:80]}...")
                if st.button("Use this video", key=f"mu_use_video_{j}"):
                    try:
                        import httpx as _httpx
                        _resp = _httpx.get(vj["result_url"], timeout=60, follow_redirects=True)
                        _resp.raise_for_status()
                        st.session_state["cs_video_result"] = {
                            "video_bytes": _resp.content,
                            "duration_sec": params.get("duration", 5),
                            "aspect_ratio": params.get("aspect_ratio", "9:16"),
                        }
                        st.rerun()
                    except Exception as _e:
                        st.error(f"Could not download video: {_e}")
                break  # show first available
    else:
        st.warning("No video available. Generate one in the **Photo-to-Video** tab first.")

    st.divider()

    # ---- 2. Select Audio ----
    st.markdown("**2. Select Audio**")

    audio_source = st.radio(
        "Audio source",
        ["Generate music", "Upload audio file"],
        key="mu_audio_source",
        horizontal=True,
        label_visibility="collapsed",
    )

    audio_bytes = None
    audio_format = "wav"

    if audio_source == "Generate music":
        # Music generation settings in sidebar
        with st.sidebar:
            st.divider()
            st.subheader("Music Settings")

            music_model = st.selectbox(
                "Model",
                list(MUSIC_MODELS.keys()),
                format_func=lambda k: MUSIC_MODELS[k]["label"],
                key="mu_model",
            )

            mu_duration = st.slider("Duration (sec)", 5, 30, 10, key="mu_dur")

            temperature = st.slider(
                "Creativity", 0.5, 1.5, 1.0, step=0.1, key="mu_temp",
                help="Higher = more creative/varied, lower = more predictable",
            )

            mu_model_info = MUSIC_MODELS[music_model]
            mu_cost = mu_duration * mu_model_info["cost_per_sec"]
            st.caption(f"Estimated cost: ${mu_cost:.3f}")

        st.caption("Tools: **MusicGen (Meta)** via Replicate")

        # Quick style presets
        st.markdown("**Quick style presets:**")
        preset_cols = st.columns(4)
        presets = [
            ("Mediterranean", "Mediterranean acoustic guitar, warm breeze, relaxed cafe vibes. Instrumental only."),
            ("Jazz Lounge", "smooth jazz piano, upright bass, candlelit sophisticated ambiance. Instrumental only."),
            ("Chill Tropical", "chill tropical house, soft beat, poolside lounge vibes. Instrumental only."),
            ("Cinematic", "cinematic strings, building piano, epic reveal moment. Instrumental only."),
        ]
        for i, (label, preset_prompt) in enumerate(presets):
            with preset_cols[i]:
                if st.button(label, key=f"mu_preset_{i}", use_container_width=True):
                    st.session_state["mu_prompt"] = preset_prompt

        # Ambiance/category style reference
        with st.expander("Style reference (ambiance & category mappings)"):
            ref1, ref2 = st.columns(2)
            with ref1:
                st.markdown("**By ambiance:**")
                for k, v in AMBIANCE_MUSIC_MAP.items():
                    st.caption(f"{k} → {v}")
            with ref2:
                st.markdown("**By category:**")
                for k, v in CATEGORY_MUSIC_MAP.items():
                    st.caption(f"{k} → {v}")

        # Initialize prompt if not set
        if "mu_prompt" not in st.session_state:
            st.session_state["mu_prompt"] = presets[0][1]

        music_prompt = st.text_area(
            "Music Prompt",
            height=100,
            key="mu_prompt",
            help="Describe the style, mood, instruments. The AI generates instrumental music.",
        )

        if st.button("Generate Music", type="primary", key="mu_generate"):
            with st.spinner(f"Generating {mu_duration}s music track..."):
                try:
                    mu_result = generate_music(
                        prompt=music_prompt,
                        duration=mu_duration,
                        model=music_model,
                        temperature=temperature,
                    )
                    st.session_state["mu_result"] = mu_result
                    st.success(f"Music generated! Cost: ${mu_result['_cost']['cost_usd']:.3f}")
                except Exception as e:
                    st.error(f"Music generation failed: {e}")

        # Display generated music
        mu_result = st.session_state.get("mu_result")
        if mu_result:
            audio_bytes = mu_result["audio_bytes"]
            audio_format = mu_result["format"]
            st.audio(audio_bytes, format=f"audio/{audio_format}")
            st.caption(f"Duration: {mu_result['duration_sec']}s | Format: {audio_format}")

    else:
        # Upload audio
        uploaded_audio = st.file_uploader("Upload WAV or MP3", type=["wav", "mp3"], key="mu_upload_audio")
        if uploaded_audio:
            audio_bytes = uploaded_audio.read()
            audio_format = "mp3" if uploaded_audio.name.endswith(".mp3") else "wav"
            st.audio(audio_bytes, format=f"audio/{audio_format}")

    st.divider()

    # ---- 3. Merge + Download ----
    st.markdown("**3. Merge + Download**")

    # Also pick up audio from session if generated earlier
    if audio_bytes is None:
        mu_result = st.session_state.get("mu_result")
        if mu_result:
            audio_bytes = mu_result["audio_bytes"]
            audio_format = mu_result["format"]

    # Mix settings
    mix_c1, mix_c2 = st.columns(2)
    with mix_c1:
        volume = st.slider("Music volume", 0.0, 1.0, 0.3, step=0.05, key="mu_vol",
                           help="0.3 = subtle background, 0.7 = prominent, 1.0 = full volume")
    with mix_c2:
        fade_out = st.slider("Fade out (sec)", 0.0, 3.0, 1.5, step=0.5, key="mu_fade",
                             help="Fade out music before video ends")

    can_merge = _music_video_bytes is not None and audio_bytes is not None

    if not _music_video_bytes:
        st.caption("Missing video — generate or select one above.")
    if audio_bytes is None:
        st.caption("Missing audio — generate music or upload a file above.")

    if st.button("Merge Video + Audio", type="primary", disabled=not can_merge, key="mu_merge"):
        with st.spinner("Compositing video + audio with FFmpeg..."):
            try:
                vc_result = composite_video_audio(
                    video_bytes=_music_video_bytes,
                    audio_bytes=audio_bytes,
                    volume=volume,
                    fade_out_sec=fade_out,
                    audio_format=audio_format,
                )
                st.session_state["mu_composite_result"] = vc_result
                st.success("Video + audio merged!")
            except Exception as e:
                st.error(f"Compositing failed: {e}")

    # Display merged result
    vc_result = st.session_state.get("mu_composite_result")
    if vc_result:
        st.video(vc_result["video_bytes"])
        st.download_button(
            "Download Final Video",
            data=vc_result["video_bytes"],
            file_name=f"{media.get('file_name', 'video').rsplit('.', 1)[0]}_reel_music.mp4",
            mime="video/mp4",
            key="mu_dl_final",
        )
