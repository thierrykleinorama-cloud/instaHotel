"""
InstaHotel — Production Pipeline
Route-based tabs: one tab per content type, each self-contained with settings + pipeline steps.
"""
import json
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from datetime import date, timedelta

from app.components.ui import sidebar_css, page_title
from app.components.review_controls import render_inline_review, STATUS_COLORS
from app.components.media_grid import _fetch_thumbnail_b64
from src.services.editorial_queries import fetch_calendar_range, update_calendar_creative_status
from src.services.creative_queries import (
    fetch_scenarios_for_calendar_ids,
    fetch_videos_for_calendar_ids,
    fetch_music_for_calendar_ids,
    fetch_composite_for_calendar_ids,
    fetch_slideshows_for_calendar_ids,
    fetch_accepted_scenario_for_calendar,
    fetch_media_info,
    accept_scenario_reject_others,
)
from src.services.carousel_queries import fetch_carousels_for_calendar_ids
from src.services.content_queries import fetch_content_for_calendar_range
from src.services.google_drive import download_file_bytes
from src.services.batch_creative import (
    classify_slots_by_route,
    batch_generate_scenarios,
    batch_generate_videos,
    batch_generate_music,
    batch_composite,
    batch_generate_carousels,
    batch_generate_slideshows,
    estimate_scenario_cost,
    estimate_video_cost,
    estimate_music_cost,
    estimate_carousel_cost,
    ROUTES_REEL,
    ROUTES_NEED_MUSIC,
)
from src.services.content_generator import generate_for_slot, estimate_batch_cost
from src.services.caption_generator import DEFAULT_MODEL
from src.prompts.tone_variants import TONE_LABELS

sidebar_css()
page_title("Production Pipeline", "Generate and review content — one tab per route")

ROUTE_LABELS = {
    "feed": "Image Posts",
    "carousel": "Carousel",
    "reel-kling": "Reel (Kling)",
    "reel-veo": "Reel (Veo)",
    "reel-slideshow": "Slideshow",
}
ROUTE_COLORS = {
    "feed": "gray",
    "carousel": "orange",
    "reel-kling": "blue",
    "reel-veo": "green",
    "reel-slideshow": "violet",
}

