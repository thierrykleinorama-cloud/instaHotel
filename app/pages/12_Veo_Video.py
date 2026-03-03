"""
View 12 — Veo 3 Video (AI Lab)
Dedicated test page for Google Veo 3.1 video generation.
"""
import sys
from datetime import datetime
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.ui import sidebar_css, page_title
from app.components.media_selector import render_media_selector
from src.utils import encode_image_bytes
from src.services.creative_transform import (
    generate_motion_prompt_ai,
    photo_to_video,
    VIDEO_MODELS,
    estimate_video_cost,
)
from src.prompts.creative_transform import HOTEL_CONTEXT
from src.services.creative_job_queries import save_video_job, fetch_video_jobs
from src.services.creative_queries import update_job_feedback
from src.services.publisher import upload_to_supabase_storage
from src.services.google_drive import upload_file_to_drive, ensure_generated_folders

sidebar_css()
page_title("Veo 3 Video", "Google Veo 3.1 photo-to-video generation")

st.page_link("pages/5_AI_Lab.py", label="Back to AI Lab", icon=":material/arrow_back:")

# --- Media selector ---
media, image_bytes = render_media_selector("veo")

# --- Veo-only models ---
VEO_KEYS = [k for k, v in VIDEO_MODELS.items() if v.get("provider") == "google"]

# --- Sidebar settings ---
with st.sidebar:
    st.divider()
    st.subheader("Veo Settings")

    veo_model = st.selectbox(
        "Model Variant",
        VEO_KEYS,
        format_func=lambda k: VIDEO_MODELS[k]["label"],
        key="veo_model",
    )

    duration = st.select_slider("Duration (sec)", [4, 6, 8], value=8, key="veo_dur")
    aspect_ratio = st.selectbox("Aspect Ratio", ["9:16", "16:9"], key="veo_ar")
    resolution = st.selectbox("Resolution", ["720p", "1080p"], key="veo_res")

    cost = estimate_video_cost(veo_model, duration)
    st.caption(f"Estimated cost: **${cost:.2f}**")

    st.divider()
    st.markdown("**Veo 3.1 vs Kling:**")
    st.caption(
        "- Higher visual quality\n"
        "- Native audio generation\n"
        "- Duration: 4/6/8s (vs 5/10s)\n"
        "- Higher cost per second"
    )

# --- Prompt section ---
st.markdown("### Motion Prompt")

prompt_mode = st.radio(
    "Prompt source",
    ["AI-generated (Claude)", "Manual"],
    key="veo_prompt_mode",
    horizontal=True,
)

if prompt_mode.startswith("AI"):
    ai_brief = st.text_input(
        "Creative brief (optional)",
        placeholder="e.g., 'cinematic sunrise reveal', 'cozy winter morning'",
        key="veo_ai_brief",
    )
    ai_include_photo = st.checkbox("Include photo in AI prompt", value=True, key="veo_ai_photo")

    if st.button("Generate AI Prompt", type="secondary", key="veo_gen_prompt"):
        with st.spinner("Claude is writing a cinematic prompt..."):
            try:
                b64 = encode_image_bytes(image_bytes) if ai_include_photo else None
                ai_result = generate_motion_prompt_ai(
                    media,
                    creative_brief=ai_brief,
                    image_base64=b64,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                )
                st.session_state["veo_motion_prompt"] = ai_result["prompt"]
                st.session_state["_veo_prompt_updated"] = True
                usage = ai_result["_usage"]
                st.success(f"AI prompt generated! (${usage['cost_usd']:.4f})")
            except Exception as e:
                st.error(f"AI prompt generation failed: {e}")

if st.session_state.pop("_veo_prompt_updated", False):
    st.session_state["veo_prompt_edit"] = st.session_state.get("veo_motion_prompt", "")
elif "veo_prompt_edit" not in st.session_state:
    st.session_state["veo_prompt_edit"] = ""

motion_prompt = st.text_area(
    "Motion Prompt",
    height=120,
    key="veo_prompt_edit",
    placeholder="Describe camera movement + animation. E.g., 'Slow dolly forward, curtains sway in breeze, warm golden light...'",
)

with st.expander("Negative prompt"):
    neg_prompt = st.text_input(
        "Negative prompt",
        value="blurry, distorted, low quality, text overlay, watermark, AI artifacts, unrealistic proportions",
        key="veo_neg",
    )

