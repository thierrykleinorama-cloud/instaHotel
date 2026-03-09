"""
InstaHotel — Batch Creative Pipeline
Orchestrate scenario/video/music/composite generation for all calendar slots.
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
    fetch_media_info,
)
from app.components.media_grid import _fetch_thumbnail_b64
from src.services.batch_creative import (
    batch_generate_scenarios,
    batch_generate_videos,
    batch_generate_music,
    batch_composite,
    estimate_scenario_cost,
    estimate_video_cost,
    estimate_music_cost,
)
from src.services.creative_transform import VIDEO_MODELS

sidebar_css()
page_title("Batch Pipeline", "Generate creative content for all calendar slots")

with st.expander("How it works", expanded=False):
    st.markdown("""
**4-step pipeline with review gates:**

1. **Run Scenarios** — AI generates 3 creative video concepts per calendar slot (~$0.02/slot)
2. **Review in Drafts Review** — Accept the best scenario for each slot, reject the rest
3. **Run Videos** — Generates video from each accepted scenario (~$0.30/slot Kling, ~$0.60 Veo)
4. **Review in Drafts Review** — Accept/reject videos
5. **Run Music** — Generates background music for accepted videos (~$0.02/slot)
6. **Review in Drafts Review** — Accept/reject music
7. **Run Composite** — Merges accepted video + music into final Reel (free)

Each step only processes slots that passed the previous review gate.
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
    # so the default date shows work the user already started
    _lookback_start = default_start - timedelta(weeks=4)
    _recent_cal = fetch_calendar_range(_lookback_start, default_start - timedelta(days=1))
    _has_creative = [e for e in _recent_cal if e.get("creative_status")]
    if _has_creative and not st.session_state.get("_bp_date_overridden"):
        # Default to the earliest week with creative work
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
    _video_options = {v["label"]: k for k, v in VIDEO_MODELS.items()}
    _video_label = st.selectbox("Video Model", list(_video_options.keys()), key="bp_video_label")
    video_model = _video_options[_video_label]
    _model_info = VIDEO_MODELS[video_model]
    if _model_info.get("provider") == "google":
        video_duration = st.selectbox("Duration", [4, 6, 8], index=0, key="bp_video_dur")
    else:
        video_duration = st.selectbox("Duration", [5, 10], index=0, key="bp_video_dur")
    video_aspect = st.selectbox("Aspect Ratio", ["9:16", "16:9", "1:1"], key="bp_video_ar")

    st.divider()
    st.subheader("Music Settings")
    music_duration = st.slider("Duration (sec)", 5, 30, 10, key="bp_music_dur")

    st.divider()
    st.subheader("Composite Settings")
    composite_volume = st.slider("Music Volume", 0.1, 1.0, 0.3, step=0.1, key="bp_comp_vol")

# -------------------------------------------------------
# Load calendar data + creative status
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

cal_ids = [s["id"] for s in slots_with_media]

# Fetch creative status for all slots
scenario_map = fetch_scenarios_for_calendar_ids(cal_ids)
video_map = fetch_videos_for_calendar_ids(cal_ids)
music_map = fetch_music_for_calendar_ids(cal_ids)
composite_map = fetch_composite_for_calendar_ids(cal_ids)

# Fetch media info for display (name + drive_file_id for thumbnails)
all_media_ids = list({
    s.get("manual_media_id") or s.get("media_id")
    for s in slots_with_media
    if s.get("manual_media_id") or s.get("media_id")
})
media_info = fetch_media_info(all_media_ids)

# -------------------------------------------------------
# Compute per-slot status
# -------------------------------------------------------

def _count_by_status(items: list[dict], status_key: str = "status") -> dict:
    """Count items by status."""
    counts: dict[str, int] = {}
    for item in items:
        s = item.get(status_key, "unknown")
        counts[s] = counts.get(s, 0) + 1
    return counts


