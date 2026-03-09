"""
View 11 — Drafts Review
Review, accept or reject generated content (scenarios, videos, music).
"""
import json
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
import streamlit.components.v1 as components

from app.components.ui import sidebar_css, page_title
from app.components.media_grid import _fetch_thumbnail_b64
from app.components.ig_preview import render_ig_preview_carousel
from src.services.google_drive import download_file_bytes
from src.services.creative_queries import (
    fetch_draft_scenarios,
    fetch_draft_music,
    fetch_draft_videos,
    fetch_media_info,
    update_scenario_feedback,
    update_music_feedback,
    update_job_feedback,
)
from src.services.carousel_queries import (
    fetch_carousel_drafts,
    update_carousel_feedback,
)


sidebar_css()
page_title("Drafts Review", "Review, accept or reject generated content")


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------

STATUS_OPTIONS = {
    "Scenarios": ["draft", "accepted", "rejected", "all"],
    "Videos": ["unreviewed", "accepted", "rejected", "all"],
    "Music": ["draft", "accepted", "rejected", "all"],
    "Carousels": ["draft", "accepted", "rejected", "all"],
}

STATUS_LABELS = {
    "draft": "Draft",
    "unreviewed": "Unreviewed",
    "accepted": "Accepted",
    "rejected": "Rejected",
    "all": "All",
}

STATUS_COLORS = {
    "draft": "blue",
    "unreviewed": "blue",
    "accepted": "green",
    "rejected": "red",
    "completed": "blue",
    "published": "violet",
    "validated": "green",
}

with st.sidebar:
    st.subheader("Filters")

    filter_type = st.selectbox(
        "Content type",
        ["All", "Scenarios", "Videos", "Music", "Carousels"],
        key="dr_type",
    )

    # Status filter per type
    status_scenario = st.selectbox(
        "Scenario status",
        STATUS_OPTIONS["Scenarios"],
        format_func=lambda s: STATUS_LABELS[s],
        key="dr_status_sc",
    )
    status_video = st.selectbox(
        "Video status",
        STATUS_OPTIONS["Videos"],
        format_func=lambda s: STATUS_LABELS[s],
        key="dr_status_vid",
    )
    status_music = st.selectbox(
        "Music status",
        STATUS_OPTIONS["Music"],
        format_func=lambda s: STATUS_LABELS[s],
        key="dr_status_mu",
    )
    status_carousel = st.selectbox(
        "Carousel status",
        STATUS_OPTIONS["Carousels"],
        format_func=lambda s: STATUS_LABELS[s],
        key="dr_status_car",
    )


# ---------------------------------------------------------------------------
# Shared review widget
# ---------------------------------------------------------------------------

def render_review_controls(item_id: str, item_type: str, current_status: str, key_prefix: str):
    """Render accept/reject + rating + feedback controls.

    item_type: 'scenario' | 'music' | 'video'
    Returns True if an action was taken (caller should rerun).
    """
    already_reviewed = current_status in ("accepted", "rejected")

    if already_reviewed:
        color = STATUS_COLORS.get(current_status, "gray")
        st.markdown(f"Status: :{color}[{current_status.upper()}]")

    rating = st.slider(
        "Rating", 1, 5, 3, key=f"{key_prefix}_rating_{item_id}",
        help="Your quality assessment: 1 = poor, 5 = excellent. Used to improve future AI prompts.",
    )
    feedback_text = st.text_input(
        "Feedback",
        key=f"{key_prefix}_fb_{item_id}",
        placeholder="Optional — what's good or bad about this?",
    )

    col_accept, col_reject = st.columns(2)
    with col_accept:
        accept_label = "Accepted" if current_status == "accepted" else "Accept"
        if st.button(
            accept_label,
            key=f"{key_prefix}_accept_{item_id}",
            type="primary" if current_status != "accepted" else "secondary",
            use_container_width=True,
        ):
            _do_feedback(item_id, item_type, "accepted", feedback_text, rating)
            st.rerun()
    with col_reject:
        reject_label = "Rejected" if current_status == "rejected" else "Reject"
        if st.button(
            reject_label,
            key=f"{key_prefix}_reject_{item_id}",
            type="secondary",
            use_container_width=True,
        ):
            _do_feedback(item_id, item_type, "rejected", feedback_text, rating)
            st.rerun()


