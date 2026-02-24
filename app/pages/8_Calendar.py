"""
InstaHotel — Editorial Calendar
Generate, browse, and manage the posting calendar with scored media assignments.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from datetime import date, timedelta

from app.components.ui import sidebar_css, page_title
from app.components.media_grid import _fetch_thumbnail_b64
from src.services.editorial_queries import (
    fetch_all_rules,
    fetch_active_theme_for_date,
    fetch_calendar_range,
    bulk_upsert_calendar,
    update_calendar_status,
    update_calendar_media,
    delete_calendar_range,
)
from src.services.editorial_engine import (
    generate_calendar,
    select_best_media,
    get_current_season,
    score_media,
    _fetch_analyzed_media,
    _fetch_recent_media_ids,
)

sidebar_css()
page_title("Calendar", "Editorial posting calendar")

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
STATUS_COLORS = {
    "planned": "gray",
    "generated": "blue",
    "validated": "green",
    "published": "violet",
    "skipped": "orange",
}

# -------------------------------------------------------
# Sidebar controls
# -------------------------------------------------------
with st.sidebar:
    st.subheader("Calendar Controls")

    today = date.today()
    default_start = today - timedelta(days=today.weekday())  # Monday of current week

    start_date = st.date_input("Start Date", value=default_start, key="cal_start")
    weeks = st.slider("Weeks", 1, 8, 4, key="cal_weeks")
    end_date = start_date + timedelta(weeks=weeks) - timedelta(days=1)
    st.caption(f"Range: {start_date} → {end_date}")

    st.divider()

    overwrite = st.checkbox("Overwrite existing entries", value=False, key="cal_overwrite")

    if st.button("Generate Calendar", type="primary", use_container_width=True):
        rules = fetch_all_rules()
        if not rules:
            st.error("No editorial rules found. Configure rules first.")
        else:
            with st.spinner("Generating calendar..."):
                entries = generate_calendar(
                    start_date=start_date,
                    end_date=end_date,
                    rules=rules,
                    fetch_theme_fn=fetch_active_theme_for_date,
                    overwrite_existing=overwrite,
                )
                if entries:
                    bulk_upsert_calendar(entries)
                    st.success(f"Generated {len(entries)} calendar entries.")
                    st.rerun()
                else:
                    st.info("No new entries to generate (all slots already filled).")

    st.divider()
    status_filter = st.multiselect(
        "Filter by Status",
        ["planned", "generated", "validated", "published", "skipped"],
        default=["generated", "validated", "planned"],
        key="cal_status_filter",
    )

# -------------------------------------------------------
# Fetch calendar data
# -------------------------------------------------------
calendar_data = fetch_calendar_range(start_date, end_date)

if status_filter:
    calendar_data = [e for e in calendar_data if e.get("status") in status_filter]

if not calendar_data:
    st.info("No calendar entries for this range. Use the sidebar to generate.")
    st.stop()

# -------------------------------------------------------
# View toggle
# -------------------------------------------------------
view_mode = st.radio("View", ["Week Grid", "List"], horizontal=True, key="cal_view")

# -------------------------------------------------------
# Week Grid View
# -------------------------------------------------------
if view_mode == "Week Grid":
    # Group entries by week start (Monday)
    entries_by_date: dict[str, list[dict]] = {}
    for e in calendar_data:
        entries_by_date.setdefault(e["post_date"], []).append(e)

    # Iterate week by week
    current_week_start = start_date
    while current_week_start <= end_date:
        week_end = current_week_start + timedelta(days=6)
        st.markdown(f"#### Week of {current_week_start.strftime('%b %d')}")

        cols = st.columns(7)
        for i, col in enumerate(cols):
            day = current_week_start + timedelta(days=i)
            day_str = day.isoformat()
            day_entries = entries_by_date.get(day_str, [])

            with col:
                is_today = day == today
                header = f"**{DAY_NAMES[i]} {day.day}**" if not is_today else f"**:red[{DAY_NAMES[i]} {day.day}]**"
                st.markdown(header)

                if not day_entries:
                    st.caption("—")
                else:
                    for entry in day_entries:
                        status = entry.get("status", "planned")
                        cat = entry.get("target_category") or "?"
                        score = entry.get("media_score")
                        slot = entry.get("slot_index", 1)
                        media_id = entry.get("manual_media_id") or entry.get("media_id")

                        # Show thumbnail if media assigned
                        if media_id:
                            # Try to get drive_file_id for thumbnail
                            # We'll just show a colored status indicator
                            score_str = f"{score:.0f}" if score else "—"
                            st.markdown(f":{STATUS_COLORS.get(status, 'gray')}[●] {cat}")
                            st.caption(f"S{slot} | {score_str}pts")
                        else:
                            st.markdown(f":gray[○] {cat}")
                            st.caption(f"S{slot} | no media")

        st.divider()
        current_week_start += timedelta(days=7)

# -------------------------------------------------------
# List View
# -------------------------------------------------------
else:
    for entry in calendar_data:
        post_date = entry["post_date"]
        status = entry.get("status", "planned")
        cat = entry.get("target_category") or "?"
        fmt = entry.get("target_format") or "?"
        score = entry.get("media_score")
        theme = entry.get("theme_name") or "—"
        slot = entry.get("slot_index", 1)
        season = entry.get("season_context") or "—"
        media_id = entry.get("manual_media_id") or entry.get("media_id")

        score_str = f"{score:.1f}" if score else "—"
        color = STATUS_COLORS.get(status, "gray")

        with st.expander(f":{color}[●] {post_date} — S{slot} | {cat} | {score_str}pts | {status}", expanded=False):
            c1, c2 = st.columns([2, 1])

            with c1:
                st.markdown(f"**Date:** {post_date}  \n**Slot:** {slot}  \n**Category:** {cat}  \n**Format:** {fmt}")
                st.markdown(f"**Season:** {season}  \n**Theme:** {theme}")
                st.markdown(f"**Score:** {score_str}  \n**Status:** :{color}[{status}]")

                # Score breakdown
                breakdown = entry.get("score_breakdown")
                if breakdown:
                    st.markdown("**Score Breakdown:**")
                    bd_cols = st.columns(6)
                    for idx, (dim, pts) in enumerate(breakdown.items()):
                        bd_cols[idx % 6].metric(dim.capitalize(), f"{pts}")

            with c2:
                # Media thumbnail
                if media_id:
                    # Fetch media details for thumbnail
                    from src.services.media_queries import fetch_media_by_id
                    media = fetch_media_by_id(media_id)
                    if media and media.get("drive_file_id"):
                        try:
                            thumb = _fetch_thumbnail_b64(media["drive_file_id"])
                            if thumb:
                                st.image(f"data:image/jpeg;base64,{thumb}", use_container_width=True)
                        except Exception:
                            st.caption("(thumbnail unavailable)")
                    st.caption(media["file_name"] if media else media_id[:8])
                else:
                    st.caption("No media assigned")

            # Actions
            st.markdown("---")
            action_cols = st.columns(5)

            with action_cols[0]:
                if st.button("Validate", key=f"val_{entry['id']}", type="primary", disabled=status == "validated"):
                    update_calendar_status(entry["id"], "validated")
                    st.rerun()

            with action_cols[1]:
                if st.button("Skip", key=f"skip_{entry['id']}", disabled=status == "skipped"):
                    update_calendar_status(entry["id"], "skipped")
                    st.rerun()

            with action_cols[2]:
                if st.button("Published", key=f"pub_{entry['id']}", disabled=status == "published"):
                    update_calendar_status(entry["id"], "published")
                    st.rerun()

            with action_cols[3]:
                if st.button("Reset", key=f"reset_{entry['id']}", disabled=status == "generated"):
                    update_calendar_status(entry["id"], "generated")
                    st.rerun()

            # Swap media — show top 5 alternatives
            with action_cols[4]:
                swap_clicked = st.button("Swap Media", key=f"swap_btn_{entry['id']}")

            if swap_clicked:
                st.session_state[f"swap_open_{entry['id']}"] = True

            if st.session_state.get(f"swap_open_{entry['id']}"):
                st.markdown("**Alternative Media (top 5):**")
                all_media = _fetch_analyzed_media()
                recently_used = _fetch_recent_media_ids()
                target_season = entry.get("season_context") or get_current_season(date.fromisoformat(post_date))
                theme_data = None
                if entry.get("theme_id"):
                    theme_data = fetch_active_theme_for_date(date.fromisoformat(post_date))

                # Exclude currently assigned media from candidates
                batch_used = set()
                current_media = entry.get("manual_media_id") or entry.get("media_id")

                candidates = select_best_media(
                    all_media=all_media,
                    target_category=entry.get("target_category"),
                    target_season=target_season,
                    target_format=entry.get("target_format"),
                    min_quality=1,  # Show all quality levels for swap
                    theme=theme_data,
                    recently_used_ids=recently_used,
                    batch_used_ids=batch_used,
                    today=date.fromisoformat(post_date),
                    top_n=6,
                )

                # Filter out currently assigned
                candidates = [(m, s, b) for m, s, b in candidates if m["id"] != current_media][:5]

                if not candidates:
                    st.caption("No alternative candidates found.")
                else:
                    swap_cols = st.columns(5)
                    for idx, (cand, cand_score, cand_bd) in enumerate(candidates):
                        with swap_cols[idx]:
                            # Thumbnail
                            try:
                                thumb = _fetch_thumbnail_b64(cand["drive_file_id"])
                                if thumb:
                                    st.image(f"data:image/jpeg;base64,{thumb}", use_container_width=True)
                            except Exception:
                                pass
                            st.caption(f"{cand.get('category', '?')} | {cand_score:.0f}pts")
                            if st.button("Use", key=f"use_{entry['id']}_{cand['id']}"):
                                update_calendar_media(entry["id"], cand["id"], cand_score, cand_bd)
                                st.session_state[f"swap_open_{entry['id']}"] = False
                                st.rerun()

                if st.button("Cancel", key=f"swap_cancel_{entry['id']}"):
                    st.session_state[f"swap_open_{entry['id']}"] = False
                    st.rerun()

# -------------------------------------------------------
# Summary stats
# -------------------------------------------------------
st.divider()
st.markdown("### Summary")
total = len(calendar_data)
by_status = {}
for e in calendar_data:
    s = e.get("status", "planned")
    by_status[s] = by_status.get(s, 0) + 1

metric_cols = st.columns(len(by_status) + 1)
metric_cols[0].metric("Total Entries", total)
for i, (s, count) in enumerate(sorted(by_status.items()), 1):
    metric_cols[i].metric(s.capitalize(), count)

filled = sum(1 for e in calendar_data if e.get("media_id") or e.get("manual_media_id"))
avg_score = 0.0
scored = [e["media_score"] for e in calendar_data if e.get("media_score")]
if scored:
    avg_score = sum(scored) / len(scored)

c1, c2 = st.columns(2)
c1.metric("Media Assigned", f"{filled}/{total}")
c2.metric("Avg Score", f"{avg_score:.1f}")