# Aggregate counts
total_slots = len(slots_with_media)

scenarios_total = sum(1 for cid in cal_ids if cid in scenario_map)
scenarios_accepted = sum(
    1 for cid in cal_ids
    if any(s.get("status") == "accepted" for s in scenario_map.get(cid, []))
)

videos_total = sum(1 for cid in cal_ids if cid in video_map)
videos_accepted = sum(
    1 for cid in cal_ids
    if any(v.get("status") == "accepted" for v in video_map.get(cid, []))
)

music_total = sum(1 for cid in cal_ids if cid in music_map)
music_accepted = sum(
    1 for cid in cal_ids
    if any(m.get("status") == "accepted" for m in music_map.get(cid, []))
)

composites_total = sum(1 for cid in cal_ids if cid in composite_map)

# Cost estimates for eligible slots
scenario_eligible = total_slots - scenarios_total
video_eligible = scenarios_accepted - videos_total
music_eligible = videos_accepted - music_total
composite_eligible = min(videos_accepted, music_accepted) - composites_total

sc_est = estimate_scenario_cost(max(scenario_eligible, 0), scenario_count, scenario_include_image, scenario_model)
vid_est = estimate_video_cost(max(video_eligible, 0), video_model, video_duration)
mus_est = estimate_music_cost(max(music_eligible, 0), music_duration)

# -------------------------------------------------------
# Step overview — 4 metric columns
# -------------------------------------------------------
st.subheader("Pipeline Overview")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric("SCENARIOS", f"{scenarios_total}/{total_slots}")
    st.caption(f":green[{scenarios_accepted} accepted]" if scenarios_accepted else "0 accepted")
    if scenario_eligible > 0:
        st.caption(f"~${sc_est['total']:.2f} for {scenario_eligible} slots")

with c2:
    st.metric("VIDEOS", f"{videos_total}/{scenarios_accepted or '—'}")
    st.caption(f":green[{videos_accepted} accepted]" if videos_accepted else "0 accepted")
    if video_eligible > 0:
        st.caption(f"~${vid_est['total']:.2f} for {video_eligible} slots")

with c3:
    st.metric("MUSIC", f"{music_total}/{videos_accepted or '—'}")
    st.caption(f":green[{music_accepted} accepted]" if music_accepted else "0 accepted")
    if music_eligible > 0:
        st.caption(f"~${mus_est['total']:.2f} for {music_eligible} slots")

with c4:
    st.metric("COMPOSITE", f"{composites_total}/{min(videos_accepted, music_accepted) or '—'}")
    st.caption(":green[Free (FFmpeg)]")
    if composite_eligible > 0:
        st.caption(f"{composite_eligible} slots ready")

# Next action hint
_hints = []
if scenario_eligible > 0:
    _hints.append(f"**1.** Run scenarios for **{scenario_eligible}** slots")
if scenarios_total > 0 and scenarios_accepted < scenarios_total:
    _unreviewed = scenarios_total - scenarios_accepted - sum(
        1 for cid in cal_ids
        if all(s.get("status") == "rejected" for s in scenario_map.get(cid, []))
        and cid in scenario_map
    )
    if _unreviewed > 0:
        _hints.append(f"**2.** Go to **Drafts Review** → accept best scenario per slot ({_unreviewed} to review)")
if video_eligible > 0:
    _hints.append(f"**3.** Run videos for **{video_eligible}** accepted scenarios (~${vid_est['total']:.2f})")
elif videos_total > 0 and videos_accepted == 0:
    _hints.append("**3.** Go to **Drafts Review** → accept/reject videos")
if music_eligible > 0:
    _hints.append(f"**4.** Run music for **{music_eligible}** accepted videos")
elif music_total > 0 and music_accepted == 0:
    _hints.append("**4.** Go to **Drafts Review** → accept/reject music")
if composite_eligible > 0:
    _hints.append(f"**5.** Run composite for **{composite_eligible}** slots (free)")

