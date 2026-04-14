"""
View 11 — Review History
Review, accept or reject generated content (scenarios, videos, music, carousels).
Items grouped by calendar slot when available.
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
from app.components.review_controls import render_review_controls, STATUS_COLORS
from src.services.google_drive import download_file_bytes
from src.services.creative_queries import (
    fetch_draft_scenarios,
    fetch_draft_music,
    fetch_draft_videos,
    fetch_media_info,
)
from src.services.carousel_queries import (
    fetch_carousel_drafts,
)
from src.services.editorial_queries import fetch_calendar_range
from datetime import date, timedelta


sidebar_css()
page_title("Review History", "Review, accept or reject generated content")


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

    st.divider()
    group_by_slot = st.checkbox("Group by calendar slot", value=True, key="dr_group_slot")


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
media_names = {mid: info.get("file_name", "---") for mid, info in _media_info.items()}

# Build calendar slot lookup for grouping
_all_cal_ids = set()
for item in scenarios:
    if item.get("calendar_id"):
        _all_cal_ids.add(item["calendar_id"])
for item in videos:
    if item.get("calendar_id"):
        _all_cal_ids.add(item["calendar_id"])
for item in music_tracks:
    if item.get("calendar_id"):
        _all_cal_ids.add(item["calendar_id"])
for item in carousels:
    if item.get("calendar_id"):
        _all_cal_ids.add(item["calendar_id"])

_cal_lookup = {}
if _all_cal_ids:
    # Fetch calendar entries for context
    _lookback = date.today() - timedelta(weeks=12)
    _lookahead = date.today() + timedelta(weeks=12)
    _cal_data = fetch_calendar_range(_lookback, _lookahead)
    _cal_lookup = {e["id"]: e for e in _cal_data}


def _slot_header(calendar_id):
    """Return a slot header string for grouping."""
    entry = _cal_lookup.get(calendar_id)
    if not entry:
        return None
    pd = entry.get("post_date", "?")
    si = entry.get("slot_index", 1)
    cat = entry.get("target_category") or "?"
    route = entry.get("target_format") or "feed"
    return f"{pd} S{si} | {cat} | {route}"


# Sidebar summary stats
with st.sidebar:
    st.divider()
    st.subheader("Summary")
    st.metric("Scenarios", len(scenarios))
    st.metric("Videos", len(videos))
    st.metric("Music tracks", len(music_tracks))
    st.metric("Carousels", len(carousels))


# ---------------------------------------------------------------------------
# Group-by-slot helper
# ---------------------------------------------------------------------------

def _group_by_calendar(items):
    """Group items by calendar_id. Returns (grouped_dict, ungrouped_list)."""
    grouped = {}
    ungrouped = []
    for item in items:
        cal_id = item.get("calendar_id")
        if cal_id and cal_id in _cal_lookup:
            grouped.setdefault(cal_id, []).append(item)
        else:
            ungrouped.append(item)
    return grouped, ungrouped


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
def _render_scenario(sc, prefix="dr_sc"):
    sc_id = sc["id"]
    mood = sc.get("mood", "?")
    title = sc.get("title", "Untitled")
    source_mid = sc.get("source_media_id", "")
    source_name = media_names.get(source_mid, "---")
    sc_status = sc.get("status", "draft")
    color = STATUS_COLORS.get(sc_status, "gray")

    with st.expander(f":{color}[{sc_status.upper()}] :violet[Video scenario] [{mood.upper()}] {title}  ---  *{source_name}*"):
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
                st.caption("---")
        with _sc_info_col:
            if sc.get("description"):
                st.markdown(f"**{sc['description']}**")
            if sc.get("caption_hook"):
                st.markdown(f"Caption hook: *{sc['caption_hook']}*")

        if sc.get("motion_prompt"):
            st.text_area("Motion prompt", value=sc["motion_prompt"], height=80,
                         key=f"{prefix}_mp_{sc_id}", disabled=True)

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
            st.markdown(f"Previous rating: {'*' * sc['rating']}")

        render_review_controls(sc_id, "scenario", sc_status, prefix)


with tab_scenarios:
    if not scenarios:
        st.info("No scenarios match the current filter.")
    elif group_by_slot:
        grouped, ungrouped = _group_by_calendar(scenarios)
        for cal_id, items in grouped.items():
            header = _slot_header(cal_id)
            st.markdown(f"#### {header}")
            for sc in items:
                _render_scenario(sc, f"dr_sc_{cal_id[:8]}")
        if ungrouped:
            st.markdown("#### Ungrouped / AI Lab")
            for sc in ungrouped:
                _render_scenario(sc, "dr_sc_ug")
    else:
        for sc in scenarios:
            _render_scenario(sc)


# ---------------------------------------------------------------------------
# Tab 2: Videos
# ---------------------------------------------------------------------------
def _render_video(vj, prefix="dr_vid"):
    vj_id = vj["id"]
    params = vj.get("params", {})
    if isinstance(params, str):
        params = json.loads(params)
    source_name = media_names.get(vj.get("source_media_id", ""), "---")
    vj_status = vj.get("status", "completed")
    display_status = vj_status if vj.get("feedback") is not None else "unreviewed"
    if vj_status in ("accepted", "rejected"):
        display_status = vj_status
    color = STATUS_COLORS.get(display_status, "gray")

    prompt_preview = (params.get("prompt", "")[:60] + "...") if params.get("prompt") else "---"
    date_str = vj.get("created_at", "?")[:16]

    with st.expander(f":{color}[{display_status.upper()}] {date_str}  ---  *{source_name}*  ---  {prompt_preview}"):
        if vj.get("result_url"):
            _vid_col, _vid_spacer = st.columns([2, 1])
            with _vid_col:
                st.video(vj["result_url"])
        if params.get("prompt"):
            st.text_area("Prompt", value=params["prompt"], height=80,
                         key=f"{prefix}_prompt_{vj_id}", disabled=True)

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

        render_review_controls(vj_id, "video", vj_status, prefix)


with tab_videos:
    if not videos:
        st.info("No videos match the current filter.")
    elif group_by_slot:
        grouped, ungrouped = _group_by_calendar(videos)
        for cal_id, items in grouped.items():
            header = _slot_header(cal_id)
            st.markdown(f"#### {header}")
            for vj in items:
                _render_video(vj, f"dr_vid_{cal_id[:8]}")
        if ungrouped:
            st.markdown("#### Ungrouped / AI Lab")
            for vj in ungrouped:
                _render_video(vj, "dr_vid_ug")
    else:
        for vj in videos:
            _render_video(vj)


# ---------------------------------------------------------------------------
# Tab 3: Music
# ---------------------------------------------------------------------------
def _render_music(mu, prefix="dr_mu"):
    mu_id = mu["id"]
    source_name = media_names.get(mu.get("source_media_id", ""), "---")
    mu_status = mu.get("status", "draft")
    color = STATUS_COLORS.get(mu_status, "gray")
    prompt_preview = (mu.get("prompt", "")[:60] + "...") if mu.get("prompt") else "---"
    date_str = mu.get("created_at", "?")[:16]

    with st.expander(f":{color}[{mu_status.upper()}] {date_str}  ---  *{source_name}*  ---  {prompt_preview}"):
        _mu_played = False
        _mu_error = None
        if mu.get("drive_file_id"):
            try:
                _mu_bytes = download_file_bytes(mu["drive_file_id"])
                st.audio(_mu_bytes, format="audio/wav")
                _mu_played = True
            except Exception as _mu_ex:
                _mu_error = str(_mu_ex)
        if not _mu_played and mu.get("audio_url") and "drive.google.com" not in mu.get("audio_url", ""):
            st.audio(mu["audio_url"])
            _mu_played = True
        if not _mu_played:
            st.warning(f"Cannot play audio: {_mu_error or 'no audio source'}")

        if mu.get("prompt"):
            st.text_area("Prompt", value=mu["prompt"], height=80,
                         key=f"{prefix}_prompt_{mu_id}", disabled=True)

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

        render_review_controls(mu_id, "music", mu_status, prefix)


with tab_music:
    if not music_tracks:
        st.info("No music tracks match the current filter.")
    elif group_by_slot:
        grouped, ungrouped = _group_by_calendar(music_tracks)
        for cal_id, items in grouped.items():
            header = _slot_header(cal_id)
            st.markdown(f"#### {header}")
            for mu in items:
                _render_music(mu, f"dr_mu_{cal_id[:8]}")
        if ungrouped:
            st.markdown("#### Ungrouped / AI Lab")
            for mu in ungrouped:
                _render_music(mu, "dr_mu_ug")
    else:
        for mu in music_tracks:
            _render_music(mu)


# ---------------------------------------------------------------------------
# Tab 4: Carousels
# ---------------------------------------------------------------------------
def _render_carousel(car, prefix="dr_car"):
    car_id = car["id"]
    title = car.get("title", "Untitled")
    car_status = car.get("status", "draft")
    color = STATUS_COLORS.get(car_status, "gray")
    n_images = len(car.get("media_ids", []))
    date_str = car.get("created_at", "?")[:16]

    with st.expander(f":{color}[{car_status.upper()}] {title}  ---  {n_images} images  ---  {date_str}"):
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
                                     key=f"{prefix}_{lang}_{car_id}", disabled=True)
                tags = car.get("hashtags", [])
                if tags:
                    st.markdown(f"**Hashtags:** {' '.join(f'`{t}`' for t in tags)}")
        else:
            for lang, label in [("caption_es", "ES"), ("caption_en", "EN"), ("caption_fr", "FR")]:
                text = car.get(lang, "")
                if text:
                    st.text_area(f"Caption {label}", value=text, height=60,
                                 key=f"{prefix}_{lang}_{car_id}", disabled=True)
            tags = car.get("hashtags", [])
            if tags:
                st.markdown(f"**Hashtags:** {' '.join(f'`{t}`' for t in tags)}")

        info_parts = [f"{n_images} images"]
        if car.get("ig_permalink"):
            info_parts.append(f"[Published]({car['ig_permalink']})")
        if date_str != "?":
            info_parts.append(date_str)
        st.caption(" | ".join(info_parts))

        if car.get("feedback"):
            st.markdown(f"Previous feedback: *{car['feedback']}*")
        if car.get("rating"):
            st.markdown(f"Previous rating: {'*' * car['rating']}")

        render_review_controls(car_id, "carousel", car_status, prefix)


with tab_carousels:
    if not carousels:
        st.info("No carousels match the current filter.")
    elif group_by_slot:
        grouped, ungrouped = _group_by_calendar(carousels)
        for cal_id, items in grouped.items():
            header = _slot_header(cal_id)
            st.markdown(f"#### {header}")
            for car in items:
                _render_carousel(car, f"dr_car_{cal_id[:8]}")
        if ungrouped:
            st.markdown("#### Ungrouped / AI Lab")
            for car in ungrouped:
                _render_carousel(car, "dr_car_ug")
    else:
        for car in carousels:
            _render_carousel(car)
