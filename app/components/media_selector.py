"""
Shared sidebar media selector — used by AI Captions and AI Enhancement subpages.
"""
import streamlit as st

from src.services.media_queries import fetch_all_media, fetch_media_by_id, fetch_distinct_values
from src.services.google_drive import download_file_bytes


@st.cache_data(ttl=300)
def _download_raw(drive_file_id: str) -> bytes:
    """Download raw image bytes from Drive for display."""
    return download_file_bytes(drive_file_id)


def render_media_selector(key_prefix: str) -> tuple[dict, bytes]:
    """Render sidebar media filters + selector. Returns (media_record, image_bytes).

    Calls st.stop() if no images match or media can't be loaded.
    key_prefix avoids widget key collisions between pages.
    """
    with st.sidebar:
        st.subheader("Find Media")

        categories = fetch_distinct_values("category")
        selected_cats = st.multiselect("Category", categories, key=f"{key_prefix}_cat")

        subcategories = fetch_distinct_values("subcategory")
        selected_subcats = st.multiselect("Subcategory", subcategories, key=f"{key_prefix}_subcat")

        ambiances = fetch_distinct_values("ambiance")
        selected_ambiances = st.multiselect("Ambiance", ambiances, key=f"{key_prefix}_amb")

        seasons_filter = fetch_distinct_values("season")
        selected_seasons = st.multiselect("Season filter", seasons_filter, key=f"{key_prefix}_season_filter")

        min_quality = st.slider("Min quality", 1, 10, 1, key=f"{key_prefix}_qual")
        max_quality = st.slider("Max quality", 1, 10, 10, key=f"{key_prefix}_qual_max")

        search = st.text_input("Search filename", key=f"{key_prefix}_search")
        elements_search = st.text_input(
            "Search elements", key=f"{key_prefix}_elem_search",
            help="e.g. piscine, vue_mer, terrasse",
        )

        st.divider()

        # Build filtered list — images only
        all_media = fetch_all_media(media_type="image")

        if selected_cats:
            all_media = [m for m in all_media if m.get("category") in selected_cats]
        if selected_subcats:
            all_media = [m for m in all_media if m.get("subcategory") in selected_subcats]
        if selected_ambiances:
            all_media = [
                m for m in all_media
                if isinstance(m.get("ambiance"), list)
                and any(a in selected_ambiances for a in m["ambiance"])
            ]
        if selected_seasons:
            all_media = [
                m for m in all_media
                if isinstance(m.get("season"), list)
                and any(s in selected_seasons for s in m["season"])
            ]
        all_media = [m for m in all_media if min_quality <= (m.get("ig_quality") or 0) <= max_quality]
        if search:
            all_media = [
                m for m in all_media
                if search.lower() in m.get("file_name", "").lower()
            ]
        if elements_search:
            kw = elements_search.lower()
            all_media = [
                m for m in all_media
                if isinstance(m.get("elements"), list)
                and any(kw in e.lower() for e in m["elements"])
            ]

        st.caption(f"{len(all_media)} images match")

        media_options = {m["file_name"]: m["id"] for m in all_media}
        if media_options:
            selected_name = st.selectbox("Select", list(media_options.keys()), key=f"{key_prefix}_select")
            media_id = media_options[selected_name]
        else:
            st.warning("No images match the current filters.")
            st.stop()

    # Load selected media
    media = fetch_media_by_id(media_id)
    if not media:
        st.error("Media not found.")
        st.stop()

    # Download image bytes
    if not media.get("drive_file_id"):
        st.warning("No Drive file linked to this media.")
        st.stop()

    try:
        image_bytes = _download_raw(media["drive_file_id"])
    except Exception as e:
        st.error(f"Could not download image: {e}")
        st.stop()

    # Preview
    col_preview, col_info = st.columns([1, 2])
    with col_preview:
        st.image(image_bytes, width=300)
    with col_info:
        st.markdown(f"**{media.get('file_name', '')}**")
        st.caption(f"Category: {media.get('category')} | Quality: {media.get('ig_quality')}")
        st.text(media.get("description_en", ""))

    st.divider()

    return media, image_bytes