def _do_feedback(item_id: str, item_type: str, status: str, feedback: str, rating: int):
    """Dispatch feedback update to the right DB function."""
    fb = feedback if feedback else None
    if item_type == "scenario":
        update_scenario_feedback(item_id, status, feedback=fb, rating=rating)
    elif item_type == "music":
        update_music_feedback(item_id, status, feedback=fb, rating=rating)
    elif item_type == "video":
        update_job_feedback(item_id, status=status, feedback=fb, rating=rating)
    elif item_type == "carousel":
        update_carousel_feedback(item_id, status, feedback=fb, rating=rating)


# ---------------------------------------------------------------------------
# Fetch data
# ---------------------------------------------------------------------------

show_scenarios = filter_type in ("All", "Scenarios")
show_videos = filter_type in ("All", "Videos")
show_music = filter_type in ("All", "Music")
show_carousels = filter_type in ("All", "Carousels")

scenarios = fetch_draft_scenarios(status=status_scenario) if show_scenarios else []
videos = fetch_draft_videos(status=status_video) if show_videos else []
music_tracks = fetch_draft_music(status=status_music) if show_music else []
carousels = fetch_carousel_drafts(status=status_carousel) if show_carousels else []

# Resolve source media info for display (name + thumbnail)
all_media_ids = list({
    item.get("source_media_id")
    for items in (scenarios, videos, music_tracks)
    for item in items
    if item.get("source_media_id")
})
# Also collect media_ids from carousels
for car in carousels:
    all_media_ids.extend(car.get("media_ids", []))
all_media_ids = list(set(mid for mid in all_media_ids if mid))
_media_info = fetch_media_info(all_media_ids) if all_media_ids else {}
# Backward compat helper
media_names = {mid: info.get("file_name", "—") for mid, info in _media_info.items()}

# Sidebar summary stats
with st.sidebar:
    st.divider()
    st.subheader("Summary")
    st.metric("Scenarios", len(scenarios))
    st.metric("Videos", len(videos))
    st.metric("Music tracks", len(music_tracks))
    st.metric("Carousels", len(carousels))


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab_scenarios, tab_videos, tab_music, tab_carousels = st.tabs([
    f"Scenarios ({len(scenarios)})",
    f"Videos ({len(videos)})",
    f"Music ({len(music_tracks)})",
    f"Carousels ({len(carousels)})",
])


# ---------------------------------------------------------------------------
# Tab 1: Scenarios
# ---------------------------------------------------------------------------
with tab_scenarios:
    if not scenarios:
        st.info("No scenarios match the current filter.")
    for sc in scenarios:
        sc_id = sc["id"]
        mood = sc.get("mood", "?")
        title = sc.get("title", "Untitled")
        source_mid = sc.get("source_media_id", "")
        source_name = media_names.get(source_mid, "—")
        sc_status = sc.get("status", "draft")
        color = STATUS_COLORS.get(sc_status, "gray")

        with st.expander(f":{color}[{sc_status.upper()}] :violet[Video scenario] [{mood.upper()}] {title}  —  *{source_name}*"):
            # Thumbnail + description side by side
            _sc_thumb_col, _sc_info_col = st.columns([1, 3])
            with _sc_thumb_col:
                _sc_dfid = _media_info.get(source_mid, {}).get("drive_file_id")
                if _sc_dfid:
                    try:
                        _sc_b64 = _fetch_thumbnail_b64(_sc_dfid)
                        if _sc_b64:
                            st.image(f"data:image/jpeg;base64,{_sc_b64}", width=140)
                        else:
                            st.caption("No thumbnail")
                    except Exception:
                        st.caption("No thumbnail")
                else:
                    st.caption("—")
            with _sc_info_col:
                if sc.get("description"):
                    st.markdown(f"**{sc['description']}**")
                if sc.get("caption_hook"):
                    st.markdown(f"Caption hook: *{sc['caption_hook']}*")

            if sc.get("motion_prompt"):
                st.text_area("Motion prompt", value=sc["motion_prompt"], height=80,
                             key=f"dr_sc_mp_{sc_id}", disabled=True)

            info_parts = []
            if sc.get("cost_usd"):
                info_parts.append(f"${sc['cost_usd']:.4f}")
            if sc.get("created_at"):
                info_parts.append(sc["created_at"][:16])
            if sc.get("model"):
                info_parts.append(sc["model"])
            if info_parts:
                st.caption(" | ".join(info_parts))

            if sc.get("feedback"):
                st.markdown(f"Previous feedback: *{sc['feedback']}*")
            if sc.get("rating"):
                st.markdown(f"Previous rating: {'★' * sc['rating']}")

            render_review_controls(sc_id, "scenario", sc_status, "dr_sc")


