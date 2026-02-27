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

# Preview
col_preview, col_info = st.columns([1, 2])
with col_preview:
    st.image(image_bytes, width=300)
with col_info:
    st.markdown(f"**{media.get('file_name', '')}**")
    st.caption(f"Category: {media.get('category')} | Quality: {media.get('ig_quality')}")
    st.text(media.get("description_en", ""))

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

        use_ai_prompt = st.checkbox("Generate prompt with AI", value=False, key="cs_ai_prompt",
                                    help="Use Claude to write a cinematic motion prompt from the photo")

        model_info = VIDEO_MODELS[video_model]
        cost = model_info["cost_5s"] if duration <= 5 else model_info["cost_10s"]
        st.caption(f"Estimated cost: ${cost:.2f}")

    # Auto-generate motion prompt from metadata
    auto_prompt = build_motion_prompt(media)

    # AI prompt generation
    if use_ai_prompt:
        if st.button("Generate AI Prompt", key="cs_gen_prompt"):
            with st.spinner("Claude is writing a motion prompt..."):
                try:
                    b64 = encode_image_bytes(image_bytes)
                    ai_result = generate_motion_prompt_ai(media, image_base64=b64)
                    st.session_state["cs_motion_prompt"] = ai_result["prompt"]
                    usage = ai_result["_usage"]
                    st.caption(f"Prompt cost: ${usage['cost_usd']:.4f}")
                except Exception as e:
                    st.error(f"AI prompt generation failed: {e}")

    # Editable prompt
    default_prompt = st.session_state.get("cs_motion_prompt", auto_prompt)
    motion_prompt = st.text_area(
        "Motion Prompt",
        value=default_prompt,
        height=120,
        key="cs_prompt_edit",
        help="Describe the camera movement and animation. Auto-filled from metadata.",
    )

    neg_prompt = st.text_input(
        "Negative prompt",
        value="blurry, distorted, low quality, text overlay, watermark",
        key="cs_neg",
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