# -------------------------------------------------------
# Session state defaults
# -------------------------------------------------------
for key, default in [
    ("bp_scenario_result", None),
    ("bp_video_result", None),
    ("bp_music_result", None),
    ("bp_composite_result", None),
    ("bp_carousel_result", None),
    ("bp_slideshow_result", None),
    ("bp_caption_result", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# -------------------------------------------------------
# Sidebar — date range only
# -------------------------------------------------------
with st.sidebar:
    st.subheader("Date Range")
    today = date.today()
    default_start = today - timedelta(days=today.weekday())

    # Auto-detect recent creative work
    _lookback_start = default_start - timedelta(weeks=4)
    _recent_cal = fetch_calendar_range(_lookback_start, default_start - timedelta(days=1))
    _has_creative = [e for e in _recent_cal if e.get("creative_status")]
    if _has_creative and not st.session_state.get("_bp_date_overridden"):
        _earliest = min(e["post_date"] for e in _has_creative)
        if isinstance(_earliest, str):
            _earliest = date.fromisoformat(_earliest)
        _creative_monday = _earliest - timedelta(days=_earliest.weekday())
        default_start = _creative_monday

    start_date = st.date_input("Start Date", value=default_start, key="bp_start")
    weeks = st.slider("Weeks", 1, 8, 4, key="bp_weeks")
    end_date = start_date + timedelta(weeks=weeks) - timedelta(days=1)
    st.caption(f"Range: {start_date.strftime('%d/%m/%Y')} -> {end_date.strftime('%d/%m/%Y')}")

# -------------------------------------------------------
# Load calendar data + route classification
# -------------------------------------------------------
calendar_data = fetch_calendar_range(start_date, end_date)

slots_with_media = [
    s for s in calendar_data
    if s.get("manual_media_id") or s.get("media_id")
]

if not slots_with_media:
    st.warning("No calendar slots with assigned media in this date range. Generate a calendar first.")
    st.stop()

route_groups = classify_slots_by_route(slots_with_media)
cal_ids = [s["id"] for s in slots_with_media]

# Fetch all creative data
scenario_map = fetch_scenarios_for_calendar_ids(cal_ids)
video_map = fetch_videos_for_calendar_ids(cal_ids)
music_map = fetch_music_for_calendar_ids(cal_ids)
composite_map = fetch_composite_for_calendar_ids(cal_ids)
carousel_map = fetch_carousels_for_calendar_ids(cal_ids)
slideshow_map = fetch_slideshows_for_calendar_ids(cal_ids)
content_map = fetch_content_for_calendar_range(cal_ids)

# Fetch media info for display
all_media_ids = list({
    s.get("manual_media_id") or s.get("media_id")
    for s in slots_with_media
    if s.get("manual_media_id") or s.get("media_id")
})
media_info = fetch_media_info(all_media_ids)


# -------------------------------------------------------
# Shared helpers
# -------------------------------------------------------
def _slot_label(slot):
    """Format a slot as a short label: 'Wed 12/03 S1 | chambre'."""
    pd = slot.get("post_date", "")
    if isinstance(pd, str) and len(pd) >= 10:
        from datetime import date as _d
        try:
            _dt = _d.fromisoformat(pd)
            pd = _dt.strftime("%a %d/%m")
        except Exception:
            pd = f"{pd[8:10]}/{pd[5:7]}"
    si = slot.get("slot_index", 1)
    cat = slot.get("target_category") or "?"
    return f"{pd} S{si} | {cat}"


def _slot_thumbnail(slot, width=100):
    """Show thumbnail for a slot's media."""
    mid = slot.get("manual_media_id") or slot.get("media_id")
    mi = media_info.get(mid, {}) if mid else {}
    dfid = mi.get("drive_file_id")
    if dfid:
        try:
            b64 = _fetch_thumbnail_b64(dfid)
            if b64:
                st.image(f"data:image/jpeg;base64,{b64}", width=width)
                return
        except Exception:
            pass
    st.caption("no thumb")


def _render_scenario_step(slots, key_prefix):
    """Render scenario generation + inline review for a list of reel slots.
    Returns (accepted_count, needs_action)."""
    slot_ids = [s["id"] for s in slots]

    # Settings row
    c1, c2, c3 = st.columns(3)
    scenario_count = c1.slider("Scenarios/slot", 2, 5, 3, key=f"{key_prefix}_sc_count")
    scenario_include_image = c2.checkbox("Include image", value=True, key=f"{key_prefix}_sc_img")
    scenario_model = c3.selectbox(
        "Model", ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
        key=f"{key_prefix}_sc_model",
    )

    # Stats
    sc_slots_with_active = [
        cid for cid in slot_ids
        if any(s.get("status") != "rejected" for s in scenario_map.get(cid, []))
    ]
    sc_accepted = sum(
        1 for cid in slot_ids
        if any(s.get("status") == "accepted" for s in scenario_map.get(cid, []))
    )
    sc_need_review = sum(
        1 for cid in slot_ids
        if cid in scenario_map
        and not any(s.get("status") == "accepted" for s in scenario_map.get(cid, []))
        and any(s.get("status") == "draft" for s in scenario_map.get(cid, []))
    )
    sc_eligible = len(slots) - len(sc_slots_with_active)

    # Progress bar
    st.progress(sc_accepted / max(len(slots), 1),
                text=f"Scenarios: {sc_accepted}/{len(slots)} accepted")

    if sc_need_review > 0:
        _review_labels = [
            _slot_label(s) for s in slots
            if s["id"] in scenario_map
            and not any(sc.get("status") == "accepted" for sc in scenario_map.get(s["id"], []))
            and any(sc.get("status") == "draft" for sc in scenario_map.get(s["id"], []))
        ]
        st.markdown(f":orange[Review needed:] {', '.join(_review_labels)}")
    if sc_eligible > 0:
        sc_est = estimate_scenario_cost(sc_eligible, scenario_count, scenario_include_image, scenario_model)
        if st.button(
            f"Generate Scenarios ({sc_eligible})",
            type="primary", key=f"{key_prefix}_run_sc",
            help=f"~${sc_est['total']:.2f}",
        ):
            eligible = [s for s in slots if s["id"] not in sc_slots_with_active]
            progress_bar = st.progress(0, text="Starting scenario generation...")

            def _cb(i, total, msg):
                progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

            with st.spinner(f"Generating scenarios for {len(eligible)} slots..."):
                result = batch_generate_scenarios(
                    slots=eligible, count=scenario_count, model=scenario_model,
                    include_image=scenario_include_image, progress_callback=_cb,
                )
            progress_bar.empty()
            st.success(
                f"{result['success']} generated, {result['skipped']} skipped, "
                f"{result['failed']} failed | ${result['total_cost']:.4f}"
            )
            if result["errors"]:
                for err in result["errors"]:
                    st.warning(err)
            st.rerun()

    # Show slots with all-rejected scenarios (need regeneration)
    _all_rejected_sc = [
        s for s in slots
        if s["id"] in scenario_map
        and all(sc.get("status") == "rejected" for sc in scenario_map.get(s["id"], []))
    ]
    if _all_rejected_sc:
        _rej_labels = ", ".join(_slot_label(s) for s in _all_rejected_sc)
        st.markdown(f":red[All scenarios rejected:] {_rej_labels}")
        st.caption("Click **Generate Scenarios** above to create new ones for these slots.")

    # Inline scenario review
    for slot in slots:
        cid = slot["id"]
        sc_list = scenario_map.get(cid, [])
        if not sc_list:
            continue
        has_accepted = any(s.get("status") == "accepted" for s in sc_list)
        has_draft = any(s.get("status") == "draft" for s in sc_list)

        if has_accepted and not has_draft:
            # Compact accepted card: thumbnail + title + description + motion prompt
            accepted = [s for s in sc_list if s.get("status") == "accepted"][0]
            _ac1, _ac2 = st.columns([1, 5])
            with _ac1:
                _slot_thumbnail(slot, width=80)
            with _ac2:
                st.markdown(f":green[{_slot_label(slot)}] — **{accepted.get('title', '')}**")
                if accepted.get("description"):
                    st.caption(accepted["description"][:200])
                _detail_cols = st.columns([2, 1])
                with _detail_cols[0]:
                    if accepted.get("motion_prompt"):
                        with st.popover("Motion prompt"):
                            st.text(accepted["motion_prompt"])
                with _detail_cols[1]:
                    render_inline_review(
                        accepted["id"], "scenario", "accepted",
                        f"{key_prefix}_sc_{cid}",
                        calendar_id=cid, accept_creative_status="scenario_accepted",
                    )
            continue

        st.markdown(f"**{_slot_label(slot)}**")
        _th_col, _v_col = st.columns([1, 4])
        with _th_col:
            _slot_thumbnail(slot, width=120)
        with _v_col:
            draft_sc = [s for s in sc_list if s.get("status") == "draft"]
            accepted_sc = [s for s in sc_list if s.get("status") == "accepted"]
            all_rev = accepted_sc + draft_sc
            if all_rev:
                vcols = st.columns(min(len(all_rev), 3))
                for vi, sc in enumerate(all_rev[:3]):
                    with vcols[vi]:
                        mood = sc.get("mood", "?")
                        title = sc.get("title", "Untitled")
                        sc_status = sc.get("status", "draft")
                        sc_color = STATUS_COLORS.get(sc_status, "gray")
                        st.markdown(f":{sc_color}[**{mood.upper()}**]")
                        st.markdown(f"*{title}*")
                        if sc.get("description"):
                            st.caption(sc["description"][:120])
                        if sc.get("motion_prompt"):
                            with st.popover("Motion prompt"):
                                st.text(sc["motion_prompt"])
                        if sc_status == "draft":
                            if st.button("Accept", key=f"{key_prefix}_sc_acc_{sc['id']}",
                                         type="primary", use_container_width=True):
                                accept_scenario_reject_others(sc["id"], cid)
                                st.rerun()
                        elif sc_status == "accepted":
                            st.markdown(":green[ACCEPTED]")
        st.markdown("---")

    needs_action = sc_eligible > 0 or sc_need_review > 0
    return sc_accepted, needs_action


def _render_video_step(slots, key_prefix, default_duration, duration_options, aspect_default="9:16",
                       video_model_override: str = None):
    """Render video generation + inline review. Returns (accepted_count, needs_action).

    video_model_override: if set, forces this model instead of route-based default.
    """
    slot_ids = [s["id"] for s in slots]

    # Settings row
    c1, c2 = st.columns(2)
    vid_duration = c1.selectbox("Duration (s)", duration_options,
                                index=duration_options.index(default_duration) if default_duration in duration_options else 0,
                                key=f"{key_prefix}_vid_dur")
    vid_aspect = c2.selectbox("Aspect", ["9:16", "16:9", "1:1"], key=f"{key_prefix}_vid_ar")

    vid_active_slots = [
        cid for cid in slot_ids
        if any(v.get("status") != "rejected" for v in video_map.get(cid, []))
    ]
    vid_accepted = sum(
        1 for cid in slot_ids
        if any(v.get("status") == "accepted" for v in video_map.get(cid, []))
    )
    vid_need_review = sum(
        1 for cid in slot_ids
        if cid in video_map
        and not any(v.get("status") == "accepted" for v in video_map.get(cid, []))
        and any(v.get("status") == "completed" for v in video_map.get(cid, []))
    )
    # Need accepted scenario to be eligible for video
    sc_accepted_ids = {
        cid for cid in slot_ids
        if any(s.get("status") == "accepted" for s in scenario_map.get(cid, []))
    }
    vid_eligible = sum(1 for cid in sc_accepted_ids if cid not in vid_active_slots)
    vid_blocked = len(slots) - len(sc_accepted_ids)

    st.progress(vid_accepted / max(len(slots), 1),
                text=f"Videos: {vid_accepted}/{len(slots)} accepted")

    if vid_need_review > 0:
        _vid_review_labels = [
            _slot_label(s) for s in slots
            if s["id"] in video_map
            and not any(v.get("status") == "accepted" for v in video_map.get(s["id"], []))
            and any(v.get("status") == "completed" for v in video_map.get(s["id"], []))
        ]
        st.markdown(f":orange[Review needed:] {', '.join(_vid_review_labels)}")
    if vid_blocked > 0:
        st.caption(f"{vid_blocked} waiting on scenario")

    if vid_eligible > 0:
        _est_model = video_model_override or slots[0].get("_video_model", "kling-v2.1")
        vid_est = estimate_video_cost(vid_eligible, _est_model, vid_duration)
        if st.button(
            f"Generate Videos ({vid_eligible})",
            type="primary", key=f"{key_prefix}_run_vid",
            help=f"~${vid_est['total']:.2f}",
        ):
            eligible = [
                s for s in slots
                if s["id"] in sc_accepted_ids and s["id"] not in vid_active_slots
            ]
            progress_bar = st.progress(0, text="Starting video generation...")

            def _cb(i, total, msg):
                progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

            _gen_model = video_model_override or "kling-v2.1"
            with st.spinner(f"Generating videos for {len(eligible)} slots..."):
                result = batch_generate_videos(
                    slots=eligible, video_model=_gen_model,
                    duration=vid_duration, aspect_ratio=vid_aspect,
                    progress_callback=_cb,
                )
            progress_bar.empty()
            st.success(
                f"{result['success']} generated, {result['skipped']} skipped, "
                f"{result['failed']} failed | ${result['total_cost']:.2f}"
            )
            if result["errors"]:
                for err in result["errors"]:
                    st.warning(err)
            st.rerun()
    elif len(sc_accepted_ids) == 0:
        st.info("Accept scenarios first")

    # Show slots with all-rejected videos (need regeneration)
    _all_rejected_vid = [
        s for s in slots
        if s["id"] in video_map
        and all(v.get("status") == "rejected" for v in video_map.get(s["id"], []))
        and s["id"] in sc_accepted_ids  # has accepted scenario
    ]
    if _all_rejected_vid:
        _rej_vid_labels = ", ".join(_slot_label(s) for s in _all_rejected_vid)
        st.markdown(f":red[All videos rejected:] {_rej_vid_labels}")
        st.caption("Click **Generate Videos** above to create new ones for these slots.")

    # Inline video review
    for slot in slots:
        cid = slot["id"]
        vid_list = video_map.get(cid, [])
        if not vid_list:
            continue

        # Show all non-rejected videos (including accepted — with re-reject option)
        active_vids = [v for v in vid_list if v.get("status") in ("completed", "draft", "accepted")]
        if not active_vids:
            continue

        for vj in active_vids:
            is_accepted = vj.get("status") == "accepted"
            # Get scenario title for context
            _sc = fetch_accepted_scenario_for_calendar(cid)
            _sc_title = _sc.get("title", "") if _sc else ""

            _vc1, _vc2, _vc3 = st.columns([1, 2, 1])
            with _vc1:
                _slot_thumbnail(slot, width=80)
                if _sc_title:
                    st.caption(f"*{_sc_title}*")
            with _vc2:
                _label = f":green[{_slot_label(slot)}]" if is_accepted else f"**{_slot_label(slot)}**"
                st.markdown(_label)
                _vid_drive = vj.get("drive_file_id")
                if _vid_drive:
                    try:
                        _vbytes = download_file_bytes(_vid_drive)
                        st.video(_vbytes)
                    except Exception:
                        if vj.get("result_url"):
                            st.video(vj["result_url"])
                elif vj.get("result_url"):
                    st.video(vj["result_url"])
            with _vc3:
                params = vj.get("params", {})
                if isinstance(params, str):
                    params = json.loads(params)
                if params.get("model"):
                    st.caption(params["model"])
                if vj.get("cost_usd"):
                    st.caption(f"${vj['cost_usd']:.2f}")
                render_inline_review(
                    vj["id"], "video", vj.get("status", "completed"),
                    f"{key_prefix}_vid_{cid}",
                    calendar_id=cid, accept_creative_status="video_accepted",
                )
        st.markdown("---")

    needs_action = vid_eligible > 0 or vid_need_review > 0
    return vid_accepted, needs_action


def _render_music_step(slots, key_prefix, default_duration=10):
    """Render music generation + inline review. Returns (accepted_count, needs_action)."""
    slot_ids = [s["id"] for s in slots]

    c1, _ = st.columns(2)
    mus_duration = c1.slider("Music duration (s)", 5, 30, default_duration, key=f"{key_prefix}_mus_dur")

    mus_active_slots = [
        cid for cid in slot_ids
        if any(m.get("status") != "rejected" for m in music_map.get(cid, []))
    ]
    mus_accepted = sum(
        1 for cid in slot_ids
        if any(m.get("status") == "accepted" for m in music_map.get(cid, []))
    )
    # Ready for music: accepted video or slideshow done
    music_ready_ids = set()
    for s in slots:
        cid = s["id"]
        if any(v.get("status") == "accepted" for v in video_map.get(cid, [])):
            music_ready_ids.add(cid)
        if cid in slideshow_map:
            music_ready_ids.add(cid)
    mus_eligible = sum(1 for cid in music_ready_ids if cid not in mus_active_slots)

    st.progress(mus_accepted / max(len(slots), 1),
                text=f"Music: {mus_accepted}/{len(slots)} accepted")

    if mus_eligible > 0:
        mus_est = estimate_music_cost(mus_eligible, mus_duration)
        if st.button(
            f"Generate Music ({mus_eligible})",
            type="primary", key=f"{key_prefix}_run_mus",
            help=f"~${mus_est['total']:.2f}",
        ):
            eligible = [s for s in slots if s["id"] in music_ready_ids and s["id"] not in mus_active_slots]
            progress_bar = st.progress(0, text="Starting music generation...")

            def _cb(i, total, msg):
                progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

            with st.spinner(f"Generating music for {len(eligible)} slots..."):
                result = batch_generate_music(
                    slots=eligible, music_duration=mus_duration, progress_callback=_cb,
                )
            progress_bar.empty()
            st.success(
                f"{result['success']} generated, {result['skipped']} skipped, "
                f"{result['failed']} failed | ${result['total_cost']:.4f}"
            )
            if result["errors"]:
                for err in result["errors"]:
                    st.warning(err)
            st.rerun()
    elif len(music_ready_ids) == 0:
        st.info("Accept videos first")

    # Inline music review
    for slot in slots:
        cid = slot["id"]
        mus_list = music_map.get(cid, [])
        if not mus_list:
            continue

        # Show all non-rejected music (including accepted — with re-reject option)
        active_mus = [m for m in mus_list if m.get("status") in ("draft", "accepted")]
        if not active_mus:
            continue

        for mu in active_mus:
            is_accepted = mu.get("status") == "accepted"
            _label = f":green[{_slot_label(slot)}]" if is_accepted else f"**{_slot_label(slot)}**"
            _mc1, _mc2 = st.columns([2, 1])
            with _mc1:
                st.markdown(_label)
                _played = False
                if mu.get("drive_file_id"):
                    try:
                        _mu_bytes = download_file_bytes(mu["drive_file_id"])
                        st.audio(_mu_bytes, format="audio/wav")
                        _played = True
                    except Exception:
                        pass
                if not _played and mu.get("audio_url") and "drive.google.com" not in mu.get("audio_url", ""):
                    st.audio(mu["audio_url"])
            with _mc2:
                render_inline_review(
                    mu["id"], "music", mu.get("status", "draft"),
                    f"{key_prefix}_mus_{cid}",
                    calendar_id=cid, accept_creative_status="music_accepted",
                )
        st.markdown("---")

    needs_action = mus_eligible > 0
    return mus_accepted, needs_action


def _render_composite_step(slots, key_prefix, default_volume=0.3):
    """Render composite generation. Returns (done_count, needs_action)."""
    slot_ids = [s["id"] for s in slots]

    c1, _ = st.columns(2)
    comp_volume = c1.slider("Music volume", 0.1, 1.0, default_volume, step=0.1, key=f"{key_prefix}_comp_vol")

    comp_active_slots = [
        cid for cid in slot_ids
        if any(c.get("status") != "rejected" for c in composite_map.get(cid, []))
    ]
    comp_done = len(comp_active_slots)

    # Ready for composite: accepted video/slideshow AND accepted music
    comp_ready = 0
    for s in slots:
        cid = s["id"]
        has_video = (
            any(v.get("status") == "accepted" for v in video_map.get(cid, []))
            or cid in slideshow_map
        )
        has_music = any(m.get("status") == "accepted" for m in music_map.get(cid, []))
        if has_video and has_music:
            comp_ready += 1
    comp_eligible = max(0, comp_ready - comp_done)

    st.progress(comp_done / max(len(slots), 1),
                text=f"Video + Music: {comp_done}/{len(slots)} done")

    if comp_eligible > 0:
        if st.button(
            f"Add Music to Video ({comp_eligible})",
            type="primary", key=f"{key_prefix}_run_comp",
            help="Free (FFmpeg) — merges accepted video + accepted music",
        ):
            eligible = [
                s for s in slots
                if s["id"] not in comp_active_slots
                and (any(v.get("status") == "accepted" for v in video_map.get(s["id"], []))
                     or s["id"] in slideshow_map)
                and any(m.get("status") == "accepted" for m in music_map.get(s["id"], []))
            ]
            progress_bar = st.progress(0, text="Adding music to videos...")

            def _cb(i, total, msg):
                progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

            with st.spinner(f"Merging video + music for {len(eligible)} slots..."):
                result = batch_composite(slots=eligible, volume=comp_volume, progress_callback=_cb)
            progress_bar.empty()
            st.success(
                f"{result['success']} merged, {result['skipped']} skipped, "
                f"{result['failed']} failed"
            )
            if result["errors"]:
                for err in result["errors"]:
                    st.warning(err)
            st.rerun()

    # Show done composites with video player
    for s in slots:
        cid = s["id"]
        comp_list = composite_map.get(cid, [])
        active_comp = [c for c in comp_list if c.get("status") != "rejected"]
        if not active_comp:
            continue
        comp = active_comp[0]
        _cc1, _cc2 = st.columns([3, 1])
        with _cc1:
            st.markdown(f":green[{_slot_label(s)}] — video with music")
            _comp_drive = comp.get("drive_file_id")
            if _comp_drive:
                try:
                    _comp_bytes = download_file_bytes(_comp_drive)
                    st.video(_comp_bytes)
                except Exception:
                    if comp.get("result_url"):
                        st.video(comp["result_url"])
            elif comp.get("result_url"):
                st.video(comp["result_url"])
        with _cc2:
            st.caption("FFmpeg (free)")

    return comp_done, comp_eligible > 0


def _render_caption_step(slots, key_prefix, exclude_carousel=True):
    """Render caption generation for eligible slots. Returns done_count."""
    # Determine caption-ready slots
    caption_ready = set()
    for s in slots:
        sid = s["id"]
        route = s.get("target_format") or "feed"
        if route in ("story", ""):
            route = "feed"
        if route == "reel":
            route = "reel-veo"
        if exclude_carousel and route == "carousel":
            continue
        if route == "feed":
            caption_ready.add(sid)
        elif route in ("reel-kling", "reel-slideshow"):
            if any(c.get("status") != "rejected" for c in composite_map.get(sid, [])):
                caption_ready.add(sid)
        elif route == "reel-veo":
            if any(v.get("status") == "accepted" for v in video_map.get(sid, [])):
                caption_ready.add(sid)

    cap_have = sum(1 for cid in [s["id"] for s in slots] if cid in content_map)
    cap_need = sum(1 for cid in caption_ready if cid not in content_map)

    # Settings row
    c1, c2, c3 = st.columns(3)
    cap_model = c1.selectbox("Caption Model", ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
                             key=f"{key_prefix}_cap_model")
    cap_img = c2.checkbox("Include image", value=True, key=f"{key_prefix}_cap_img")
    cap_tone = c3.selectbox("Tone", list(TONE_LABELS.keys()),
                            format_func=lambda k: TONE_LABELS[k],
                            key=f"{key_prefix}_cap_tone")

    st.progress(cap_have / max(len(slots), 1),
                text=f"Captions: {cap_have}/{len(slots)} done")

    _not_ready = len(slots) - len(caption_ready)
    if _not_ready > 0:
        st.caption(f"{_not_ready} slot{'s' if _not_ready != 1 else ''} not ready — complete previous steps first")

    if cap_need > 0:
        entries_to_caption = [s for s in slots if s["id"] in caption_ready and s["id"] not in content_map]
        cap_est = estimate_batch_cost(entries_to_caption, cap_model, cap_img)
        if st.button(
            f"Generate Captions ({cap_need})",
            type="primary", key=f"{key_prefix}_run_cap",
            help=f"~${cap_est['estimated_cost_usd']:.2f}",
        ):
            progress_bar = st.progress(0, text="Generating captions...")
            success_count = 0
            total_cost = 0.0
            total = len(entries_to_caption)

            for i, entry in enumerate(entries_to_caption):
                try:
                    image_b64 = None
                    if cap_img:
                        mid = entry.get("manual_media_id") or entry.get("media_id")
                        mi = media_info.get(mid, {}) if mid else {}
                        dfid = mi.get("drive_file_id")
                        if dfid:
                            from src.utils import encode_image_bytes
                            raw = download_file_bytes(dfid)
                            image_b64 = encode_image_bytes(raw)

                    result = generate_for_slot(
                        entry=entry, model=cap_model, include_image=cap_img,
                        image_base64=image_b64, tone=cap_tone,
                    )
                    if result:
                        success_count += 1
                        total_cost += result.get("cost_usd", 0)
                        update_calendar_creative_status(entry["id"], "captions_done")
                except Exception as e:
                    st.warning(f"Failed for {entry['post_date']} S{entry.get('slot_index', 1)}: {e}")
                progress_bar.progress((i + 1) / total, text=f"Generated {i + 1}/{total}...")

            progress_bar.empty()
            st.success(f"Captions: {success_count}/{total} (${total_cost:.4f})")
            st.rerun()
    elif cap_have > 0 and cap_need == 0:
        st.success("All eligible slots have captions!")

    return cap_have


# -------------------------------------------------------
# Route summary
# -------------------------------------------------------
st.markdown("### Route Summary")
_route_cols = st.columns(5)
for i, (route, label) in enumerate(ROUTE_LABELS.items()):
    count = len(route_groups.get(route, []))
    color = ROUTE_COLORS[route]
    _route_cols[i].markdown(f":{color}[**{label}**]  \n{count} slots")

# Overall readiness
total_slots = len(slots_with_media)
_ready_count = 0
for s in slots_with_media:
    cid = s["id"]
    route = s.get("target_format") or "feed"
    if route == "story":
        route = "feed"
    if route == "reel":
        route = "reel-veo"
    if route == "feed":
        if cid in content_map:
            _ready_count += 1
    elif route == "carousel":
        if cid in carousel_map and any(c.get("status") == "accepted" for c in carousel_map.get(cid, [])):
            _ready_count += 1
    elif route in ROUTES_NEED_MUSIC:
        if cid in composite_map:
            _ready_count += 1
    elif route == "reel-veo":
        if any(v.get("status") == "accepted" for v in video_map.get(cid, [])):
            _ready_count += 1

st.progress(_ready_count / max(total_slots, 1),
            text=f"**{_ready_count}/{total_slots}** slots production-ready")


# -------------------------------------------------------
# Route Tabs
# -------------------------------------------------------
tab_labels = []
for route, label in ROUTE_LABELS.items():
    rslots = route_groups.get(route, [])
    count = len(rslots)
    if count == 0:
        tab_labels.append(f"{label} (0)")
    else:
        # Count how many are fully done (production-ready)
        done = 0
        for s in rslots:
            cid = s["id"]
            if route == "feed":
                if cid in content_map:
                    done += 1
            elif route == "carousel":
                if any(c.get("status") == "accepted" for c in carousel_map.get(cid, [])):
                    done += 1
            elif route in ROUTES_NEED_MUSIC:
                if any(c.get("status") != "rejected" for c in composite_map.get(cid, [])):
                    done += 1
            elif route == "reel-veo":
                if any(v.get("status") == "accepted" for v in video_map.get(cid, [])):
                    done += 1
        remaining = count - done
        if remaining == 0:
            tab_labels.append(f"{label} ({count}) \u2714")
        else:
            tab_labels.append(f"{label} ({remaining}/{count})")

tabs = st.tabs(tab_labels)

# -------------------------------------------------------
# TAB: Image Posts
# -------------------------------------------------------
with tabs[0]:
    feed_slots = route_groups.get("feed", [])
    if not feed_slots:
        st.info("No image post slots in this date range.")
    else:
        _render_caption_step(feed_slots, "feed", exclude_carousel=False)

# -------------------------------------------------------
# TAB: Carousel
# -------------------------------------------------------
with tabs[1]:
    carousel_slots_list = route_groups.get("carousel", [])
    if not carousel_slots_list:
        st.info("No carousel slots in this date range.")
    else:
        # Settings row
        _cc1, _cc2 = st.columns(2)
        carousel_slides = _cc1.slider("Images per carousel", 3, 10, 5, key="car_slides")
        carousel_model = _cc2.selectbox("Model", ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
                                        key="car_model")

        carousel_slot_ids = [s["id"] for s in carousel_slots_list]
        _car_active = sum(
            1 for cid in carousel_slot_ids
            if cid in carousel_map and any(c.get("status") != "rejected" for c in carousel_map.get(cid, []))
        )
        _car_accepted = sum(
            1 for cid in carousel_slot_ids
            if cid in carousel_map and any(c.get("status") == "accepted" for c in carousel_map.get(cid, []))
        )
        _car_eligible = len(carousel_slots_list) - _car_active

        st.progress(_car_accepted / max(len(carousel_slots_list), 1),
                    text=f"Carousels: {_car_accepted}/{len(carousel_slots_list)} accepted")

        if _car_eligible > 0:
            car_est = estimate_carousel_cost(_car_eligible, carousel_model)
            if st.button(
                f"Generate Carousels ({_car_eligible})",
                type="primary", key="car_run",
                help=f"~${car_est['total']:.2f}",
            ):
                eligible = [
                    s for s in carousel_slots_list
                    if s["id"] not in carousel_map
                    or not any(c.get("status") != "rejected" for c in carousel_map.get(s["id"], []))
                ]
                progress_bar = st.progress(0, text="Starting carousel generation...")

                def _car_cb(i, total, msg):
                    progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

                with st.spinner(f"Generating carousels for {len(eligible)} slots..."):
                    result = batch_generate_carousels(
                        slots=eligible, model=carousel_model, slide_count=carousel_slides,
                        progress_callback=_car_cb,
                    )
                progress_bar.empty()
                st.success(
                    f"{result['success']} generated, {result['skipped']} skipped, "
                    f"{result['failed']} failed | ${result['total_cost']:.4f}"
                )
                if result["errors"]:
                    for err in result["errors"]:
                        st.warning(err)
                st.rerun()

        # Inline carousel review
        for slot in carousel_slots_list:
            cid = slot["id"]
            car_list = carousel_map.get(cid, [])
            if not car_list:
                continue
            car = car_list[0]
            car_status = car.get("status", "draft")
            car_color = STATUS_COLORS.get(car_status, "gray")

            st.markdown(f":{car_color}[{car_status.upper()}] **{_slot_label(slot)}** — {car.get('title', '')}")

            _car_media_ids = car.get("media_ids", [])
            if _car_media_ids:
                _thumb_cols = st.columns(min(len(_car_media_ids), 6))
                for ti, tmid in enumerate(_car_media_ids[:6]):
                    with _thumb_cols[ti]:
                        _tm_dfid = media_info.get(tmid, {}).get("drive_file_id")
                        if not _tm_dfid:
                            _extra = fetch_media_info([tmid])
                            _tm_dfid = _extra.get(tmid, {}).get("drive_file_id")
                        if _tm_dfid:
                            try:
                                _tb64 = _fetch_thumbnail_b64(_tm_dfid)
                                if _tb64:
                                    st.image(f"data:image/jpeg;base64,{_tb64}", use_container_width=True)
                            except Exception:
                                st.caption("-")

            if car.get("caption_es"):
                st.caption(car["caption_es"][:150] + ("..." if len(car.get("caption_es", "")) > 150 else ""))

            render_inline_review(
                car["id"], "carousel", car_status, f"car_{cid}",
                calendar_id=cid, accept_creative_status="carousel_accepted",
            )
            st.markdown("---")

# -------------------------------------------------------
# TAB: Reel (Kling)
# -------------------------------------------------------
with tabs[2]:
    kling_slots = route_groups.get("reel-kling", [])
    if not kling_slots:
        st.info("No Kling reel slots in this date range.")
    else:
        # Step 1: Scenarios
        with st.expander("Step 1: Scenarios", expanded=True):
            kling_sc_accepted, kling_sc_action = _render_scenario_step(kling_slots, "kling")

        # Step 2: Videos
        with st.expander(f"Step 2: Videos — {kling_sc_accepted} scenarios ready", expanded=not kling_sc_action):
            kling_vid_accepted, kling_vid_action = _render_video_step(
                kling_slots, "kling", default_duration=5, duration_options=[5, 10],
            )

        # Step 3: Music
        with st.expander(f"Step 3: Music — {kling_vid_accepted} videos ready",
                         expanded=not kling_sc_action and not kling_vid_action):
            kling_mus_accepted, kling_mus_action = _render_music_step(kling_slots, "kling")

        # Step 4: Video + Music
        with st.expander("Step 4: Video + Music",
                         expanded=not kling_sc_action and not kling_vid_action and not kling_mus_action):
            kling_comp_done, kling_comp_action = _render_composite_step(kling_slots, "kling")

        # Step 5: Captions
        with st.expander("Step 5: Captions", expanded=False):
            _render_caption_step(kling_slots, "kling_cap")

# -------------------------------------------------------
# TAB: Reel (Veo)
# -------------------------------------------------------
with tabs[3]:
    veo_slots = route_groups.get("reel-veo", [])
    if not veo_slots:
        st.info("No Veo reel slots in this date range.")
    else:
        # Veo model selector
        _veo_model = st.selectbox(
            "Veo Model", ["veo-3.1-fast", "veo-3.1"],
            format_func=lambda m: "Veo 3.1 Fast (~$0.15/s)" if m == "veo-3.1-fast" else "Veo 3.1 Standard (~$0.75/s)",
            key="veo_tab_model",
        )

        # Step 1: Scenarios
        with st.expander("Step 1: Scenarios", expanded=True):
            veo_sc_accepted, veo_sc_action = _render_scenario_step(veo_slots, "veo")

        # Step 2: Videos (Veo has native audio — no music step)
        with st.expander(f"Step 2: Videos — {veo_sc_accepted} scenarios ready", expanded=not veo_sc_action):
            veo_vid_accepted, veo_vid_action = _render_video_step(
                veo_slots, "veo", default_duration=4, duration_options=[4, 6, 8],
                video_model_override=_veo_model,
            )

        # Step 3: Captions
        with st.expander("Step 3: Captions", expanded=False):
            _render_caption_step(veo_slots, "veo_cap")

# -------------------------------------------------------
# TAB: Slideshow
# -------------------------------------------------------
with tabs[4]:
    ss_slots = route_groups.get("reel-slideshow", [])
    if not ss_slots:
        st.info("No slideshow slots in this date range.")
    else:
        # Step 1: Slideshow generation
        _ss1, _ss2 = st.columns(2)
        ss_slides = _ss1.slider("Images per slideshow", 3, 10, 5, key="ss_slides")
        ss_dur = _ss2.slider("Seconds/slide", 2.0, 5.0, 3.0, step=0.5, key="ss_dur")

        ss_slot_ids = [s["id"] for s in ss_slots]
        _ss_done = sum(1 for cid in ss_slot_ids if cid in slideshow_map)
        _ss_eligible = len(ss_slots) - _ss_done

        with st.expander(f"Step 1: Slideshows — {_ss_done}/{len(ss_slots)} done", expanded=_ss_eligible > 0):
            st.progress(_ss_done / max(len(ss_slots), 1),
                        text=f"Slideshows: {_ss_done}/{len(ss_slots)}")
            if _ss_eligible > 0:
                if st.button(
                    f"Generate Slideshows ({_ss_eligible})",
                    type="primary", key="ss_run",
                    help="Free (FFmpeg)",
                ):
                    eligible = [s for s in ss_slots if s["id"] not in slideshow_map]
                    progress_bar = st.progress(0, text="Starting slideshow generation...")

                    def _ss_cb(i, total, msg):
                        progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

                    with st.spinner(f"Generating slideshows for {len(eligible)} slots..."):
                        result = batch_generate_slideshows(
                            slots=eligible, slide_count=ss_slides,
                            duration_per_slide=ss_dur, progress_callback=_ss_cb,
                        )
                    progress_bar.empty()
                    st.success(
                        f"{result['success']} generated, {result['skipped']} skipped, "
                        f"{result['failed']} failed"
                    )
                    if result["errors"]:
                        for err in result["errors"]:
                            st.warning(err)
                    st.rerun()

        # Step 2: Music
        with st.expander("Step 2: Music", expanded=_ss_done > 0 and _ss_eligible == 0):
            ss_mus_accepted, ss_mus_action = _render_music_step(ss_slots, "ss")

        # Step 3: Video + Music
        with st.expander("Step 3: Video + Music",
                         expanded=not ss_mus_action and _ss_done > 0):
            ss_comp_done, ss_comp_action = _render_composite_step(ss_slots, "ss")

        # Step 4: Captions
        with st.expander("Step 4: Captions", expanded=False):
            _render_caption_step(ss_slots, "ss_cap")

# -------------------------------------------------------
# What's next guidance
# -------------------------------------------------------
st.divider()

# Compute overall status for guidance
_slots_with_captions = sum(1 for s in slots_with_media if s["id"] in content_map)
_slots_validated = sum(1 for s in calendar_data if s.get("status") == "validated")

if _ready_count == total_slots and _slots_with_captions == total_slots:
    st.markdown("### \u2192 What's next")
    if _slots_validated < total_slots:
        st.info(
            f"All {total_slots} slots have content! "
            f"**{_slots_validated}/{total_slots}** are validated. "
            f"Go to **Calendar \u2192 List view** to review and **Validate** each slot, then **Publish to Instagram**."
        )
    else:
        st.success(
            f"All {total_slots} slots validated! "
            f"Go to **Calendar** to publish or schedule them on Instagram."
        )
    st.page_link("pages/9_Calendar.py", label="Go to Calendar", icon=":material/calendar_month:")
elif _ready_count < total_slots:
    _remaining = total_slots - _ready_count
    st.caption(
        f"{_remaining} slot{'s' if _remaining != 1 else ''} still in progress. "
        f"Complete all steps above, then go to **Calendar** to validate and publish."
    )

st.page_link("pages/11_Drafts_Review.py", label="Content Drafts (all content) ->", icon=":material/rate_review:")