# --- Generate ---
if st.button("Generate Veo Video", type="primary", key="veo_generate", disabled=not motion_prompt):
    with st.spinner(f"Generating {duration}s Veo video... This may take 2-5 minutes."):
        try:
            result = photo_to_video(
                image_bytes=image_bytes,
                prompt=motion_prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                model=veo_model,
                negative_prompt=neg_prompt,
                resolution=resolution,
            )
            st.session_state["veo_video_result"] = result
            st.success(f"Video generated! Cost: ${result['_cost']['cost_usd']:.2f}")

            # Save to Storage + Drive + DB
            try:
                _ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                _stem = media.get("file_name", "video").rsplit(".", 1)[0][:40]
                fname = f"{_stem}_veo_{_ts}.mp4"
                video_url = upload_to_supabase_storage(result["video_bytes"], fname, "video/mp4")

                _drive_fid = None
                try:
                    folders = ensure_generated_folders()
                    _drive_result = upload_file_to_drive(
                        result["video_bytes"], fname, "video/mp4", folders["videos"],
                    )
                    _drive_fid = _drive_result["id"]
                    st.caption(f"Saved to Drive: Generated/Videos/{fname}")
                except Exception as _de:
                    st.warning(f"Drive upload failed: {_de}")

                save_video_job(
                    source_media_id=media["id"],
                    video_url=video_url,
                    prompt=motion_prompt,
                    cost_usd=result["_cost"]["cost_usd"],
                    provider="google",
                    params={
                        "duration": duration,
                        "aspect_ratio": aspect_ratio,
                        "model": veo_model,
                        "resolution": resolution,
                    },
                    drive_file_id=_drive_fid,
                )
            except Exception:
                pass  # non-critical
        except Exception as e:
            st.error(f"Video generation failed: {e}")

# --- Display result ---
video_result = st.session_state.get("veo_video_result")
if video_result:
    st.video(video_result["video_bytes"])
    st.caption(
        f"Duration: {video_result['duration_sec']}s | "
        f"AR: {video_result.get('aspect_ratio', '?')} | "
        f"Cost: ${video_result['_cost']['cost_usd']:.2f}"
    )

    st.download_button(
        "Download Video",
        data=video_result["video_bytes"],
        file_name=f"{media.get('file_name', 'video').rsplit('.', 1)[0]}_veo.mp4",
        mime="video/mp4",
        key="veo_dl",
    )

# --- Previous videos ---
st.divider()
prev_videos = fetch_video_jobs(media["id"], limit=5)
if prev_videos:
    with st.expander(f"Previous videos for this photo ({len(prev_videos)})"):
        for j, vj in enumerate(prev_videos):
            params = vj.get("params", {})
            if isinstance(params, str):
                import json
                params = json.loads(params)
            provider = vj.get("provider", "replicate")
            _badge = ":green[Veo]" if provider == "google" else ":blue[Kling]"
            st.caption(
                f"{_badge} **{vj.get('created_at', '?')[:16]}** | "
                f"${vj.get('cost_usd', 0):.2f} | {params.get('model', '?')}"
            )
            if params.get("prompt"):
                st.caption(f"Prompt: {params['prompt'][:120]}...")
            if vj.get("result_url"):
                st.video(vj["result_url"])

            # Accept/reject
            if vj.get("id"):
                _status = vj.get("status", "completed")
                _reviewed = _status in ("accepted", "rejected")
                if _reviewed:
                    _c = "green" if _status == "accepted" else "red"
                    st.markdown(f":{_c}[{_status.upper()}]")

                rating = st.slider("Rating", 1, 5, 3, key=f"veo_r_{vj['id']}")
                fb = st.text_input("Feedback", key=f"veo_fb_{vj['id']}", placeholder="Optional")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Accept", key=f"veo_ok_{vj['id']}", use_container_width=True):
                        update_job_feedback(vj["id"], status="accepted", feedback=fb or None, rating=rating)
                        st.rerun()
                with c2:
                    if st.button("Reject", key=f"veo_no_{vj['id']}", use_container_width=True):
                        update_job_feedback(vj["id"], status="rejected", feedback=fb or None, rating=rating)
                        st.rerun()

            if j < len(prev_videos) - 1:
                st.divider()
