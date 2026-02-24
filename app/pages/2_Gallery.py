"""
View 2 — Filterable Gallery
Photo grid with sidebar filters, base64 thumbnails, pagination, click-to-detail.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.ui import sidebar_css, page_title
from app.components.media_grid import render_media_grid
from src.services.media_queries import fetch_all_media, fetch_distinct_values

sidebar_css()
page_title("Gallery", "Browse and filter the media library")

ITEMS_PER_PAGE = 12

# --- Sidebar filters ---
with st.sidebar:
    st.subheader("Filters")

    media_type = st.radio(
        "Media type", ["All", "Images", "Videos"], horizontal=True, key="gal_type"
    )
    type_map = {"All": None, "Images": "image", "Videos": "video"}
    selected_type = type_map[media_type]

    categories = fetch_distinct_values("category")
    selected_cats = st.multiselect("Category", categories, key="gal_cat")

    subcategories = fetch_distinct_values("subcategory")
    selected_subcats = st.multiselect("Subcategory", subcategories, key="gal_subcat")

    ambiances = fetch_distinct_values("ambiance")
    selected_ambiances = st.multiselect("Ambiance", ambiances, key="gal_amb")

    seasons = fetch_distinct_values("season")
    selected_seasons = st.multiselect("Season", seasons, key="gal_season")

    min_quality = st.slider("Min quality", 1, 10, 1, key="gal_qual")

    sort_by = st.selectbox(
        "Sort by",
        ["Quality (high first)", "Quality (low first)", "File name A-Z", "File name Z-A"],
        key="gal_sort",
    )

# --- Load and filter data ---
all_media = fetch_all_media(media_type=selected_type)

filtered = all_media
if selected_cats:
    filtered = [m for m in filtered if m.get("category") in selected_cats]
if selected_subcats:
    filtered = [m for m in filtered if m.get("subcategory") in selected_subcats]
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
elif sort_by == "File name A-Z":
    filtered.sort(key=lambda m: m.get("file_name", ""))
else:
    filtered.sort(key=lambda m: m.get("file_name", ""), reverse=True)

# --- Pagination ---
total = len(filtered)
total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

col_info, col_page = st.columns([2, 1])
col_info.caption(f"{total} media found")
page = col_page.number_input("Page", 1, total_pages, 1, key="gal_page")

start = (page - 1) * ITEMS_PER_PAGE
page_items = filtered[start : start + ITEMS_PER_PAGE]

# --- Render grid ---
grid_result = render_media_grid(page_items, cols=4, key_prefix="gallery")

if grid_result["deleted"]:
    st.rerun()

if grid_result["view"]:
    st.session_state["selected_media_id"] = grid_result["view"]
    st.switch_page("pages/3_Image_Details.py")

st.caption(f"Page {page} of {total_pages}")
