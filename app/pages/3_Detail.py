"""
View 3 — Media Detail & Tag Correction
Full-size image from Drive, read-only descriptions, editable tags via tag_editor.
Images only — videos have their own page.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import base64
import io

import streamlit as st
from PIL import Image

from app.components.ui import sidebar_css, page_title
from app.components.tag_editor import render_tag_editor
from src.services.media_queries import (
    fetch_media_by_id,
    fetch_all_media,
    fetch_distinct_values,
    delete_media,
)
from src.services.google_drive import download_file_bytes


@st.cache_data(ttl=300)
def _download_for_display(drive_file_id: str) -> bytes:
    """Download raw image bytes from Drive."""
    return download_file_bytes(drive_file_id)


def _to_base64_jpeg(raw_bytes: bytes) -> str:
    """Convert raw image bytes to base64 JPEG for HTML display."""
    img = Image.open(io.BytesIO(raw_bytes))
    img.load()
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


sidebar_css()
page_title("Detail", "View full-size image and correct AI tags")

# --- Sidebar: filters + media selector ---
media_id = st.session_state.get("selected_media_id")

with st.sidebar:
    st.subheader("Find Media")

    # Filters (same as Gallery)
    categories = fetch_distinct_values("category")
    selected_cats = st.multiselect("Category", categories, key="det_cat")

    subcategories = fetch_distinct_values("subcategory")
    selected_subcats = st.multiselect("Subcategory", subcategories, key="det_subcat")

    ambiances = fetch_distinct_values("ambiance")
    selected_ambiances = st.multiselect("Ambiance", ambiances, key="det_amb")

    seasons = fetch_distinct_values("season")
    selected_seasons = st.multiselect("Season", seasons, key="det_season")

    min_quality = st.slider("Min quality", 1, 10, 1, key="det_qual")

    # Search by filename
    search = st.text_input("Search filename", key="det_search")

    # Search by elements keyword
    elements_search = st.text_input("Search elements", key="det_elem_search",
                                     help="e.g. piscine, vue_mer, terrasse")

    st.divider()

    # Build filtered list — images only
    all_images = fetch_all_media(media_type="image")

    if selected_cats:
        all_images = [m for m in all_images if m.get("category") in selected_cats]
    if selected_subcats:
        all_images = [m for m in all_images if m.get("subcategory") in selected_subcats]
    if selected_ambiances:
        all_images = [
            m for m in all_images
            if isinstance(m.get("ambiance"), list)
            and any(a in selected_ambiances for a in m["ambiance"])
        ]
    if selected_seasons:
        all_images = [
            m for m in all_images
            if isinstance(m.get("season"), list)
            and any(s in selected_seasons for s in m["season"])
        ]
    all_images = [m for m in all_images if (m.get("ig_quality") or 0) >= min_quality]
    if search:
        all_images = [
            m for m in all_images
            if search.lower() in m.get("file_name", "").lower()
        ]
    if elements_search:
        kw = elements_search.lower()
        all_images = [
            m for m in all_images
            if isinstance(m.get("elements"), list)
            and any(kw in e.lower() for e in m["elements"])
        ]

    st.caption(f"{len(all_images)} images match")

    if all_images:
        labels = [m["file_name"] for m in all_images]

        # Find current selection
        current_idx = 0
        if media_id:
            for i, m in enumerate(all_images):
                if m["id"] == media_id:
                    current_idx = i
                    break

        selected_label = st.selectbox("Select", labels, index=current_idx, key="det_select")
        sel_idx = labels.index(selected_label)
        media_id = all_images[sel_idx]["id"]
        st.session_state["selected_media_id"] = media_id

        # Prev/Next
        col_prev, col_next = st.columns(2)
        if col_prev.button("Prev", use_container_width=True, disabled=sel_idx == 0):
            st.session_state["selected_media_id"] = all_images[sel_idx - 1]["id"]
            st.rerun()
        if col_next.button("Next", use_container_width=True, disabled=sel_idx >= len(all_images) - 1):
            st.session_state["selected_media_id"] = all_images[sel_idx + 1]["id"]
            st.rerun()
    else:
        st.info("No images match the current filters.")

if not media_id:
    st.info("Select an image from the sidebar filters or the Gallery page.")
    st.stop()

# --- Load media ---
media = fetch_media_by_id(media_id)
if not media:
    st.error(f"Media {media_id} not found.")
    st.stop()

# If somehow a video was selected (e.g. from Gallery), redirect
if media.get("media_type") == "video":
    st.info("This is a video. Redirecting to Videos page.")
    st.session_state["selected_video_id"] = media_id
    st.switch_page("pages/5_Videos.py")

# --- Layout ---
left_col, right_col = st.columns([3, 2])

with left_col:
    st.subheader(media.get("file_name", ""))

    # Full-size image
    if media.get("drive_file_id"):
        try:
            raw_bytes = _download_for_display(media["drive_file_id"])
            b64 = _to_base64_jpeg(raw_bytes)
            st.markdown(
                f'<img src="data:image/jpeg;base64,{b64}" style="width:100%;border-radius:8px;" />',
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.error(f"Could not load image: {e}")

    # Read-only descriptions
    st.markdown("**Description FR:**")
    st.text(media.get("description_fr", "—"))
    st.markdown("**Description EN:**")
    st.text(media.get("description_en", "—"))

    # File metadata
    with st.expander("File Metadata"):
        st.json(
            {
                "id": media.get("id"),
                "drive_file_id": media.get("drive_file_id"),
                "file_path": media.get("file_path"),
                "mime_type": media.get("mime_type"),
                "file_size_bytes": media.get("file_size_bytes"),
                "aspect_ratio": media.get("aspect_ratio"),
                "analyzed_at": media.get("analyzed_at"),
                "analysis_model": media.get("analysis_model"),
            }
        )

    # Delete
    with st.expander("Delete this image"):
        st.warning("Removes from database only. Original stays in Google Drive.")
        if st.button("Confirm Delete", type="primary", key="det_delete"):
            fname = media.get("file_name")
            if delete_media(media["id"]):
                st.success(f"Deleted {fname}")
                del st.session_state["selected_media_id"]
                st.rerun()

with right_col:
    saved = render_tag_editor(media, key_prefix="detail")
    if saved:
        st.rerun()
