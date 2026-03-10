"""
InstaHotel — Batch Creative Pipeline
Orchestrate scenario/video/music/composite/carousel/slideshow generation
for all calendar slots, with content-type routing.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from datetime import date, timedelta

from app.components.ui import sidebar_css, page_title
from src.services.editorial_queries import fetch_calendar_range
from src.services.creative_queries import (
    fetch_scenarios_for_calendar_ids,
    fetch_videos_for_calendar_ids,
    fetch_music_for_calendar_ids,
    fetch_composite_for_calendar_ids,
    fetch_slideshows_for_calendar_ids,
    fetch_media_info,
)
from src.services.carousel_queries import fetch_carousels_for_calendar_ids
from app.components.media_grid import _fetch_thumbnail_b64
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

sidebar_css()
page_title("Batch Pipeline", "Generate creative content for all calendar slots")

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

with st.expander("How it works", expanded=False):
    st.markdown("""
**Route-based pipeline — each slot's route determines its production path:**

| Route | Pipeline |
|---|---|
| **Image Post** | Caption only (handled in Calendar) |
| **Carousel** | AI select images → generate captions → save draft |
| **Reel (Kling)** | Scenarios → Video (Kling) → Music → Composite |
| **Reel (Veo)** | Scenarios → Video (Veo) → Done (native audio) |
| **Reel (Slideshow)** | Select images → Ken Burns video → Music → Composite |