# ---------------------------------------------------------------------------
# Tab 2: Videos
# ---------------------------------------------------------------------------
with tab_videos:
    if not videos:
        st.info("No videos match the current filter.")
    for vj in videos:
        vj_id = vj["id"]
        params = vj.get("params", {})
        if isinstance(params, str):
            params = json.loads(params)
        source_name = media_names.get(vj.get("source_media_id", ""), "—")
        vj_status = vj.get("status", "completed")
        # For videos: completed with no feedback = unreviewed
        display_status = vj_status if vj.get("feedback") is not None else "unreviewed"
        if vj_status in ("accepted", "rejected"):
            display_status = vj_status
        color = STATUS_COLORS.get(display_status, "gray")

        prompt_preview = (params.get("prompt", "")[:60] + "...") if params.get("prompt") else "—"
        date_str = vj.get("created_at", "?")[:16]

        with st.expander(f":{color}[{display_status.upper()}] {date_str}  —  *{source_name}*  —  {prompt_preview}"):
            if vj.get("result_url"):
                _vid_col, _vid_spacer = st.columns([2, 1])
                with _vid_col:
                    st.video(vj["result_url"])
            if params.get("prompt"):
                st.text_area("Prompt", value=params["prompt"], height=80,
                             key=f"dr_vid_prompt_{vj_id}", disabled=True)

            info_parts = []
            if vj.get("cost_usd"):
                info_parts.append(f"${vj['cost_usd']:.2f}")
            if params.get("duration"):
                info_parts.append(f"{params['duration']}s")
            if params.get("model"):
                info_parts.append(params["model"])
            if vj.get("drive_file_id"):
                info_parts.append("Saved to Drive")
            if info_parts:
                st.caption(" | ".join(info_parts))

            if vj.get("feedback"):
                st.markdown(f"Previous feedback: *{vj['feedback']}*")
            if vj.get("rating"):
                st.markdown(f"Previous rating: {'*' * vj['rating']}")

            render_review_controls(vj_id, "video", vj_status, "dr_vid")


# ---------------------------------------------------------------------------
# Tab 3: Music
# ---------------------------------------------------------------------------
with tab_music:
    if not music_tracks:
        st.info("No music tracks match the current filter.")
    for mu in music_tracks:
        mu_id = mu["id"]
        source_name = media_names.get(mu.get("source_media_id", ""), "—")
        mu_status = mu.get("status", "draft")
        color = STATUS_COLORS.get(mu_status, "gray")
        prompt_preview = (mu.get("prompt", "")[:60] + "...") if mu.get("prompt") else "—"
        date_str = mu.get("created_at", "?")[:16]

        with st.expander(f":{color}[{mu_status.upper()}] {date_str}  —  *{source_name}*  —  {prompt_preview}"):
            # Play audio: prefer Drive download (Drive view links don't stream)
            _mu_played = False
            if mu.get("drive_file_id"):
                try:
                    _mu_bytes = download_file_bytes(mu["drive_file_id"])
                    st.audio(_mu_bytes, format="audio/wav")
                    _mu_played = True
                except Exception:
                    pass
            if not _mu_played and mu.get("audio_url") and "drive.google.com" not in mu.get("audio_url", ""):
                st.audio(mu["audio_url"])

            if mu.get("prompt"):
                st.text_area("Prompt", value=mu["prompt"], height=80,
                             key=f"dr_mu_prompt_{mu_id}", disabled=True)

            info_parts = []
            if mu.get("cost_usd"):
                info_parts.append(f"${mu['cost_usd']:.4f}")
            if mu.get("duration_seconds"):
                info_parts.append(f"{mu['duration_seconds']}s")
            if mu.get("model"):
                info_parts.append(mu["model"])
            if mu.get("drive_file_id"):
                info_parts.append("Saved to Drive")
            if info_parts:
                st.caption(" | ".join(info_parts))

            if mu.get("feedback"):
                st.markdown(f"Previous feedback: *{mu['feedback']}*")
            if mu.get("rating"):
                st.markdown(f"Previous rating: {'*' * mu['rating']}")

            render_review_controls(mu_id, "music", mu_status, "dr_mu")