if _hints:
    st.info("**Next steps:**\n\n" + "\n\n".join(_hints))
elif composites_total > 0:
    st.success("Pipeline complete! All slots have composited Reels.")

# -------------------------------------------------------
# Action buttons
# -------------------------------------------------------
st.divider()

b1, b2, b3, b4 = st.columns(4)

with b1:
    _sc_disabled = scenario_eligible <= 0
    _sc_label = f"Run Scenarios ({scenario_eligible})" if scenario_eligible > 0 else "Scenarios Done"
    run_scenarios = st.button(
        _sc_label, type="primary", use_container_width=True,
        disabled=_sc_disabled, key="bp_run_scenarios",
    )
    if scenario_eligible > 0:
        st.caption(f"Generate {scenario_count} video concepts for {scenario_eligible} slots without scenarios")
    else:
        st.caption("All slots have scenarios")

with b2:
    _vid_disabled = video_eligible <= 0
    _vid_label = f"Run Videos ({video_eligible})" if video_eligible > 0 else "Videos Done"
    run_videos = st.button(
        _vid_label, type="primary", use_container_width=True,
        disabled=_vid_disabled, key="bp_run_videos",
    )
    if video_eligible > 0:
        st.caption(f"Create video from accepted scenario for {video_eligible} slots")
    elif scenarios_accepted > 0 and videos_total > 0 and videos_accepted == 0:
        st.caption("Review videos in Drafts Review first")
    else:
        st.caption("Need accepted scenarios first")

with b3:
    _mus_disabled = music_eligible <= 0
    _mus_label = f"Run Music ({music_eligible})" if music_eligible > 0 else "Music Done"
    run_music = st.button(
        _mus_label, type="primary", use_container_width=True,
        disabled=_mus_disabled, key="bp_run_music",
    )
    if music_eligible > 0:
        st.caption(f"Generate background music for {music_eligible} accepted videos")
    else:
        st.caption("Need accepted videos first")

with b4:
    _comp_disabled = composite_eligible <= 0
    _comp_label = f"Run Composite ({composite_eligible})" if composite_eligible > 0 else "Composite Done"
    run_composite = st.button(
        _comp_label, type="primary", use_container_width=True,
        disabled=_comp_disabled, key="bp_run_composite",
    )
    if composite_eligible > 0:
        st.caption(f"Merge video + music for {composite_eligible} slots (free)")
    else:
        st.caption("Need accepted video + music")

# -------------------------------------------------------
# Progress area — run batch operations
# -------------------------------------------------------