**Review gates** between each step via the Drafts Review page.
Re-running a step skips already-processed slots (idempotent).
""")

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

    # Check if there's in-progress creative work in a recent range (look back 4 weeks)
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
    st.caption(f"Range: {start_date.strftime('%d/%m/%Y')} → {end_date.strftime('%d/%m/%Y')}")

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

# -------------------------------------------------------
# Load calendar data + route classification
# -------------------------------------------------------
calendar_data = fetch_calendar_range(start_date, end_date)

# Filter to slots with assigned media
slots_with_media = [
    s for s in calendar_data
    if s.get("manual_media_id") or s.get("media_id")
]

if not slots_with_media:
    st.warning("No calendar slots with assigned media in this date range. Generate a calendar first.")
    st.stop()

# Classify by route
route_groups = classify_slots_by_route(slots_with_media)

# Route summary
st.subheader("Route Summary")
_route_cols = st.columns(5)
for i, (route, label) in enumerate(ROUTE_LABELS.items()):
    count = len(route_groups.get(route, []))
    color = ROUTE_COLORS[route]
    _route_cols[i].markdown(f":{color}[**{label}**]  \n{count} slots")

cal_ids = [s["id"] for s in slots_with_media]

# Fetch creative status for all slots
scenario_map = fetch_scenarios_for_calendar_ids(cal_ids)
video_map = fetch_videos_for_calendar_ids(cal_ids)
music_map = fetch_music_for_calendar_ids(cal_ids)
composite_map = fetch_composite_for_calendar_ids(cal_ids)
carousel_map = fetch_carousels_for_calendar_ids(cal_ids)
slideshow_map = fetch_slideshows_for_calendar_ids(cal_ids)

# Fetch media info for display
all_media_ids = list({
    s.get("manual_media_id") or s.get("media_id")
    for s in slots_with_media
    if s.get("manual_media_id") or s.get("media_id")
})
media_info = fetch_media_info(all_media_ids)

# -------------------------------------------------------
# Reel slots (Kling + Veo)
# -------------------------------------------------------
reel_slots = route_groups.get("reel-kling", []) + route_groups.get("reel-veo", [])
reel_kling_slots = route_groups.get("reel-kling", [])
reel_veo_slots = route_groups.get("reel-veo", [])

# Music/composite eligible: reel-kling + reel-slideshow
music_slots = route_groups.get("reel-kling", []) + route_groups.get("reel-slideshow", [])

# -------------------------------------------------------
# Compute per-route status
# -------------------------------------------------------
total_slots = len(slots_with_media)

# Reel pipeline stats
reel_ids = [s["id"] for s in reel_slots]
scenarios_total = sum(1 for cid in reel_ids if cid in scenario_map)
scenarios_accepted = sum(
    1 for cid in reel_ids
    if any(s.get("status") == "accepted" for s in scenario_map.get(cid, []))
)

videos_total = sum(1 for cid in reel_ids if cid in video_map)
videos_accepted = sum(
    1 for cid in reel_ids
    if any(v.get("status") == "accepted" for v in video_map.get(cid, []))
)

# Music: reel-kling + reel-slideshow
music_ids = [s["id"] for s in music_slots]
music_total = sum(1 for cid in music_ids if cid in music_map)
music_accepted = sum(
    1 for cid in music_ids
    if any(m.get("status") == "accepted" for m in music_map.get(cid, []))
)

composites_total = sum(1 for cid in music_ids if cid in composite_map)

# Carousel stats
carousel_slot_ids = [s["id"] for s in route_groups.get("carousel", [])]
carousels_total = sum(1 for cid in carousel_slot_ids if cid in carousel_map)

# Slideshow stats
slideshow_slot_ids = [s["id"] for s in route_groups.get("reel-slideshow", [])]
slideshows_total = sum(1 for cid in slideshow_slot_ids if cid in slideshow_map)

# -------------------------------------------------------
# Pipeline Overview
# -------------------------------------------------------
st.subheader("Pipeline Overview")

c1, c2, c3, c4, c5, c6 = st.columns(6)

# Scenarios (reel-kling + reel-veo)
scenario_eligible = len(reel_slots) - scenarios_total
sc_est = estimate_scenario_cost(max(scenario_eligible, 0), scenario_count, scenario_include_image, scenario_model)
with c1:
    st.metric("SCENARIOS", f"{scenarios_total}/{len(reel_slots)} reel slots")
    st.caption(f":green[{scenarios_accepted} slots accepted]" if scenarios_accepted else "0 accepted")
    if scenario_eligible > 0:
        st.caption(f"{scenario_eligible} slots need scenarios · ~${sc_est['total']:.2f}")

# Videos (reel-kling + reel-veo)
video_eligible = scenarios_accepted - videos_total
# Estimate based on mix of Kling and Veo
_kling_eligible = max(0, sum(1 for s in reel_kling_slots if any(sc.get("status") == "accepted" for sc in scenario_map.get(s["id"], []))) - sum(1 for s in reel_kling_slots if s["id"] in video_map))
_veo_eligible = max(0, video_eligible - _kling_eligible)
vid_est_total = (
    estimate_video_cost(max(_kling_eligible, 0), "kling-v2.1", video_duration_kling)["total"]
    + estimate_video_cost(max(_veo_eligible, 0), "veo-3.1-fast", video_duration_veo)["total"]
)
with c2:
    st.metric("VIDEOS", f"{videos_total}/{scenarios_accepted or '—'} accepted slots")
    st.caption(f":green[{videos_accepted} videos accepted]" if videos_accepted else "0 accepted")
    if video_eligible > 0:
        st.caption(f"{video_eligible} to generate · ~${vid_est_total:.2f}")

# Music (reel-kling + reel-slideshow)
_kling_accepted_for_music = sum(1 for s in reel_kling_slots if any(v.get("status") == "accepted" for v in video_map.get(s["id"], [])))
_ss_done = slideshows_total
music_eligible = (_kling_accepted_for_music + _ss_done) - music_total
mus_est = estimate_music_cost(max(music_eligible, 0), music_duration)
_music_ready = _kling_accepted_for_music + _ss_done
with c3:
    st.metric("MUSIC", f"{music_total}/{_music_ready or '—'} ready slots")
    st.caption(f":green[{music_accepted} accepted]" if music_accepted else "0 accepted")
    if music_eligible > 0:
        st.caption(f"{music_eligible} to generate · ~${mus_est['total']:.2f}")

# Composite
composite_eligible = min(_music_ready, music_accepted) - composites_total
with c4:
    st.metric("COMPOSITE", f"{composites_total}/{min(_music_ready, music_accepted) or '—'} ready")
    st.caption(":green[Free (FFmpeg)]")

# Carousel
carousel_eligible = len(route_groups.get("carousel", [])) - carousels_total
car_est = estimate_carousel_cost(max(carousel_eligible, 0), scenario_model)
with c5:
    st.metric("CAROUSELS", f"{carousels_total}/{len(route_groups.get('carousel', []))} slots")
    if carousel_eligible > 0:
        st.caption(f"{carousel_eligible} to generate · ~${car_est['total']:.2f}")

# Slideshow
slideshow_eligible = len(route_groups.get("reel-slideshow", [])) - slideshows_total
with c6:
    st.metric("SLIDESHOWS", f"{slideshows_total}/{len(route_groups.get('reel-slideshow', []))} slots")
    st.caption(":green[Free (FFmpeg)]")

# Next action hints
_hints = []
if scenario_eligible > 0:
    _hints.append(f"Run scenarios for **{scenario_eligible}** reel slots")
if scenarios_total > 0 and scenarios_accepted < scenarios_total:
    _unreviewed = scenarios_total - scenarios_accepted - sum(
        1 for cid in reel_ids
        if all(s.get("status") == "rejected" for s in scenario_map.get(cid, []))
        and cid in scenario_map
    )
    if _unreviewed > 0:
        _hints.append(f"Go to **Drafts Review** → {_unreviewed} reel slot{'s have' if _unreviewed > 1 else ' has'} draft scenarios waiting for accept/reject")
if video_eligible > 0:
    _hints.append(f"Run videos for **{video_eligible}** accepted scenarios (~${vid_est_total:.2f})")
if carousel_eligible > 0:
    _hints.append(f"Run carousels for **{carousel_eligible}** carousel slots")
if slideshow_eligible > 0:
    _hints.append(f"Run slideshows for **{slideshow_eligible}** slideshow slots")
if music_eligible > 0:
    _hints.append(f"Run music for **{music_eligible}** Kling+slideshow slots")
if composite_eligible > 0:
    _hints.append(f"Run composite for **{composite_eligible}** slots (free)")

if _hints:
    st.info("**Next steps:**\n\n" + "\n\n".join(f"- {h}" for h in _hints))
elif composites_total > 0 and composite_eligible <= 0 and carousel_eligible <= 0 and slideshow_eligible <= 0:
    st.success("Pipeline complete! All slots processed.")

# -------------------------------------------------------
# Action buttons
# -------------------------------------------------------
st.divider()

# Row 1: Reel pipeline
st.markdown("**Reel Pipeline** (Kling + Veo)")
b1, b2, b3, b4 = st.columns(4)

with b1:
    _sc_disabled = scenario_eligible <= 0
    _sc_label = f"Run Scenarios ({scenario_eligible})" if scenario_eligible > 0 else "Scenarios Done"
    run_scenarios = st.button(
        _sc_label, type="primary", use_container_width=True,
        disabled=_sc_disabled, key="bp_run_scenarios",
    )
    if scenario_eligible > 0:
        st.caption(f"{scenario_count} concepts × {scenario_eligible} reel slots")
    else:
        st.caption("All reel slots have scenarios")

with b2:
    _vid_disabled = video_eligible <= 0
    _vid_label = f"Run Videos ({video_eligible})" if video_eligible > 0 else "Videos Done"
    run_videos = st.button(
        _vid_label, type="primary", use_container_width=True,
        disabled=_vid_disabled, key="bp_run_videos",
    )
    if video_eligible > 0:
        _kling_n = sum(1 for s in reel_kling_slots if any(sc.get("status") == "accepted" for sc in scenario_map.get(s["id"], [])) and s["id"] not in video_map)
        _veo_n = video_eligible - _kling_n
        parts = []
        if _kling_n > 0:
            parts.append(f"{_kling_n} Kling")
        if _veo_n > 0:
            parts.append(f"{_veo_n} Veo")
        st.caption(" + ".join(parts))
    else:
        st.caption("Need accepted scenarios")

with b3:
    _mus_disabled = music_eligible <= 0
    _mus_label = f"Run Music ({music_eligible})" if music_eligible > 0 else "Music Done"
    run_music = st.button(
        _mus_label, type="primary", use_container_width=True,
        disabled=_mus_disabled, key="bp_run_music",
    )
    if music_eligible > 0:
        st.caption(f"Kling + slideshow slots")
    else:
        st.caption("Need accepted videos/slideshows")

with b4:
    _comp_disabled = composite_eligible <= 0
    _comp_label = f"Run Composite ({composite_eligible})" if composite_eligible > 0 else "Composite Done"
    run_composite = st.button(
        _comp_label, type="primary", use_container_width=True,
        disabled=_comp_disabled, key="bp_run_composite",
    )
    st.caption("Free (FFmpeg)")

# Row 2: Carousel + Slideshow
st.markdown("**Carousel & Slideshow**")
b5, b6, _b7, _b8 = st.columns(4)

with b5:
    _car_disabled = carousel_eligible <= 0
    _car_label = f"Run Carousels ({carousel_eligible})" if carousel_eligible > 0 else "Carousels Done"
    run_carousels = st.button(
        _car_label, type="primary", use_container_width=True,
        disabled=_car_disabled, key="bp_run_carousels",
    )
    if carousel_eligible > 0:
        st.caption(f"AI select {carousel_slides} images + captions")
    else:
        st.caption("All carousel slots done")

with b6:
    _ss_disabled = slideshow_eligible <= 0
    _ss_label = f"Run Slideshows ({slideshow_eligible})" if slideshow_eligible > 0 else "Slideshows Done"
    run_slideshows = st.button(
        _ss_label, type="primary", use_container_width=True,
        disabled=_ss_disabled, key="bp_run_slideshows",
    )
    if slideshow_eligible > 0:
        st.caption(f"{slideshow_slides} images × {slideshow_duration}s (free)")
    else:
        st.caption("All slideshow slots done")

# -------------------------------------------------------
# Progress area — run batch operations
# -------------------------------------------------------

if run_scenarios:
    eligible_slots = [s for s in reel_slots if s["id"] not in scenario_map]
    if eligible_slots:
        progress_bar = st.progress(0, text="Starting scenario generation...")

        def _sc_progress(i, total, msg):
            progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

        with st.spinner(f"Generating scenarios for {len(eligible_slots)} slots..."):
            result = batch_generate_scenarios(
                slots=eligible_slots,
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
            with st.expander("Errors"):
                for err in result["errors"]:
                    st.warning(err)
        st.rerun()


if run_videos:
    eligible_slots = [
        s for s in reel_slots
        if s["id"] not in video_map
        and any(sc.get("status") == "accepted" for sc in scenario_map.get(s["id"], []))
    ]
    if eligible_slots:
        progress_bar = st.progress(0, text="Starting video generation...")

        def _vid_progress(i, total, msg):
            progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

        # Duration depends on slot route
        # Use Kling duration as default; batch_generate_videos will adapt per-slot
        with st.spinner(f"Generating videos for {len(eligible_slots)} slots (this may take several minutes)..."):
            result = batch_generate_videos(
                slots=eligible_slots,
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
            with st.expander("Errors"):
                for err in result["errors"]:
                    st.warning(err)
        st.rerun()


if run_music:
    eligible_slots = [
        s for s in music_slots
        if s["id"] not in music_map
        and (
            any(v.get("status") == "accepted" for v in video_map.get(s["id"], []))
            or s["id"] in slideshow_map
        )
    ]
    if eligible_slots:
        progress_bar = st.progress(0, text="Starting music generation...")

        def _mus_progress(i, total, msg):
            progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

        with st.spinner(f"Generating music for {len(eligible_slots)} slots..."):
            result = batch_generate_music(
                slots=eligible_slots,
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
            with st.expander("Errors"):
                for err in result["errors"]:
                    st.warning(err)
        st.rerun()


if run_composite:
    eligible_slots = [
        s for s in music_slots
        if s["id"] not in composite_map
        and (
            any(v.get("status") == "accepted" for v in video_map.get(s["id"], []))
            or s["id"] in slideshow_map
        )
        and any(m.get("status") == "accepted" for m in music_map.get(s["id"], []))
    ]
    if eligible_slots:
        progress_bar = st.progress(0, text="Starting composite generation...")

        def _comp_progress(i, total, msg):
            progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

        with st.spinner(f"Compositing {len(eligible_slots)} slots..."):
            result = batch_composite(
                slots=eligible_slots,
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
            with st.expander("Errors"):
                for err in result["errors"]:
                    st.warning(err)
        st.rerun()


if run_carousels:
    _carousel_slots = route_groups.get("carousel", [])
    eligible_slots = [s for s in _carousel_slots if s["id"] not in carousel_map]
    if eligible_slots:
        progress_bar = st.progress(0, text="Starting carousel generation...")

        def _car_progress(i, total, msg):
            progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

        with st.spinner(f"Generating carousels for {len(eligible_slots)} slots..."):
            result = batch_generate_carousels(
                slots=eligible_slots,
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
            with st.expander("Errors"):
                for err in result["errors"]:
                    st.warning(err)
        st.rerun()


if run_slideshows:
    _ss_slots = route_groups.get("reel-slideshow", [])
    eligible_slots = [s for s in _ss_slots if s["id"] not in slideshow_map]
    if eligible_slots:
        progress_bar = st.progress(0, text="Starting slideshow generation...")

        def _ss_progress(i, total, msg):
            progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

        with st.spinner(f"Generating slideshows for {len(eligible_slots)} slots..."):
            result = batch_generate_slideshows(
                slots=eligible_slots,
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
            with st.expander("Errors"):
                for err in result["errors"]:
                    st.warning(err)
        st.rerun()

# -------------------------------------------------------
# Slot status table
# -------------------------------------------------------
st.divider()
st.subheader("Slot Details")

# Header row
_h1, _h2, _h3, _h4, _h5, _h6, _h7, _h8 = st.columns([1.0, 1.0, 2.0, 1.3, 1.3, 0.9, 0.9, 1.2])
_h1.markdown("**Photo**")
_h2.markdown("**Route**")
_h3.markdown("**Slot**")
_h4.markdown("**Scenarios**")
_h5.markdown("**Video**")
_h6.markdown("**Music**")
_h7.markdown("**Comp.**")
_h8.markdown("**Stage**")

# Render slot rows
for slot in slots_with_media:
    cid = slot["id"]
    mid = slot.get("manual_media_id") or slot.get("media_id")
    mi = media_info.get(mid, {}) if mid else {}
    mname = mi.get("file_name", "—")
    drive_fid = mi.get("drive_file_id")
    cat = slot.get("target_category") or mi.get("category") or "—"

    # Route
    route = slot.get("target_format") or "feed"
    if route == "story":
        route = "feed"
    if route == "reel":
        route = "reel-kling"
    route_label = ROUTE_LABELS.get(route, route)
    route_color = ROUTE_COLORS.get(route, "gray")

    # Format date
    _pd = slot.get("post_date", "")
    if isinstance(_pd, str) and len(_pd) >= 10:
        _pd = f"{_pd[8:10]}/{_pd[5:7]}/{_pd[:4]}"

    # Scenarios (reel routes only)
    sc_list = scenario_map.get(cid, [])
    sc_count = len(sc_list)
    sc_accepted = sum(1 for s in sc_list if s.get("status") == "accepted")
    if route not in ROUTES_REEL:
        sc_label = ":gray[n/a]"
    elif sc_count == 0:
        sc_label = "—"
    elif sc_accepted > 0:
        sc_label = f":green[{sc_accepted} accepted]"
    else:
        sc_rejected = sum(1 for s in sc_list if s.get("status") == "rejected")
        if sc_rejected == sc_count:
            sc_label = f":red[{sc_rejected} rejected]"
        else:
            sc_label = f"{sc_count} draft"

    # Videos
    vid_list = video_map.get(cid, [])
    vid_count = len(vid_list)
    vid_accepted = any(v.get("status") == "accepted" for v in vid_list)
    if route == "carousel":
        # Show carousel status
        car_list = carousel_map.get(cid, [])
        if car_list:
            vid_label = f":orange[carousel]"
        else:
            vid_label = "—"
    elif route == "reel-slideshow":
        ss_list = slideshow_map.get(cid, [])
        if ss_list:
            vid_label = f":violet[slideshow]"
        else:
            vid_label = "—"
    elif route == "feed":
        vid_label = ":gray[n/a]"
    elif vid_count == 0:
        vid_label = "—"
    elif vid_accepted:
        vid_label = ":green[accepted]"
    else:
        vid_label = f"{vid_count} unreviewed"

    # Music
    mus_list = music_map.get(cid, [])
    mus_count = len(mus_list)
    mus_accepted = any(m.get("status") == "accepted" for m in mus_list)
    if route not in ROUTES_NEED_MUSIC:
        mus_label = ":gray[n/a]"
    elif mus_count == 0:
        mus_label = "—"
    elif mus_accepted:
        mus_label = ":green[accepted]"
    else:
        mus_label = f"{mus_count} draft"

    # Composite
    comp_list = composite_map.get(cid, [])
    if route not in ROUTES_NEED_MUSIC:
        comp_label = ":gray[n/a]"
    else:
        comp_label = ":green[done]" if comp_list else "—"

    # Render row
    rc1, rc2, rc3, rc4, rc5, rc6, rc7, rc8 = st.columns([1.0, 1.0, 2.0, 1.3, 1.3, 0.9, 0.9, 1.2])
    with rc1:
        if drive_fid:
            try:
                b64 = _fetch_thumbnail_b64(drive_fid)
                if b64:
                    st.image(f"data:image/jpeg;base64,{b64}", width=70)
                else:
                    st.caption("no thumb")
            except Exception:
                st.caption("no thumb")
        else:
            st.caption("—")
    with rc2:
        st.markdown(f":{route_color}[{route_label}]")
    with rc3:
        st.markdown(f"**{_pd}** S{slot.get('slot_index', 1)}  \n{cat} · {mname[:20]}")
    with rc4:
        st.markdown(sc_label)
    with rc5:
        st.markdown(vid_label)
    with rc6:
        st.markdown(mus_label)
    with rc7:
        st.markdown(comp_label)
    with rc8:
        _cs = slot.get("creative_status")
        _badges = {
            "scenarios_generated": ":violet[Scenarios]",
            "video_generated": ":blue[Video]",
            "music_generated": ":orange[Music]",
            "complete": ":green[Complete]",
            "carousel_generated": ":orange[Carousel]",
            "slideshow_generated": ":violet[Slideshow]",
        }
        st.markdown(_badges.get(_cs, ":gray[—]"))

# -------------------------------------------------------
# Link to Drafts Review
# -------------------------------------------------------
st.divider()
st.page_link("pages/11_Drafts_Review.py", label="Review generated content →", icon=":material/rate_review:")