# ---------------------------------------------------------------------------
# Tab 4: Carousels
# ---------------------------------------------------------------------------
with tab_carousels:
    if not carousels:
        st.info("No carousels match the current filter.")
    for car in carousels:
        car_id = car["id"]
        title = car.get("title", "Untitled")
        car_status = car.get("status", "draft")
        color = STATUS_COLORS.get(car_status, "gray")
        n_images = len(car.get("media_ids", []))
        date_str = car.get("created_at", "?")[:16]
        caption_preview = (car.get("caption_es", "")[:60] + "...") if car.get("caption_es") else "—"

        with st.expander(f":{color}[{car_status.upper()}] {title}  —  {n_images} images  —  {date_str}"):
            # Carousel image preview
            _car_media_ids = car.get("media_ids", [])
            _car_images_b64 = []
            if _car_media_ids:
                for _cm_id in _car_media_ids:
                    _cm_dfid = _media_info.get(_cm_id, {}).get("drive_file_id")
                    if _cm_dfid:
                        try:
                            _cm_b64 = _fetch_thumbnail_b64(_cm_dfid)
                            if _cm_b64:
                                _car_images_b64.append(_cm_b64)
                        except Exception:
                            pass

            if _car_images_b64:
                _car_caption = car.get("caption_es", "")
                _car_tags = " ".join(car.get("hashtags", []))
                _car_html, _car_h = render_ig_preview_carousel(
                    _car_images_b64, _car_caption, _car_tags,
                )
                _preview_col, _info_col = st.columns([1, 1])
                with _preview_col:
                    components.html(_car_html, height=min(_car_h, 700), scrolling=True)
                with _info_col:
                    for lang, label in [("caption_es", "ES"), ("caption_en", "EN"), ("caption_fr", "FR")]:
                        text = car.get(lang, "")
                        if text:
                            st.text_area(f"Caption {label}", value=text, height=60,
                                         key=f"dr_car_{lang}_{car_id}", disabled=True)
                    tags = car.get("hashtags", [])
                    if tags:
                        st.markdown(f"**Hashtags:** {' '.join(f'`{t}`' for t in tags)}")
            else:
                # No images available — show captions only
                for lang, label in [("caption_es", "ES"), ("caption_en", "EN"), ("caption_fr", "FR")]:
                    text = car.get(lang, "")
                    if text:
                        st.text_area(f"Caption {label}", value=text, height=60,
                                     key=f"dr_car_{lang}_{car_id}", disabled=True)
                tags = car.get("hashtags", [])
                if tags:
                    st.markdown(f"**Hashtags:** {' '.join(f'`{t}`' for t in tags)}")

            # Meta info
            info_parts = [f"{n_images} images"]
            if car.get("ig_permalink"):
                info_parts.append(f"[Published]({car['ig_permalink']})")
            if date_str != "?":
                info_parts.append(date_str)
            st.caption(" | ".join(info_parts))

            if car.get("feedback"):
                st.markdown(f"Previous feedback: *{car['feedback']}*")
            if car.get("rating"):
                st.markdown(f"Previous rating: {'★' * car['rating']}")

            render_review_controls(car_id, "carousel", car_status, "dr_car")
