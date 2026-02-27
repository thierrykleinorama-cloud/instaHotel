"""
View 9 — Creative Studio
Photo-to-video generation, creative scenarios, and seasonal variants.
Test creative transforms before using them in the calendar.
"""
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


@st.cache_data(ttl=300)
def _download_raw(drive_file_id: str) -> bytes:
    return download_file_bytes(drive_file_id)


sidebar_css()
page_title("Creative Studio", "Generate videos, scenarios & seasonal variants")

st.page_link("pages/5_AI_Lab.py", label="Back to AI Lab", icon=":material/arrow_back:")

# --- Media selector (images only — source for creative transforms) ---
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

    selected_name = st.selectbox("Select", list(media_options.keys()), key="cs_select")
    media_id = media_options[selected_name]

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

    # Core tags
    _cat = media.get("category", "—")
    _subcat = media.get("subcategory", "—")
    _quality = media.get("ig_quality", "—")
    st.markdown(f"**Category:** {_cat} / {_subcat}  \n**Quality:** {_quality}/10")

    # Ambiance & season
    _ambiance = media.get("ambiance", [])
    _season = media.get("season", [])
    _amb_str = ", ".join(_ambiance) if isinstance(_ambiance, list) else str(_ambiance or "—")
    _sea_str = ", ".join(_season) if isinstance(_season, list) else str(_season or "—")
    st.markdown(f"**Ambiance:** {_amb_str}  \n**Season:** {_sea_str}")

    # Elements
    _elements = media.get("elements", [])
    if _elements:
        st.markdown(f"**Elements:** {', '.join(_elements)}")

    # Descriptions
    _desc_fr = media.get("description_fr", "")
    _desc_en = media.get("description_en", "")
    if _desc_fr:
        st.caption(f"FR: {_desc_fr}")
    if _desc_en:
        st.caption(f"EN: {_desc_en}")

    # Manual notes
    _notes = media.get("manual_notes")
    if _notes:
        st.caption(f"Notes: {_notes}")

st.divider()

# -------------------------------------------------------
# Tabs: Photo-to-Video / Creative Scenarios
# -------------------------------------------------------
tab_video, tab_scenarios = st.tabs(["Photo-to-Video", "Creative Scenarios"])

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
            "Auto (from metadata — basic)",
            "AI-generated (Claude writes a cinematic prompt — recommended)",
            "From scenario (use Creative Scenarios tab first)",
            "Manual (write your own)",
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
        # Show what will be sent to Claude
        with st.expander("View prompt sent to Claude"):
            from src.prompts.creative_transform import MOTION_PROMPT_SYSTEM, MOTION_PROMPT_TEMPLATE
            _preview_user = MOTION_PROMPT_TEMPLATE.format(
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
                    usage = ai_result["_usage"]
                    st.success(f"AI prompt generated! (${usage['cost_usd']:.4f})")
                except Exception as e:
                    st.error(f"AI prompt generation failed: {e}")
        default_prompt = st.session_state.get("cs_motion_prompt", auto_prompt)

    elif prompt_method.startswith("From scenario"):
        scenario_prompt = st.session_state.get("cs_motion_prompt")
        if scenario_prompt and scenario_prompt != auto_prompt:
            default_prompt = scenario_prompt
            st.success("Using scenario prompt loaded from Creative Scenarios tab.")
        else:
            st.warning("No scenario loaded yet. Go to the **Creative Scenarios** tab, generate ideas, and click 'Use this prompt'.")
            default_prompt = auto_prompt

    elif prompt_method.startswith("Manual"):
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
        default_prompt = auto_prompt
        st.caption(
            f"Auto-generated from metadata: ambiance ({', '.join(media.get('ambiance', []) or ['—'])}) "
            f"+ category ({media.get('category', '—')}). Edit below to improve."
        )

    # Editable prompt (always shown — user can tweak any source)
    motion_prompt = st.text_area(
        "Motion Prompt (editable)",
        value=default_prompt,
        height=120,
        key="cs_prompt_edit",
        help="This is sent to the video model. Describe camera movement + animation, NOT the static image.",
    )

    with st.expander("Negative prompt (technical — usually no need to change)"):
        neg_prompt = st.text_input(
            "Negative prompt",
            value="blurry, distorted, low quality, text overlay, watermark",
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
            except Exception as e:
                st.error(f"Video generation failed: {e}")

    # Display result
    video_result = st.session_state.get("cs_video_result")
    if video_result:
        st.video(video_result["video_bytes"])
        st.caption(f"Duration: {video_result['duration_sec']}s | AR: {video_result.get('aspect_ratio', '?')}")

        col_dl, col_music = st.columns(2)
        with col_dl:
            st.download_button(
                "Download Video",
                data=video_result["video_bytes"],
                file_name=f"{media.get('file_name', 'video').rsplit('.', 1)[0]}_reel.mp4",
                mime="video/mp4",
                key="cs_dl_video",
            )
        with col_music:
            st.page_link("pages/10_AI_Music.py", label="Add Music", icon=":material/music_note:")

# -------------------------------------------------------
# Tab 2: Creative Scenarios
# -------------------------------------------------------
with tab_scenarios:
    st.markdown("### Creative Scenario Ideas")
    st.caption(
        "Claude generates creative video concepts from your photo + hotel context. "
        "Each scenario includes a motion prompt you can use to generate the video."
    )

    hotel_context = st.text_area(
        "Hotel Context",
        value=(
            "Hotel Noucentista — Art Nouveau boutique hotel in Sitges (Barcelona). "
            "Warm Mediterranean vibe, cats live at the hotel as unofficial mascots. "
            "Guests love the rooftop terrace, the pool, and walking to the beach."
        ),
        height=80,
        key="cs_hotel_ctx",
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
                    st.session_state["cs_prompt_edit"] = s.get("motion_prompt", "")
                    st.info("Prompt loaded! Switch to the Photo-to-Video tab to generate.")
