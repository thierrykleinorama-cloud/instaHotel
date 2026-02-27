"""
View 10 — AI Music
Generate background music for Reels and composite video+audio.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.ui import sidebar_css, page_title
from src.prompts.music_generation import build_music_prompt, AMBIANCE_MUSIC_MAP, CATEGORY_MUSIC_MAP
from src.services.music_generator import generate_music, MUSIC_MODELS, DEFAULT_MUSIC_MODEL
from src.services.video_composer import composite_video_audio


sidebar_css()
page_title("AI Music", "Generate background music for Reels")

st.page_link("pages/5_AI_Lab.py", label="Back to AI Lab", icon=":material/arrow_back:")

# -------------------------------------------------------
# Tabs: Music Generation / Video + Audio Composite
# -------------------------------------------------------
tab_gen, tab_composite = st.tabs(["Generate Music", "Video + Audio Composite"])

# -------------------------------------------------------
# Tab 1: Music Generation
# -------------------------------------------------------
with tab_gen:
    st.markdown("### Generate Background Music")

    with st.sidebar:
        st.subheader("Music Settings")

        music_model = st.selectbox(
            "Model",
            list(MUSIC_MODELS.keys()),
            format_func=lambda k: MUSIC_MODELS[k]["label"],
            key="mu_model",
        )

        duration = st.slider("Duration (sec)", 5, 30, 10, key="mu_dur")

        temperature = st.slider(
            "Creativity", 0.5, 1.5, 1.0, step=0.1, key="mu_temp",
            help="Higher = more creative/varied, lower = more predictable",
        )

        model_info = MUSIC_MODELS[music_model]
        cost = duration * model_info["cost_per_sec"]
        st.caption(f"Estimated cost: ${cost:.3f}")

    # Prompt building helpers
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
                st.session_state["mu_prompt_val"] = preset_prompt

    # Show ambiance/category maps for reference
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

    music_prompt = st.text_area(
        "Music Prompt",
        value=st.session_state.get("mu_prompt_val", presets[0][1]),
        height=100,
        key="mu_prompt",
        help="Describe the style, mood, instruments. The AI generates instrumental music.",
    )

    if st.button("Generate Music", type="primary", key="mu_generate"):
        with st.spinner(f"Generating {duration}s music track..."):
            try:
                result = generate_music(
                    prompt=music_prompt,
                    duration=duration,
                    model=music_model,
                    temperature=temperature,
                )
                st.session_state["mu_result"] = result
                st.success(f"Music generated! Cost: ${result['_cost']['cost_usd']:.3f}")
            except Exception as e:
                st.error(f"Music generation failed: {e}")

    # Display result
    music_result = st.session_state.get("mu_result")
    if music_result:
        st.audio(music_result["audio_bytes"], format=f"audio/{music_result['format']}")
        st.caption(f"Duration: {music_result['duration_sec']}s | Format: {music_result['format']}")

        st.download_button(
            "Download Audio",
            data=music_result["audio_bytes"],
            file_name=f"music_{music_result['duration_sec']}s.{music_result['format']}",
            mime=f"audio/{music_result['format']}",
            key="mu_dl",
        )

# -------------------------------------------------------
# Tab 2: Video + Audio Composite
# -------------------------------------------------------
with tab_composite:
    st.markdown("### Merge Video + Audio")
    st.caption(
        "Upload or use a generated video and audio track to create a final MP4 with background music."
    )

    # Video source
    st.markdown("**Video source:**")
    video_source = st.radio("Source", ["Upload file", "From Creative Studio (session)"], key="vc_vsource", horizontal=True)

    video_bytes = None
    if video_source == "Upload file":
        uploaded_video = st.file_uploader("Upload MP4 video", type=["mp4"], key="vc_upload_v")
        if uploaded_video:
            video_bytes = uploaded_video.read()
            st.video(video_bytes)
    else:
        cs_result = st.session_state.get("cs_video_result")
        if cs_result:
            video_bytes = cs_result["video_bytes"]
            st.video(video_bytes)
            st.caption(f"From Creative Studio: {cs_result.get('duration_sec', '?')}s")
        else:
            st.info("No video in session. Generate one in the Creative Studio first.")

    st.markdown("**Audio source:**")
    audio_source = st.radio("Source", ["Upload file", "Generated music (session)"], key="vc_asource", horizontal=True)

    audio_bytes = None
    audio_format = "wav"
    if audio_source == "Upload file":
        uploaded_audio = st.file_uploader("Upload audio", type=["wav", "mp3"], key="vc_upload_a")
        if uploaded_audio:
            audio_bytes = uploaded_audio.read()
            audio_format = "mp3" if uploaded_audio.name.endswith(".mp3") else "wav"
            st.audio(audio_bytes, format=f"audio/{audio_format}")
    else:
        mu_result = st.session_state.get("mu_result")
        if mu_result:
            audio_bytes = mu_result["audio_bytes"]
            audio_format = mu_result["format"]
            st.audio(audio_bytes, format=f"audio/{audio_format}")
            st.caption(f"Generated music: {mu_result['duration_sec']}s")
        else:
            st.info("No music in session. Generate some in the Generate Music tab first.")

    # Composite settings
    st.markdown("**Mix settings:**")
    mix_c1, mix_c2 = st.columns(2)
    with mix_c1:
        volume = st.slider("Music volume", 0.0, 1.0, 0.3, step=0.05, key="vc_vol",
                          help="0.3 = subtle background, 0.7 = prominent, 1.0 = full volume")
    with mix_c2:
        fade_out = st.slider("Fade out (sec)", 0.0, 3.0, 1.5, step=0.5, key="vc_fade",
                            help="Fade out music before video ends")

    can_composite = video_bytes is not None and audio_bytes is not None

    if st.button("Merge Video + Audio", type="primary", disabled=not can_composite, key="vc_merge"):
        with st.spinner("Compositing video + audio with FFmpeg..."):
            try:
                result = composite_video_audio(
                    video_bytes=video_bytes,
                    audio_bytes=audio_bytes,
                    volume=volume,
                    fade_out_sec=fade_out,
                    audio_format=audio_format,
                )
                st.session_state["vc_result"] = result
                st.success("Video + audio merged!")
            except Exception as e:
                st.error(f"Compositing failed: {e}")

    # Display result
    vc_result = st.session_state.get("vc_result")
    if vc_result:
        st.video(vc_result["video_bytes"])

        st.download_button(
            "Download Final Video",
            data=vc_result["video_bytes"],
            file_name="reel_with_music.mp4",
            mime="video/mp4",
            key="vc_dl",
        )
