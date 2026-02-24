"""
View 5 — Videos
Video gallery with filters, player, per-scene detail, and tag correction.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.ui import sidebar_css, page_title
from app.components.media_grid import render_media_grid
from app.components.tag_editor import render_tag_editor
from src.services.media_queries import (
    fetch_all_media,
    fetch_media_by_id,
    fetch_distinct_values,
    delete_media,
)
from src.services.google_drive import download_file_bytes

sidebar_css()
page_title("Video Details", "Browse videos, view scenes, and correct tags")

ITEMS_PER_PAGE = 12


@st.cache_data(ttl=300)
def _download_video_cached(drive_file_id: str) -> bytes:
    """Download video bytes from Drive. Cached 5 min."""
    return download_file_bytes(drive_file_id)


# --- Sidebar filters ---
with st.sidebar:
    st.subheader("Filters")

    categories = fetch_distinct_values("category")
    selected_cats = st.multiselect("Category", categories, key="vid_cat")

    ambiances = fetch_distinct_values("ambiance")
    selected_ambiances = st.multiselect("Ambiance", ambiances, key="vid_amb")

    seasons = fetch_distinct_values("season")
    selected_seasons = st.multiselect("Season", seasons, key="vid_season")

    min_quality = st.slider("Min quality", 1, 10, 1, key="vid_qual")

    sort_by = st.selectbox(
        "Sort by",
        ["Quality (high first)", "Quality (low first)", "Duration (long first)", "File name A-Z"],
        key="vid_sort",
    )

# --- Load and filter ---
all_videos = fetch_all_media(media_type="video")

filtered = all_videos
if selected_cats:
    filtered = [m for m in filtered if m.get("category") in selected_cats]
if selected_ambiances:
    filtered = [
        m for m in filtered
        if isinstance(m.get("ambiance"), list)
        and any(a in selected_ambiances for a in m["ambiance"])
    ]
if selected_seasons:
    filtered = [
        m for m in filtered
        if isinstance(m.get("season"), list)
        and any(s in selected_seasons for s in m["season"])
    ]
filtered = [m for m in filtered if (m.get("ig_quality") or 0) >= min_quality]

# Sort
if sort_by == "Quality (high first)":
    filtered.sort(key=lambda m: m.get("ig_quality") or 0, reverse=True)
elif sort_by == "Quality (low first)":
    filtered.sort(key=lambda m: m.get("ig_quality") or 0)
elif sort_by == "Duration (long first)":
    filtered.sort(key=lambda m: m.get("duration_seconds") or 0, reverse=True)
else:
    filtered.sort(key=lambda m: m.get("file_name", ""))

st.caption(f"{len(filtered)} videos found")

# --- Mode: browse or detail ---
selected_video_id = st.session_state.get("selected_video_id")

# Gallery / Detail toggle
if selected_video_id:
    if st.button("Back to video gallery"):
        del st.session_state["selected_video_id"]
        st.rerun()

    # --- Video detail mode ---
    video = fetch_media_by_id(selected_video_id)
    if not video:
        st.error("Video not found.")
        st.stop()

    st.subheader(video.get("file_name", ""))

    # Video metadata bar
    meta_cols = st.columns(4)
    meta_cols[0].metric("Duration", f"{video.get('duration_seconds', 0):.1f}s")
    scenes = video.get("scenes") or []
    scene_count = len(scenes) if isinstance(scenes, list) else 0
    meta_cols[1].metric("Scenes", scene_count)
    meta_cols[2].metric("Aspect Ratio", video.get("aspect_ratio", "?"))
    meta_cols[3].metric("Quality", video.get("ig_quality", "?"))

    # Video player
    if video.get("drive_file_id"):
        try:
            with st.spinner("Loading video..."):
                video_bytes = _download_video_cached(video["drive_file_id"])
            st.video(video_bytes)
        except Exception as e:
            st.error(f"Could not load video: {e}")

    # Descriptions
    st.markdown("**Description FR:**")
    st.text(video.get("description_fr", "—"))
    st.markdown("**Description EN:**")
    st.text(video.get("description_en", "—"))

    # Per-scene detail
    if isinstance(scenes, list) and scenes:
        st.subheader("Scenes")
        for i, scene in enumerate(scenes):
            with st.expander(
                f"Scene {i+1}: {scene.get('start_sec', 0):.1f}s — {scene.get('end_sec', 0):.1f}s"
            ):
                s_cols = st.columns(3)
                s_cols[0].markdown(f"**Category:** {scene.get('category', '?')}")
                s_cols[1].markdown(f"**Subcategory:** {scene.get('subcategory', '?')}")
                s_cols[2].markdown(f"**Quality:** {scene.get('ig_quality', '?')}")

                ambiance = scene.get("ambiance", [])
                if ambiance:
                    st.markdown(f"**Ambiance:** {', '.join(ambiance)}")

                elements = scene.get("elements", [])
                if elements:
                    st.markdown(f"**Elements:** {', '.join(elements)}")

                desc_fr = scene.get("description_fr", "")
                desc_en = scene.get("description_en", "")
                if desc_fr:
                    st.caption(f"FR: {desc_fr}")
                if desc_en:
                    st.caption(f"EN: {desc_en}")

    # Tag editor
    st.divider()
    saved = render_tag_editor(video, key_prefix="video_detail")
    if saved:
        st.rerun()

    # Delete
    with st.expander("Delete this video"):
        st.warning("This permanently removes the video from the database.")
        if st.button("Confirm Delete", type="primary", key="vid_delete"):
            if delete_media(video["id"]):
                st.success(f"Deleted {video.get('file_name')}")
                del st.session_state["selected_video_id"]
                st.rerun()

else:
    # --- Gallery mode ---
    total = len(filtered)
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
    page = st.number_input("Page", 1, total_pages, 1, key="vid_page")
    start = (page - 1) * ITEMS_PER_PAGE
    page_items = filtered[start : start + ITEMS_PER_PAGE]

    grid_result = render_media_grid(page_items, cols=3, key_prefix="videos")

    if grid_result["deleted"]:
        st.rerun()

    if grid_result["view"]:
        st.session_state["selected_video_id"] = grid_result["view"]
        st.rerun()

    st.caption(f"Page {page} of {total_pages}")
