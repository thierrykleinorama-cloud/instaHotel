"""
InstaHotel — Production Pipeline
Guided stepper with inline review: generate AND review in one page.
No more bouncing between pages.
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
from src.services.editorial_queries import fetch_calendar_range
from src.services.creative_queries import (
    fetch_scenarios_for_calendar_ids,
    fetch_videos_for_calendar_ids,
    fetch_music_for_calendar_ids,
    fetch_composite_for_calendar_ids,
    fetch_slideshows_for_calendar_ids,
    fetch_media_info,
    accept_scenario_reject_others,
    update_scenario_feedback,
    update_music_feedback,
    update_job_feedback,
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

sidebar_css()
page_title("Production Pipeline", "Generate and review content — one page, guided steps")

ROUTE_LABELS = {
    "feed": "Image Post",
    "carousel": "Carousel",
    "reel-kling": "Reel (Kling)",
    "reel-veo": "Reel (Veo)",
    "reel-slideshow": "Reel (Slideshow)",
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
# Sidebar controls
# -------------------------------------------------------
with st.sidebar:
    st.subheader("Date Range")
    today = date.today()
    default_start = today - timedelta(days=today.weekday())

    # Check if there's in-progress creative work in a recent range
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

    st.divider()
    st.subheader("Scenario Settings")
    scenario_count = st.slider("Scenarios per slot", 2, 5, 3, key="bp_scenario_count")
    scenario_include_image = st.checkbox("Include image in prompt", value=True, key="bp_scenario_img")
    scenario_model = st.selectbox(
        "Model", ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
        key="bp_scenario_model",
    )

    st.divider()
    st.subheader("Video Settings")
    st.caption("Video model is set per-slot by route (Kling or Veo)")
    video_duration_kling = st.selectbox("Kling Duration", [5, 10], index=0, key="bp_video_dur_kling")
    video_duration_veo = st.selectbox("Veo Duration", [4, 6, 8], index=0, key="bp_video_dur_veo")
    video_aspect = st.selectbox("Aspect Ratio", ["9:16", "16:9", "1:1"], key="bp_video_ar")

    st.divider()
    st.subheader("Music Settings")
    music_duration = st.slider("Duration (sec)", 5, 30, 10, key="bp_music_dur")

    st.divider()
    st.subheader("Composite Settings")
    composite_volume = st.slider("Music Volume", 0.1, 1.0, 0.3, step=0.1, key="bp_comp_vol")

    st.divider()
    st.subheader("Carousel Settings")
    carousel_slides = st.slider("Images per carousel", 3, 10, 5, key="bp_carousel_slides")

    st.divider()
    st.subheader("Slideshow Settings")
    slideshow_slides = st.slider("Images per slideshow", 3, 10, 5, key="bp_ss_slides")
    slideshow_duration = st.slider("Seconds per slide", 2.0, 5.0, 3.0, step=0.5, key="bp_ss_dur")

    st.divider()
    st.subheader("Caption Settings")
    caption_model = st.selectbox(
        "Caption Model", ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
        key="bp_caption_model",
    )
    caption_include_image = st.checkbox("Include image in caption prompt", value=False, key="bp_caption_img")
    from src.prompts.tone_variants import TONE_LABELS
    caption_tone = st.selectbox(
        "Tone", list(TONE_LABELS.keys()),
        format_func=lambda k: TONE_LABELS[k],
        key="bp_caption_tone",
    )

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
# Route summary + overall progress
# -------------------------------------------------------
st.markdown("### Route Summary")
_route_cols = st.columns(5)
for i, (route, label) in enumerate(ROUTE_LABELS.items()):
    count = len(route_groups.get(route, []))
    color = ROUTE_COLORS[route]
    _route_cols[i].markdown(f":{color}[**{label}**]  \n{count} slots")

# Compute overall readiness
total_slots = len(slots_with_media)
_ready_count = 0
for s in slots_with_media:
    cid = s["id"]
    route = s.get("target_format") or "feed"
    if route == "story":
        route = "feed"
    if route == "reel":
        route = "reel-kling"
    if route == "feed":
        # Feed slots are ready when they have captions
        if cid in content_map:
            _ready_count += 1
    elif route == "carousel":
        if cid in carousel_map:
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
# Helpers
# -------------------------------------------------------
reel_slots = route_groups.get("reel-kling", []) + route_groups.get("reel-veo", [])
reel_kling_slots = route_groups.get("reel-kling", [])
reel_veo_slots = route_groups.get("reel-veo", [])
music_slots = route_groups.get("reel-kling", []) + route_groups.get("reel-slideshow", [])
reel_ids = [s["id"] for s in reel_slots]
music_slot_ids = [s["id"] for s in music_slots]


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
    route = slot.get("target_format") or "feed"
    if route == "reel":
        route = "reel-kling"
    rlabel = ROUTE_LABELS.get(route, route)
    return f"{pd} S{si} | {cat} | {rlabel}"


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


# -------------------------------------------------------
# REEL PIPELINE
# -------------------------------------------------------
if reel_slots:
    st.markdown("---")
    st.markdown(f"### Reel Pipeline ({len(reel_slots)} reel slots)")

    # --- Step 1: Scenarios ---
    _sc_slots_with = [cid for cid in reel_ids if cid in scenario_map]
    _sc_accepted = sum(
        1 for cid in reel_ids
        if any(s.get("status") == "accepted" for s in scenario_map.get(cid, []))
    )
    _sc_need_review = sum(
        1 for cid in reel_ids
        if cid in scenario_map
        and not any(s.get("status") == "accepted" for s in scenario_map.get(cid, []))
        and any(s.get("status") == "draft" for s in scenario_map.get(cid, []))
    )
    _sc_eligible = len(reel_slots) - len(_sc_slots_with)

    # Determine auto-expand: expand the first step that needs action
    _sc_needs_action = _sc_eligible > 0 or _sc_need_review > 0
    _sc_icon = "green" if _sc_accepted == len(reel_slots) else ("orange" if len(_sc_slots_with) > 0 else "gray")

    with st.expander(
        f":{_sc_icon}[Step 1: SCENARIOS] — {_sc_accepted}/{len(reel_slots)} slots ready",
        expanded=_sc_needs_action,
    ):
        # Status summary
        if _sc_accepted > 0:
            st.markdown(f":green[{_sc_accepted} slot{'s' if _sc_accepted != 1 else ''}: scenario accepted]")
        if _sc_need_review > 0:
            st.markdown(f":orange[{_sc_need_review} slot{'s' if _sc_need_review != 1 else ''}: draft scenarios — REVIEW BELOW]")
        if _sc_eligible > 0:
            sc_est = estimate_scenario_cost(_sc_eligible, scenario_count, scenario_include_image, scenario_model)
            st.markdown(f":gray[{_sc_eligible} slot{'s' if _sc_eligible != 1 else ''}: need scenarios]")

        # Generate button
        if _sc_eligible > 0:
            if st.button(
                f"Generate Scenarios ({_sc_eligible})",
                type="primary", key="bp_run_scenarios",
                help=f"{scenario_count} concepts x {_sc_eligible} slots ~ ${sc_est['total']:.2f}",
            ):
                eligible = [s for s in reel_slots if s["id"] not in scenario_map]
                progress_bar = st.progress(0, text="Starting scenario generation...")

                def _sc_progress(i, total, msg):
                    progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

                with st.spinner(f"Generating scenarios for {len(eligible)} slots..."):
                    result = batch_generate_scenarios(
                        slots=eligible,
                        count=scenario_count,
                        model=scenario_model,
                        include_image=scenario_include_image,
                        progress_callback=_sc_progress,
                    )
                    st.session_state["bp_scenario_result"] = result

                progress_bar.empty()
                st.success(
                    f"Scenarios: {result['success']} generated, {result['skipped']} skipped, "
                    f"{result['failed']} failed | Cost: ${result['total_cost']:.4f}"
                )
                if result["errors"]:
                    for err in result["errors"]:
                        st.warning(err)
                st.rerun()

        # Inline review: grouped by slot
        for slot in reel_slots:
            cid = slot["id"]
            sc_list = scenario_map.get(cid, [])
            if not sc_list:
                continue
            has_accepted = any(s.get("status") == "accepted" for s in sc_list)
            has_draft = any(s.get("status") == "draft" for s in sc_list)

            if has_accepted and not has_draft:
                # Show compact accepted summary
                accepted = [s for s in sc_list if s.get("status") == "accepted"][0]
                st.markdown(f":green[{_slot_label(slot)}] — accepted: *{accepted.get('title', '')}*")
                continue

            # Show full review UI for this slot
            st.markdown(f"**{_slot_label(slot)}**")

            # Show thumbnail once
            _th_col, _variants_col = st.columns([1, 4])
            with _th_col:
                _slot_thumbnail(slot, width=120)

            with _variants_col:
                # Side-by-side variant columns
                draft_scenarios = [s for s in sc_list if s.get("status") == "draft"]
                accepted_scenarios = [s for s in sc_list if s.get("status") == "accepted"]
                all_reviewable = accepted_scenarios + draft_scenarios

                if all_reviewable:
                    variant_cols = st.columns(min(len(all_reviewable), 3))
                    for vi, sc in enumerate(all_reviewable[:3]):
                        with variant_cols[vi]:
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

                            # Accept-one pattern
                            if sc_status == "draft":
                                if st.button(
                                    "Accept",
                                    key=f"pp_sc_acc_{sc['id']}",
                                    type="primary",
                                    use_container_width=True,
                                ):
                                    accept_scenario_reject_others(sc["id"], cid)
                                    st.rerun()
                            elif sc_status == "accepted":
                                st.markdown(":green[ACCEPTED]")
                            elif sc_status == "rejected":
                                st.markdown(":red[rejected]")

            st.markdown("---")

    # --- Step 2: Videos ---
    _vid_total = sum(1 for cid in reel_ids if cid in video_map)
    _vid_accepted = sum(
        1 for cid in reel_ids
        if any(v.get("status") == "accepted" for v in video_map.get(cid, []))
    )
    _vid_need_review = sum(
        1 for cid in reel_ids
        if cid in video_map
        and not any(v.get("status") == "accepted" for v in video_map.get(cid, []))
        and any(v.get("status") == "completed" for v in video_map.get(cid, []))
    )
    _vid_eligible = _sc_accepted - _vid_total
    _vid_blocked = len(reel_slots) - _sc_accepted
    _vid_icon = "green" if _vid_accepted == len(reel_slots) else ("orange" if _vid_total > 0 else "gray")
    _vid_needs_action = (_vid_eligible > 0 or _vid_need_review > 0) and not _sc_needs_action

    with st.expander(
        f":{_vid_icon}[Step 2: VIDEOS] — {_vid_accepted}/{len(reel_slots)} slots ready",
        expanded=_vid_needs_action,
    ):
        if _vid_accepted > 0:
            st.markdown(f":green[{_vid_accepted} slot{'s' if _vid_accepted != 1 else ''}: video accepted]")
        if _vid_need_review > 0:
            st.markdown(f":orange[{_vid_need_review} slot{'s' if _vid_need_review != 1 else ''}: video needs review]")
        if _vid_blocked > 0:
            st.markdown(f":gray[{_vid_blocked} slot{'s' if _vid_blocked != 1 else ''}: need accepted scenario first]")
        if _vid_eligible > 0:
            _kling_elig = sum(
                1 for s in reel_kling_slots
                if any(sc.get("status") == "accepted" for sc in scenario_map.get(s["id"], []))
                and s["id"] not in video_map
            )
            _veo_elig = max(0, _vid_eligible - _kling_elig)
            vid_est = (
                estimate_video_cost(max(_kling_elig, 0), "kling-v2.1", video_duration_kling)["total"]
                + estimate_video_cost(max(_veo_elig, 0), "veo-3.1-fast", video_duration_veo)["total"]
            )

        # Generate button
        if _vid_eligible > 0:
            if st.button(
                f"Generate Videos ({_vid_eligible})",
                type="primary", key="bp_run_videos",
                help=f"~${vid_est:.2f}",
            ):
                eligible = [
                    s for s in reel_slots
                    if s["id"] not in video_map
                    and any(sc.get("status") == "accepted" for sc in scenario_map.get(s["id"], []))
                ]
                progress_bar = st.progress(0, text="Starting video generation...")

                def _vid_progress(i, total, msg):
                    progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

                with st.spinner(f"Generating videos for {len(eligible)} slots..."):
                    result = batch_generate_videos(
                        slots=eligible,
                        duration=video_duration_kling,
                        aspect_ratio=video_aspect,
                        progress_callback=_vid_progress,
                    )
                    st.session_state["bp_video_result"] = result

                progress_bar.empty()
                st.success(
                    f"Videos: {result['success']} generated, {result['skipped']} skipped, "
                    f"{result['failed']} failed | Cost: ${result['total_cost']:.2f}"
                )
                if result["errors"]:
                    for err in result["errors"]:
                        st.warning(err)
                st.rerun()
        elif _sc_accepted == 0:
            st.info("Accept scenarios first")

        # Inline video review
        for slot in reel_slots:
            cid = slot["id"]
            vid_list = video_map.get(cid, [])
            if not vid_list:
                continue
            has_accepted = any(v.get("status") == "accepted" for v in vid_list)

            if has_accepted:
                accepted_v = [v for v in vid_list if v.get("status") == "accepted"][0]
                st.markdown(f":green[{_slot_label(slot)}] — video accepted")
                continue

            st.markdown(f"**{_slot_label(slot)}**")
            for vj in vid_list:
                if vj.get("status") not in ("completed", "draft"):
                    continue
                _vc1, _vc2 = st.columns([2, 1])
                with _vc1:
                    if vj.get("result_url"):
                        _vid_drive = vj.get("drive_file_id")
                        if _vid_drive:
                            try:
                                _vbytes = download_file_bytes(_vid_drive)
                                st.video(_vbytes)
                            except Exception:
                                st.video(vj["result_url"])
                        else:
                            st.video(vj["result_url"])
                with _vc2:
                    params = vj.get("params", {})
                    if isinstance(params, str):
                        params = json.loads(params)
                    if params.get("model"):
                        st.caption(params["model"])
                    if vj.get("cost_usd"):
                        st.caption(f"${vj['cost_usd']:.2f}")
                    render_inline_review(vj["id"], "video", vj.get("status", "completed"),
                                         f"pp_vid_{cid}")
            st.markdown("---")

    # --- Step 3: Music + Composite ---
    if music_slots:
        _mus_total = sum(1 for cid in music_slot_ids if cid in music_map)
        _mus_accepted = sum(
            1 for cid in music_slot_ids
            if any(m.get("status") == "accepted" for m in music_map.get(cid, []))
        )
        _comp_total = sum(1 for cid in music_slot_ids if cid in composite_map)
        # Ready for music: accepted video (kling) or slideshow done
        _kling_vid_accepted = sum(
            1 for s in reel_kling_slots
            if any(v.get("status") == "accepted" for v in video_map.get(s["id"], []))
        )
        _ss_done = sum(1 for cid in [s["id"] for s in route_groups.get("reel-slideshow", [])]
                       if cid in slideshow_map)
        _music_ready = _kling_vid_accepted + _ss_done
        _mus_eligible = _music_ready - _mus_total
        _comp_eligible = min(_music_ready, _mus_accepted) - _comp_total
        _mus_icon = "green" if _comp_total == len(music_slots) else ("orange" if _mus_total > 0 else "gray")
        _mus_needs_action = (_mus_eligible > 0 or _comp_eligible > 0) and not _vid_needs_action and not _sc_needs_action

        with st.expander(
            f":{_mus_icon}[Step 3: MUSIC + COMPOSITE] — {_comp_total}/{len(music_slots)} slots complete",
            expanded=_mus_needs_action,
        ):
            if _comp_total > 0:
                st.markdown(f":green[{_comp_total} slot{'s' if _comp_total != 1 else ''}: composite done]")
            if _mus_accepted > 0 and _comp_total < _mus_accepted:
                st.markdown(f":orange[{_mus_accepted - _comp_total} slot{'s' if (_mus_accepted - _comp_total) != 1 else ''}: music accepted, needs composite]")
            _mus_blocked = len(music_slots) - _music_ready
            if _mus_blocked > 0:
                st.markdown(f":gray[{_mus_blocked} slot{'s' if _mus_blocked != 1 else ''}: need accepted video first]")

            # Music generate button
            if _mus_eligible > 0:
                mus_est = estimate_music_cost(max(_mus_eligible, 0), music_duration)
                if st.button(
                    f"Generate Music ({_mus_eligible})",
                    type="primary", key="bp_run_music",
                    help=f"~${mus_est['total']:.2f}",
                ):
                    eligible = [
                        s for s in music_slots
                        if s["id"] not in music_map
                        and (
                            any(v.get("status") == "accepted" for v in video_map.get(s["id"], []))
                            or s["id"] in slideshow_map
                        )
                    ]
                    progress_bar = st.progress(0, text="Starting music generation...")

                    def _mus_progress(i, total, msg):
                        progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

                    with st.spinner(f"Generating music for {len(eligible)} slots..."):
                        result = batch_generate_music(
                            slots=eligible,
                            music_duration=music_duration,
                            progress_callback=_mus_progress,
                        )
                        st.session_state["bp_music_result"] = result

                    progress_bar.empty()
                    st.success(
                        f"Music: {result['success']} generated, {result['skipped']} skipped, "
                        f"{result['failed']} failed | Cost: ${result['total_cost']:.4f}"
                    )
                    if result["errors"]:
                        for err in result["errors"]:
                            st.warning(err)
                    st.rerun()
            elif _music_ready == 0:
                st.info("Accept videos first")

            # Inline music review
            for slot in music_slots:
                cid = slot["id"]
                mus_list = music_map.get(cid, [])
                if not mus_list:
                    continue
                has_accepted = any(m.get("status") == "accepted" for m in mus_list)
                if has_accepted:
                    st.markdown(f":green[{_slot_label(slot)}] — music accepted")
                    continue

                st.markdown(f"**{_slot_label(slot)}**")
                for mu in mus_list:
                    if mu.get("status") not in ("draft",):
                        continue
                    _mc1, _mc2 = st.columns([2, 1])
                    with _mc1:
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
                    with _mc2:
                        render_inline_review(mu["id"], "music", mu.get("status", "draft"),
                                             f"pp_mus_{cid}")
                st.markdown("---")

            # Composite button
            if _comp_eligible > 0:
                st.divider()
                if st.button(
                    f"Run Composite ({_comp_eligible})",
                    type="primary", key="bp_run_composite",
                    help="Free (FFmpeg)",
                ):
                    eligible = [
                        s for s in music_slots
                        if s["id"] not in composite_map
                        and (
                            any(v.get("status") == "accepted" for v in video_map.get(s["id"], []))
                            or s["id"] in slideshow_map
                        )
                        and any(m.get("status") == "accepted" for m in music_map.get(s["id"], []))
                    ]
                    progress_bar = st.progress(0, text="Starting composite generation...")

                    def _comp_progress(i, total, msg):
                        progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

                    with st.spinner(f"Compositing {len(eligible)} slots..."):
                        result = batch_composite(
                            slots=eligible,
                            volume=composite_volume,
                            progress_callback=_comp_progress,
                        )
                        st.session_state["bp_composite_result"] = result

                    progress_bar.empty()
                    st.success(
                        f"Composites: {result['success']} generated, {result['skipped']} skipped, "
                        f"{result['failed']} failed"
                    )
                    if result["errors"]:
                        for err in result["errors"]:
                            st.warning(err)
                    st.rerun()

# -------------------------------------------------------
# CAROUSEL PIPELINE
# -------------------------------------------------------
carousel_slots_list = route_groups.get("carousel", [])
if carousel_slots_list:
    st.markdown("---")
    carousel_slot_ids = [s["id"] for s in carousel_slots_list]
    _car_total = sum(1 for cid in carousel_slot_ids if cid in carousel_map)
    _car_eligible = len(carousel_slots_list) - _car_total
    _car_icon = "green" if _car_total == len(carousel_slots_list) else ("orange" if _car_total > 0 else "gray")

    st.markdown(f"### Carousel Pipeline ({len(carousel_slots_list)} slots)")
    with st.expander(
        f":{_car_icon}[Step 1: CAROUSELS] — {_car_total}/{len(carousel_slots_list)} done",
        expanded=_car_eligible > 0,
    ):
        if _car_total > 0:
            st.markdown(f":green[{_car_total} carousel{'s' if _car_total != 1 else ''} generated]")
        if _car_eligible > 0:
            car_est = estimate_carousel_cost(_car_eligible, scenario_model)
            if st.button(
                f"Generate Carousels ({_car_eligible})",
                type="primary", key="bp_run_carousels",
                help=f"~${car_est['total']:.2f}",
            ):
                eligible = [s for s in carousel_slots_list if s["id"] not in carousel_map]
                progress_bar = st.progress(0, text="Starting carousel generation...")

                def _car_progress(i, total, msg):
                    progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

                with st.spinner(f"Generating carousels for {len(eligible)} slots..."):
                    result = batch_generate_carousels(
                        slots=eligible,
                        model=scenario_model,
                        slide_count=carousel_slides,
                        progress_callback=_car_progress,
                    )
                    st.session_state["bp_carousel_result"] = result

                progress_bar.empty()
                st.success(
                    f"Carousels: {result['success']} generated, {result['skipped']} skipped, "
                    f"{result['failed']} failed | Cost: ${result['total_cost']:.4f}"
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
                            # Need to fetch this media's info
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

            render_inline_review(car["id"], "carousel", car_status, f"pp_car_{cid}")
            st.markdown("---")


# -------------------------------------------------------
# SLIDESHOW PIPELINE
# -------------------------------------------------------
slideshow_slots_list = route_groups.get("reel-slideshow", [])
if slideshow_slots_list:
    st.markdown("---")
    ss_slot_ids = [s["id"] for s in slideshow_slots_list]
    _ss_total = sum(1 for cid in ss_slot_ids if cid in slideshow_map)
    _ss_eligible = len(slideshow_slots_list) - _ss_total
    _ss_icon = "green" if _ss_total == len(slideshow_slots_list) else ("orange" if _ss_total > 0 else "gray")

    st.markdown(f"### Slideshow Pipeline ({len(slideshow_slots_list)} slots)")
    with st.expander(
        f":{_ss_icon}[Step 1: SLIDESHOWS] — {_ss_total}/{len(slideshow_slots_list)} done",
        expanded=_ss_eligible > 0,
    ):
        if _ss_total > 0:
            st.markdown(f":green[{_ss_total} slideshow{'s' if _ss_total != 1 else ''} generated]")
        if _ss_eligible > 0:
            if st.button(
                f"Generate Slideshows ({_ss_eligible})",
                type="primary", key="bp_run_slideshows",
                help="Free (FFmpeg)",
            ):
                eligible = [s for s in slideshow_slots_list if s["id"] not in slideshow_map]
                progress_bar = st.progress(0, text="Starting slideshow generation...")

                def _ss_progress(i, total, msg):
                    progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

                with st.spinner(f"Generating slideshows for {len(eligible)} slots..."):
                    result = batch_generate_slideshows(
                        slots=eligible,
                        slide_count=slideshow_slides,
                        duration_per_slide=slideshow_duration,
                        progress_callback=_ss_progress,
                    )
                    st.session_state["bp_slideshow_result"] = result

                progress_bar.empty()
                st.success(
                    f"Slideshows: {result['success']} generated, {result['skipped']} skipped, "
                    f"{result['failed']} failed"
                )
                if result["errors"]:
                    for err in result["errors"]:
                        st.warning(err)
                st.rerun()

    # Note: slideshow music+composite is handled in the reel music step above
    # (slideshow_slots are in music_slots already)


# -------------------------------------------------------
# CAPTIONS (all slots)
# -------------------------------------------------------
st.markdown("---")
st.markdown(f"### Captions ({total_slots} slots)")

_cap_have = sum(1 for cid in cal_ids if cid in content_map)
_cap_need = total_slots - _cap_have
# Carousel slots already have captions from carousel generation — exclude them
_carousel_cal_ids = set(s["id"] for s in carousel_slots_list) if carousel_slots_list else set()
_cap_need_non_carousel = sum(
    1 for s in slots_with_media
    if s["id"] not in content_map and s["id"] not in _carousel_cal_ids
)
_cap_icon = "green" if _cap_have == total_slots else ("orange" if _cap_have > 0 else "gray")

with st.expander(
    f":{_cap_icon}[CAPTIONS] — {_cap_have}/{total_slots} slots with captions",
    expanded=_cap_need_non_carousel > 0 and _ready_count > total_slots * 0.5,
):
    if _cap_have > 0:
        st.markdown(f":green[{_cap_have} slot{'s' if _cap_have != 1 else ''} have captions]")
    if _cap_need_non_carousel > 0:
        cap_est = estimate_batch_cost(
            [s for s in slots_with_media if s["id"] not in content_map and s["id"] not in _carousel_cal_ids],
            caption_model,
            caption_include_image,
        )
        st.markdown(f":gray[{_cap_need_non_carousel} slot{'s' if _cap_need_non_carousel != 1 else ''} need captions]")

        if st.button(
            f"Generate Captions ({_cap_need_non_carousel})",
            type="primary", key="bp_run_captions",
            help=f"~${cap_est['estimated_cost_usd']:.2f}",
        ):
            entries_to_caption = [
                s for s in slots_with_media
                if s["id"] not in content_map and s["id"] not in _carousel_cal_ids
            ]
            progress_bar = st.progress(0, text="Generating captions...")
            success_count = 0
            total_cost = 0.0
            total = len(entries_to_caption)

            for i, entry in enumerate(entries_to_caption):
                try:
                    image_b64 = None
                    if caption_include_image:
                        mid = entry.get("manual_media_id") or entry.get("media_id")
                        mi = media_info.get(mid, {}) if mid else {}
                        dfid = mi.get("drive_file_id")
                        if dfid:
                            from src.utils import encode_image_bytes
                            raw = download_file_bytes(dfid)
                            image_b64 = encode_image_bytes(raw)

                    result = generate_for_slot(
                        entry=entry,
                        model=caption_model,
                        include_image=caption_include_image,
                        image_base64=image_b64,
                        tone=caption_tone,
                    )
                    if result:
                        success_count += 1
                        total_cost += result.get("cost_usd", 0)
                except Exception as e:
                    st.warning(f"Failed for {entry['post_date']} S{entry.get('slot_index', 1)}: {e}")

                progress_bar.progress((i + 1) / total, text=f"Generated {i + 1}/{total}...")

            progress_bar.empty()
            st.success(f"Generated captions for {success_count}/{total} slots (${total_cost:.4f})")
            st.rerun()
    elif _cap_need == 0:
        st.success("All slots have captions!")
    else:
        st.info("Carousel captions are generated with the carousel step")

# -------------------------------------------------------
# Link to review history
# -------------------------------------------------------
st.divider()
st.page_link("pages/11_Drafts_Review.py", label="Review History (all content) ->", icon=":material/rate_review:")