if run_scenarios:
    eligible_slots = [s for s in slots_with_media if s["id"] not in scenario_map]
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
        s for s in slots_with_media
        if s["id"] not in video_map
        and any(sc.get("status") == "accepted" for sc in scenario_map.get(s["id"], []))
    ]
    if eligible_slots:
        progress_bar = st.progress(0, text="Starting video generation...")

        def _vid_progress(i, total, msg):
            progress_bar.progress((i + 1) / max(total, 1) if i < total else 1.0, text=msg)

        with st.spinner(f"Generating videos for {len(eligible_slots)} slots (this may take several minutes)..."):
            result = batch_generate_videos(
                slots=eligible_slots,
                video_model=video_model,
                duration=video_duration,
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
        s for s in slots_with_media
        if s["id"] not in music_map
        and any(v.get("status") == "accepted" for v in video_map.get(s["id"], []))
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
        s for s in slots_with_media
        if s["id"] not in composite_map
        and any(v.get("status") == "accepted" for v in video_map.get(s["id"], []))
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

# -------------------------------------------------------
# Slot status table
# -------------------------------------------------------
st.divider()
st.subheader("Slot Details")

# Header row
_h1, _h2, _h3, _h4, _h5, _h6, _h7 = st.columns([1.2, 2.5, 1.5, 1.5, 1.0, 1.0, 1.3])
_h1.markdown("**Photo**")
_h2.markdown("**Slot**")
_h3.markdown("**Scenarios**")
_h4.markdown("**Video**")
_h5.markdown("**Music**")
_h6.markdown("**Comp.**")
_h7.markdown("**Stage**")

# Render slot rows with thumbnails
for slot in slots_with_media:
    cid = slot["id"]
    mid = slot.get("manual_media_id") or slot.get("media_id")
    mi = media_info.get(mid, {}) if mid else {}
    mname = mi.get("file_name", "—")
    drive_fid = mi.get("drive_file_id")
    cat = slot.get("target_category") or mi.get("category") or "—"

    # Format date as DD/MM/YYYY
    _pd = slot.get("post_date", "")
    if isinstance(_pd, str) and len(_pd) >= 10:
        _pd = f"{_pd[8:10]}/{_pd[5:7]}/{_pd[:4]}"

    # Scenarios
    sc_list = scenario_map.get(cid, [])
    sc_count = len(sc_list)
    sc_accepted = sum(1 for s in sc_list if s.get("status") == "accepted")
    sc_rejected = sum(1 for s in sc_list if s.get("status") == "rejected")
    if sc_count == 0:
        sc_label = "—"
    elif sc_accepted > 0:
        sc_label = f":green[{sc_accepted} accepted]"
    elif sc_rejected == sc_count:
        sc_label = f":red[{sc_rejected} rejected]"
    else:
        sc_label = f"{sc_count} draft"

    # Videos
    vid_list = video_map.get(cid, [])
    vid_count = len(vid_list)
    vid_accepted = any(v.get("status") == "accepted" for v in vid_list)
    if vid_count == 0:
        vid_label = "—"
    elif vid_accepted:
        vid_label = ":green[accepted]"
    else:
        vid_label = f"{vid_count} unreviewed"

    # Music
    mus_list = music_map.get(cid, [])
    mus_count = len(mus_list)
    mus_accepted = any(m.get("status") == "accepted" for m in mus_list)
    if mus_count == 0:
        mus_label = "—"
    elif mus_accepted:
        mus_label = ":green[accepted]"
    else:
        mus_label = f"{mus_count} draft"

    # Composite
    comp_list = composite_map.get(cid, [])
    comp_label = ":green[done]" if comp_list else "—"

    # Render row: thumbnail | info | pipeline status
    rc1, rc2, rc3, rc4, rc5, rc6, rc7 = st.columns([1.2, 2.5, 1.5, 1.5, 1.0, 1.0, 1.3])
    with rc1:
        if drive_fid:
            try:
                b64 = _fetch_thumbnail_b64(drive_fid)
                if b64:
                    st.image(f"data:image/jpeg;base64,{b64}", width=80)
                else:
                    st.caption("no thumb")
            except Exception:
                st.caption("no thumb")
        else:
            st.caption("—")
    with rc2:
        st.markdown(f"**{_pd}** S{slot.get('slot_index', 1)}  \n{cat} · {mname[:25]}")
    with rc3:
        st.markdown(f"Scenarios: {sc_label}")
    with rc4:
        st.markdown(f"Video: {vid_label}")
    with rc5:
        st.markdown(f"Music: {mus_label}")
    with rc6:
        st.markdown(f"Comp: {comp_label}")
    with rc7:
        # Show creative_status badge
        _cs = slot.get("creative_status")
        _badges = {
            "scenarios_generated": ":violet[Scenarios]",
            "video_generated": ":blue[Video]",
            "music_generated": ":orange[Music]",
            "complete": ":green[Complete]",
        }
        st.markdown(_badges.get(_cs, ":gray[—]"))

# -------------------------------------------------------
# Link to Drafts Review
# -------------------------------------------------------
st.divider()
st.page_link("pages/11_Drafts_Review.py", label="Review generated content →", icon=":material/rate_review:")
