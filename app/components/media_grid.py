"""
Reusable thumbnail grid component.
Downloads Drive thumbnails server-side and embeds as base64 data URIs.
Each thumbnail has View + Delete buttons.
"""
import base64
import io

import streamlit as st
from PIL import Image

from src.services.google_drive import get_drive_service, download_file_bytes
from src.services.media_queries import delete_media


THUMB_SIZE = 300  # px


@st.cache_data(ttl=3600)
def _fetch_thumbnail_b64(file_id: str) -> str:
    """Download a Drive file, resize to thumbnail, return base64 JPEG. Cached 1h."""
    try:
        service = get_drive_service()
        meta = service.files().get(fileId=file_id, fields="thumbnailLink").execute()
        link = meta.get("thumbnailLink")
        if link:
            link = link.replace("=s220", f"=s{THUMB_SIZE}")
            import urllib.request
            data = urllib.request.urlopen(link, timeout=10).read()
            return base64.b64encode(data).decode()
    except Exception:
        pass

    try:
        raw = download_file_bytes(file_id)
        img = Image.open(io.BytesIO(raw))
        img.load()
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        img.thumbnail((THUMB_SIZE, THUMB_SIZE), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


@st.cache_data(ttl=3600)
def _fetch_thumbnails_batch(file_ids: tuple[str, ...]) -> dict[str, str]:
    """Fetch base64 thumbnails for a batch of file IDs."""
    result = {}
    for fid in file_ids:
        result[fid] = _fetch_thumbnail_b64(fid)
    return result


def render_media_grid(
    media_items: list[dict],
    cols: int = 4,
    key_prefix: str = "grid",
) -> dict:
    """
    Render a grid of media thumbnails with View and Delete buttons.

    Returns dict with:
        "view": media_id if View clicked, else None
        "deleted": True if something was deleted
    """
    result = {"view": None, "deleted": False}

    if not media_items:
        st.info("No media found matching filters.")
        return result

    # Fetch base64 thumbnails for visible items
    file_ids = tuple(m["drive_file_id"] for m in media_items if m.get("drive_file_id"))
    with st.spinner("Loading thumbnails..."):
        thumbs = _fetch_thumbnails_batch(file_ids)

    grid_cols = st.columns(cols)

    for idx, media in enumerate(media_items):
        col = grid_cols[idx % cols]
        fid = media.get("drive_file_id", "")
        b64 = thumbs.get(fid, "")
        category = media.get("category", "?")
        quality = media.get("ig_quality", "?")
        name = media.get("file_name", "unnamed")
        mid = media["id"]

        with col:
            if b64:
                st.markdown(
                    f"""<div class="thumb-container">
                        <img src="data:image/jpeg;base64,{b64}" alt="{name}" />
                        <span class="thumb-badge">{category}</span>
                        <span class="thumb-quality">{quality}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""<div class="thumb-container" style="display:flex;align-items:center;justify-content:center;height:200px;background:#2a2a2a;">
                        <span style="color:#888;font-size:11px;">{name[:25]}</span>
                        <span class="thumb-badge">{category}</span>
                        <span class="thumb-quality">{quality}</span>
                    </div>""",
                    unsafe_allow_html=True,
                )

            st.caption(name[:30])

            btn_view, btn_del = st.columns(2)
            if btn_view.button("View", key=f"{key_prefix}_v_{mid}", use_container_width=True):
                result["view"] = mid

            # Delete with confirmation via session_state
            confirm_key = f"{key_prefix}_confirm_{mid}"
            if st.session_state.get(confirm_key):
                st.warning(f"Delete **{name[:20]}**?")
                c_yes, c_no = st.columns(2)
                if c_yes.button("Yes", key=f"{key_prefix}_dy_{mid}", use_container_width=True):
                    if delete_media(mid):
                        st.session_state[confirm_key] = False
                        result["deleted"] = True
                if c_no.button("No", key=f"{key_prefix}_dn_{mid}", use_container_width=True):
                    st.session_state[confirm_key] = False
                    st.rerun()
            else:
                if btn_del.button("Del", key=f"{key_prefix}_d_{mid}", use_container_width=True):
                    st.session_state[confirm_key] = True
                    st.rerun()

    return result
