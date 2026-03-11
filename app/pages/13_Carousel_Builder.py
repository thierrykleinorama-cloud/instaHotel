"""
View 13 — Carousel Builder (AI Lab)
Build multi-image carousel posts for Instagram — manual or AI-assisted.
"""
import base64
import io
import os
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from PIL import Image

from app.components.ui import sidebar_css, page_title
from src.services.media_queries import fetch_all_media, fetch_distinct_values
from src.services.google_drive import download_file_bytes, get_drive_service
from src.services.carousel_queries import (
    save_carousel_draft,
    fetch_carousel_drafts,
    update_carousel_feedback,
    delete_carousel_draft,
)
from src.services.carousel_ai import (
    suggest_carousel_themes,
    select_carousel_images,
    generate_carousel_captions,
)


# --- HEIF support (lazy, once per session) ---
_heif_registered = False

def _ensure_heif():
    global _heif_registered
    if not _heif_registered:
        try:
            from pillow_heif import register_heif_opener
            register_heif_opener()
        except ImportError:
            pass
        _heif_registered = True


# --- Thumbnail helpers (same approach as Gallery page / media_grid.py) ---
THUMB_SIZE = 300

@st.cache_data(ttl=3600)
def _fetch_thumbnail_b64(file_id: str) -> str:
    """Download a Drive file, resize to thumbnail, return base64 JPEG. Cached 1h.
    Two-tier: Drive thumbnailLink (fast) → fallback to Pillow resize."""
    # Tier 1: Drive thumbnail API
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

    # Tier 2: Download + Pillow resize (handles HEIC)
    try:
        _ensure_heif()
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


@st.cache_data(ttl=300)
def _download_thumb(drive_file_id: str) -> bytes:
    return download_file_bytes(drive_file_id)


def _to_jpeg_bytes(raw_bytes: bytes) -> bytes:
    """Convert any image format (HEIC, PNG, JPEG) to JPEG bytes."""
    _ensure_heif()
    img = Image.open(io.BytesIO(raw_bytes))
    if img.mode not in ("RGB",):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def _to_jpeg_b64(raw_bytes: bytes) -> str:
    """Convert any image format (HEIC, PNG, JPEG) to JPEG base64 string."""
    return base64.b64encode(_to_jpeg_bytes(raw_bytes)).decode()


# ---- Page setup ----
sidebar_css()
page_title("Carousel Builder", "Multi-image Instagram carousel posts")

# ---- Initialize session state defaults ----
for _key, _default in [
    ("cb_selected_ids", []),
    ("cb_caption_es", ""),
    ("cb_caption_en", ""),
    ("cb_caption_fr", ""),
    ("cb_hashtags", ""),
    ("cb_hashtags_list", []),
    ("cb_title", ""),
    ("cb_ai_selection_reasons", {}),
    ("cb_ai_themes", []),
    ("cb_ai_theme_title", ""),
    ("cb_ai_theme_desc", ""),
    ("cb_gallery_page", 0),
    # Separate storage keys for AI-generated captions (not tied to widgets)
    ("_cb_gen_caption_es", ""),
    ("_cb_gen_caption_en", ""),
    ("_cb_gen_caption_fr", ""),
]:
    if _key not in st.session_state:
        st.session_state[_key] = _default

selected_ids: list[str] = st.session_state["cb_selected_ids"]

# ---- Fetch all images ONCE, build lookup dict ----
all_media = fetch_all_media(media_type="image")
media_by_id: dict[str, dict] = {m["id"]: m for m in all_media}

# ---- Sidebar filters ----
with st.sidebar:
    st.subheader("Find Images")
    categories = fetch_distinct_values("category")
    sel_cats = st.multiselect("Category", categories, key="cb_cat")
    min_q = st.slider("Min quality", 1, 10, 5, key="cb_minq")
    search = st.text_input("Search filename", key="cb_search")

# Apply filters (uses set for O(1) category lookup)
_sel_cats_set = set(sel_cats) if sel_cats else None
_search_lower = search.lower() if search else None

filtered_media = [
    m for m in all_media
    if (m.get("ig_quality") or 0) >= min_q
    and (_sel_cats_set is None or m.get("category") in _sel_cats_set)
    and (_search_lower is None or _search_lower in m.get("file_name", "").lower())
]

# Pre-fetch selected media objects (used in multiple sections below)
selected_media_objs: list[dict] = [media_by_id[mid] for mid in selected_ids if mid in media_by_id]

# =======================================================================
# STEP 0: AI-Assisted Carousel Creation
# =======================================================================
st.markdown("### AI Carousel Assistant")

build_mode = st.radio(
    "How do you want to build this carousel?",
    ["AI-assisted (recommended)", "Manual selection"],
    key="cb_mode",
    horizontal=True,
)

if build_mode.startswith("AI"):
    tab_themes, tab_custom = st.tabs(["Suggest Themes", "Custom Theme"])

    # --- Tab 1: AI suggests themes ---
    with tab_themes:
        st.caption("Claude analyzes your media library and suggests carousel themes.")

        if st.button("Suggest Carousel Themes", type="primary", key="cb_suggest"):
            with st.spinner("Claude is brainstorming carousel ideas..."):
                try:
                    result = suggest_carousel_themes(all_media, count=5)
                    st.session_state["cb_ai_themes"] = result.get("themes", [])
                    usage = result.get("_usage", {})
                    st.caption(f"Cost: ${usage.get('cost_usd', 0):.4f}")
                except Exception as e:
                    st.error(f"Theme suggestion failed: {e}")

        themes = st.session_state.get("cb_ai_themes", [])
        if themes:
            for i, theme in enumerate(themes):
                with st.expander(
                    f"**{theme.get('title', f'Theme {i+1}')}** — "
                    f"{theme.get('slide_count', '?')} slides | "
                    f"{', '.join(theme.get('categories', []))}",
                    expanded=(i == 0),
                ):
                    st.markdown(theme.get("description", ""))
                    st.caption(f"Ordering: {theme.get('ordering', '?')}")
                    st.caption(f"Hashtags: {theme.get('hashtag_seed', '')}")

                    if st.button("Use this theme", key=f"cb_use_theme_{i}", type="primary"):
                        st.session_state["cb_ai_theme_title"] = theme.get("title", "")
                        st.session_state["cb_ai_theme_desc"] = theme.get("description", "")
                        st.session_state["cb_ai_theme_ordering"] = theme.get("ordering", "best-first")
                        st.session_state["cb_ai_theme_count"] = theme.get("slide_count", 5)
                        st.session_state["cb_ai_theme_cats"] = theme.get("categories", [])
                        st.session_state["_cb_select_images"] = True
                        st.rerun()

    # --- Tab 2: Custom theme ---
    with tab_custom:
        st.caption("Describe your own carousel theme and let AI pick the images.")
        custom_title = st.text_input("Theme title", key="cb_custom_title",
                                     placeholder="e.g., 'Top 5 Sitges Beaches'")
        custom_desc = st.text_area("Description", key="cb_custom_desc", height=80,
                                   placeholder="What should this carousel show? E.g., 'A visual tour of the hotel rooms, from smallest to largest suite'")
        custom_count = st.slider("Number of slides", 2, 10, 5, key="cb_custom_count")
        custom_ordering = st.selectbox("Ordering", [
            "best-first (most eye-catching hook)",
            "narrative arc (beginning \u2192 middle \u2192 end)",
            "chronological (morning \u2192 evening)",
            "variety (alternate categories)",
        ], key="cb_custom_ordering")

        if st.button("AI Select Images", type="primary", key="cb_custom_select",
                      disabled=not custom_title):
            st.session_state["cb_ai_theme_title"] = custom_title
            st.session_state["cb_ai_theme_desc"] = custom_desc
            st.session_state["cb_ai_theme_ordering"] = custom_ordering.split("(")[0].strip()
            st.session_state["cb_ai_theme_count"] = custom_count
            st.session_state["cb_ai_theme_cats"] = []
            st.session_state["_cb_select_images"] = True
            st.rerun()

    # --- AI Image Selection (triggered from either tab) ---
    if st.session_state.pop("_cb_select_images", False):
        theme_title = st.session_state.get("cb_ai_theme_title", "")
        theme_desc = st.session_state.get("cb_ai_theme_desc", "")
        theme_ordering = st.session_state.get("cb_ai_theme_ordering", "best-first")
        theme_count = st.session_state.get("cb_ai_theme_count", 5)
        theme_cats = st.session_state.get("cb_ai_theme_cats", [])

        # Filter candidates by theme categories if specified
        candidates = list(all_media)
        if theme_cats:
            cat_set = set(theme_cats)
            cat_filtered = [m for m in candidates if m.get("category") in cat_set]
            if len(cat_filtered) >= theme_count:
                candidates = cat_filtered

        with st.spinner(f"Claude is selecting {theme_count} images for '{theme_title}'..."):
            try:
                sel_result = select_carousel_images(
                    theme_title=theme_title,
                    theme_description=theme_desc,
                    ordering=theme_ordering,
                    slide_count=theme_count,
                    media_list=candidates,
                )
                selected = sel_result.get("selected", [])
                new_ids = [s["media_id"] for s in sorted(selected, key=lambda x: x.get("position", 0))]

                # Validate IDs via dict lookup (no DB calls)
                valid_ids = [mid for mid in new_ids if mid in media_by_id]
                if valid_ids:
                    st.session_state["cb_selected_ids"] = valid_ids
                    selected_ids = valid_ids
                    st.session_state["cb_title"] = sel_result.get("carousel_title", theme_title)
                    st.session_state["cb_ai_selection_reasons"] = {
                        s["media_id"]: s.get("reason", "") for s in selected
                    }
                    st.success(f"Selected {len(valid_ids)} images! Hook: {sel_result.get('hook_note', '')}")
                else:
                    st.error("AI selection returned no valid image IDs.")

                usage = sel_result.get("_usage", {})
                st.caption(f"Cost: ${usage.get('cost_usd', 0):.4f}")
            except Exception as e:
                st.error(f"AI image selection failed: {e}")

    st.divider()

# =======================================================================
# STEP 1: Manual Image Picker (paginated gallery with thumbnails)
# =======================================================================
GALLERY_PAGE_SIZE = 50

with st.expander(
    f"Image Gallery ({len(filtered_media)} images, {len(selected_ids)} selected)",
    expanded=(build_mode.startswith("Manual") and len(selected_ids) < 2),
):
    # Pagination
    total_pages = max(1, (len(filtered_media) + GALLERY_PAGE_SIZE - 1) // GALLERY_PAGE_SIZE)
    page_idx = st.session_state.get("cb_gallery_page", 0)
    if page_idx >= total_pages:
        page_idx = 0

    start = page_idx * GALLERY_PAGE_SIZE
    page_media = filtered_media[start : start + GALLERY_PAGE_SIZE]

    if total_pages > 1:
        pc1, pc2, pc3 = st.columns([1, 2, 1])
        with pc1:
            if page_idx > 0 and st.button("Previous", key="cb_gal_prev"):
                st.session_state["cb_gallery_page"] = page_idx - 1
                st.rerun()
        with pc2:
            st.caption(f"Page {page_idx + 1} of {total_pages}")
        with pc3:
            if page_idx < total_pages - 1 and st.button("Next", key="cb_gal_next"):
                st.session_state["cb_gallery_page"] = page_idx + 1
                st.rerun()

    # Batch-fetch thumbnails for visible page (Drive API + HEIC-safe)
    _page_file_ids = tuple(m["drive_file_id"] for m in page_media if m.get("drive_file_id"))
    with st.spinner("Loading thumbnails..."):
        _page_thumbs = _fetch_thumbnails_batch(_page_file_ids)

    COLS = 5
    selected_set = set(selected_ids)  # O(1) lookup
    rows = [page_media[i:i + COLS] for i in range(0, len(page_media), COLS)]

    for row_items in rows:
        cols = st.columns(COLS)
        for idx, m in enumerate(row_items):
            with cols[idx]:
                mid = m["id"]
                is_selected = mid in selected_set
                fid = m.get("drive_file_id", "")
                b64 = _page_thumbs.get(fid, "")

                # Show thumbnail as base64 data URI (handles HEIC, fast)
                if b64:
                    border = "3px solid #ff6b35" if is_selected else "none"
                    st.markdown(
                        f'<img src="data:image/jpeg;base64,{b64}" '
                        f'style="width:120px;border-radius:6px;border:{border};" />',
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption(m.get("file_name", "?")[:20])

                if is_selected:
                    st.markdown(f"**#{selected_ids.index(mid) + 1}**")

                cb = st.checkbox(
                    m.get("file_name", "?")[:18],
                    value=is_selected,
                    key=f"cb_sel_{mid}",
                )
                if cb and mid not in selected_set:
                    if len(selected_ids) < 10:
                        selected_ids.append(mid)
                        st.rerun()
                elif not cb and mid in selected_set:
                    selected_ids.remove(mid)
                    st.rerun()

# =======================================================================
# STEP 2: Selected Images & Reorder
# =======================================================================
st.markdown(f"### Selected Images ({len(selected_ids)})")

if len(selected_ids) < 2:
    remaining = 2 - len(selected_ids)
    st.info(f"Select {remaining} more image{'s' if remaining > 1 else ''} to build a carousel.")
else:
    ai_reasons = st.session_state.get("cb_ai_selection_reasons", {})
    n_selected = len(selected_ids)

    # Batch-fetch thumbnails for selected images
    _sel_file_ids = tuple(
        media_by_id[mid]["drive_file_id"]
        for mid in selected_ids
        if mid in media_by_id and media_by_id[mid].get("drive_file_id")
    )
    _sel_thumbs = _fetch_thumbnails_batch(_sel_file_ids)

    # Show images in a numbered horizontal strip
    img_cols = st.columns(min(n_selected, 5))

    for i, mid in enumerate(selected_ids):
        col_idx = i % min(n_selected, 5)
        with img_cols[col_idx]:
            m = media_by_id.get(mid)
            if m:
                fid = m.get("drive_file_id", "")
                b64 = _sel_thumbs.get(fid, "")
                if b64:
                    st.markdown(
                        f'<img src="data:image/jpeg;base64,{b64}" '
                        f'style="width:100%;border-radius:6px;" />',
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption(m.get("file_name", "?")[:15])
                st.caption(f"**#{i + 1}** {m.get('file_name', '?')[:15]}")
            else:
                st.caption(f"**#{i + 1}** (missing)")

            if mid in ai_reasons:
                st.caption(f"*{ai_reasons[mid][:60]}*")

            # Compact button row using use_container_width for even sizing
            bc1, bc2, bc3 = st.columns(3)
            if i > 0:
                if bc1.button("\u25c0", key=f"cb_up_{mid}", help="Move left", use_container_width=True):
                    selected_ids[i], selected_ids[i - 1] = selected_ids[i - 1], selected_ids[i]
                    st.rerun()
            if i < n_selected - 1:
                if bc2.button("\u25b6", key=f"cb_dn_{mid}", help="Move right", use_container_width=True):
                    selected_ids[i], selected_ids[i + 1] = selected_ids[i + 1], selected_ids[i]
                    st.rerun()
            if bc3.button("\u2717", key=f"cb_rm_{mid}", help="Remove", use_container_width=True):
                selected_ids.remove(mid)
                st.rerun()

    st.divider()

    # =======================================================================
    # STEP 3: Preview (all 3 languages stacked, HEIC converted)
    # =======================================================================
    st.markdown("### Preview")

    from app.components.ig_preview import render_ig_preview_carousel

    # Collect b64 images — convert HEIC/PNG to JPEG for preview
    first_m = media_by_id.get(selected_ids[0])
    if first_m and first_m.get("drive_file_id"):
        try:
            all_b64 = []
            for mid in selected_ids:
                m = media_by_id.get(mid)
                if m and m.get("drive_file_id"):
                    try:
                        b = _download_thumb(m["drive_file_id"])
                        all_b64.append(_to_jpeg_b64(b))
                    except Exception:
                        pass

            # Build stacked multilingual caption for preview.
            # Read from BOTH widget keys AND backup keys (widget keys
            # only have values after their text_area renders further down).
            caption_parts = []
            _pv_es = st.session_state.get("cb_caption_es", "") or st.session_state.get("_cb_gen_caption_es", "")
            _pv_en = st.session_state.get("cb_caption_en", "") or st.session_state.get("_cb_gen_caption_en", "")
            _pv_fr = st.session_state.get("cb_caption_fr", "") or st.session_state.get("_cb_gen_caption_fr", "")
            if _pv_es:
                caption_parts.append(_pv_es)
            if _pv_en:
                caption_parts.append(f"\U0001f1ec\U0001f1e7 {_pv_en}")
            if _pv_fr:
                caption_parts.append(f"\U0001f1eb\U0001f1f7 {_pv_fr}")
            caption_text = "\n\n".join(caption_parts)

            hashtags_text = " ".join(f"#{h}" for h in st.session_state.get("cb_hashtags_list", []))

            html, height = render_ig_preview_carousel(
                images_b64=all_b64,
                caption=caption_text,
                hashtags=hashtags_text,
            )
            st.components.v1.html(html, height=height)
        except Exception as e:
            st.warning(f"Preview unavailable: {e}")

    st.divider()

    # =======================================================================
    # STEP 3b: Export as Reel (image slideshow + optional music)
    # =======================================================================
    st.markdown("### Export as Reel")
    st.caption("Stitch selected images into a video slideshow with Ken Burns effect, optionally add music.")

    # Initialize session state for reel
    for _rk, _rv in [
        ("cb_reel_bytes", None),
        ("cb_reel_duration", 0.0),
        ("cb_reel_cost", 0.0),
    ]:
        if _rk not in st.session_state:
            st.session_state[_rk] = _rv

    rc1, rc2 = st.columns(2)
    with rc1:
        reel_duration = st.slider(
            "Duration per slide (seconds)", 2.0, 5.0, 3.0, 0.5,
            key="cb_reel_slide_dur",
        )
    with rc2:
        reel_aspect = st.selectbox(
            "Aspect ratio",
            ["9:16 (Reel)", "4:5 (Feed)"],
            key="cb_reel_aspect",
        )

    reel_add_music = st.checkbox("Add background music", key="cb_reel_music")

    if reel_add_music:
        mc1, mc2 = st.columns(2)
        with mc1:
            reel_mood = st.selectbox(
                "Mood",
                ["Relaxed", "Upbeat", "Mediterranean", "Ambient", "Elegant"],
                key="cb_reel_mood",
            )
        with mc2:
            reel_custom_prompt = st.text_input(
                "Or custom prompt (overrides mood)",
                key="cb_reel_custom_prompt",
                placeholder="e.g., soft piano with ocean waves",
            )

    # --- Generate Reel ---
    if st.button("Generate Reel", type="primary", key="cb_gen_reel"):
        from src.services.video_composer import images_to_slideshow, composite_video_audio

        aspect = reel_aspect.split(" ")[0]  # "9:16" or "4:5"
        total_cost = 0.0

        with st.spinner("Creating slideshow..."):
            try:
                # Download all selected images
                img_list = []
                for mid in selected_ids:
                    m = media_by_id.get(mid)
                    if m and m.get("drive_file_id"):
                        img_list.append(_download_thumb(m["drive_file_id"]))

                if len(img_list) < 2:
                    st.error("Need at least 2 downloadable images.")
                else:
                    # Step 1: Create slideshow
                    slide_result = images_to_slideshow(
                        img_list,
                        duration_per_slide=reel_duration,
                        aspect_ratio=aspect,
                    )
                    reel_bytes = slide_result["video_bytes"]
                    reel_dur = slide_result["duration_sec"]

                    # Step 2: Add music if requested
                    if reel_add_music:
                        from src.services.music_generator import generate_music

                        prompt = reel_custom_prompt.strip() if reel_custom_prompt.strip() else None
                        if not prompt:
                            mood_prompts = {
                                "Relaxed": "soft acoustic guitar, warm ambient pads, relaxing beach vibes",
                                "Upbeat": "upbeat acoustic pop, light percussion, happy summer feeling",
                                "Mediterranean": "Spanish guitar, light flamenco rhythm, sea breeze",
                                "Ambient": "ambient pads, soft piano, minimalist peaceful atmosphere",
                                "Elegant": "smooth jazz piano, subtle strings, luxury hotel lounge",
                            }
                            prompt = mood_prompts.get(reel_mood, mood_prompts["Relaxed"])

                        st.spinner("Generating music...")
                        music_duration = int(reel_dur) + 1  # slightly longer to cover
                        music_result = generate_music(prompt, duration=music_duration)
                        audio_bytes = music_result["audio_bytes"]
                        total_cost += music_result.get("_cost", {}).get("cost_usd", 0)

                        st.spinner("Compositing video + audio...")
                        comp_result = composite_video_audio(
                            reel_bytes, audio_bytes, volume=0.3,
                        )
                        reel_bytes = comp_result["video_bytes"]

                    st.session_state["cb_reel_bytes"] = reel_bytes
                    st.session_state["cb_reel_duration"] = reel_dur
                    st.session_state["cb_reel_cost"] = total_cost
                    st.rerun()

            except Exception as e:
                st.error(f"Reel generation failed: {e}")

    # --- Show result if available ---
    if st.session_state.get("cb_reel_bytes"):
        reel_bytes = st.session_state["cb_reel_bytes"]
        reel_dur = st.session_state.get("cb_reel_duration", 0)
        reel_cost = st.session_state.get("cb_reel_cost", 0)

        st.video(reel_bytes)
        st.caption(
            f"Duration: {reel_dur:.1f}s | "
            f"Size: {len(reel_bytes) / 1024 / 1024:.1f} MB | "
            f"Cost: ${reel_cost:.4f}"
        )

        st.download_button(
            "Download Reel MP4",
            data=reel_bytes,
            file_name="carousel_reel.mp4",
            mime="video/mp4",
            key="cb_dl_reel",
        )

        # --- Publish reel to Instagram (shared component) ---
        from app.components.ig_publish import render_publish_to_ig

        # Build default caption from carousel captions
        _reel_cap_parts = []
        _reel_es = st.session_state.get("cb_caption_es", "") or st.session_state.get("_cb_gen_caption_es", "")
        _reel_en = st.session_state.get("cb_caption_en", "") or st.session_state.get("_cb_gen_caption_en", "")
        _reel_fr = st.session_state.get("cb_caption_fr", "") or st.session_state.get("_cb_gen_caption_fr", "")
        if _reel_es:
            _reel_cap_parts.append(_reel_es)
        if _reel_en:
            _reel_cap_parts.append(f"\U0001f1ec\U0001f1e7\n{_reel_en}")
        if _reel_fr:
            _reel_cap_parts.append(f"\U0001f1eb\U0001f1f7\n{_reel_fr}")
        _reel_default_caption = "\n\n".join(_reel_cap_parts)
        _reel_default_hashtags = " ".join(f"#{h}" for h in st.session_state.get("cb_hashtags_list", []))

        render_publish_to_ig(
            media_bytes=reel_bytes,
            media_type="REELS",
            filename=f"carousel_reel_{selected_ids[0][:8]}.mp4",
            mime_type="video/mp4",
            key_prefix="cb_reel_pub",
            default_caption=_reel_default_caption,
            default_hashtags=_reel_default_hashtags,
        )

    st.divider()

    # =======================================================================
    # STEP 4: Captions & Hashtags (manual + AI)
    # =======================================================================
    st.markdown("### Captions & Hashtags")

    # --- AI Caption Generation ---
    # Use a flag pattern to avoid widget key conflicts with session_state writes
    if st.session_state.pop("_cb_captions_generated", False):
        st.success("Captions generated!")

    if st.button("AI Generate Captions", type="secondary", key="cb_ai_captions"):
        theme_title = st.session_state.get("cb_ai_theme_title", "") or st.session_state.get("cb_title", "Hotel carousel")
        theme_desc = st.session_state.get("cb_ai_theme_desc", "") or "Carousel post for Hotel Noucentista"

        # Use pre-fetched media objects (no extra DB calls)
        sel_media = [media_by_id[mid] for mid in selected_ids if mid in media_by_id]

        with st.spinner("Claude is writing carousel captions..."):
            try:
                cap_result = generate_carousel_captions(
                    theme_title=theme_title,
                    theme_description=theme_desc,
                    selected_media=sel_media,
                )
                new_es = cap_result.get("caption_es", "")
                new_en = cap_result.get("caption_en", "")
                new_fr = cap_result.get("caption_fr", "")

                # Store in backup keys (not tied to widgets — always reliable)
                st.session_state["_cb_gen_caption_es"] = new_es
                st.session_state["_cb_gen_caption_en"] = new_en
                st.session_state["_cb_gen_caption_fr"] = new_fr

                # Delete widget keys THEN set new values + rerun
                for k in ["cb_caption_es", "cb_caption_en", "cb_caption_fr", "cb_hashtags"]:
                    st.session_state.pop(k, None)
                st.session_state["cb_caption_es"] = new_es
                st.session_state["cb_caption_en"] = new_en
                st.session_state["cb_caption_fr"] = new_fr
                hashtags = cap_result.get("hashtags", [])
                if hashtags:
                    st.session_state["cb_hashtags"] = ", ".join(hashtags)
                    st.session_state["cb_hashtags_list"] = hashtags
                st.session_state["_cb_captions_generated"] = True
                st.rerun()
            except Exception as e:
                st.error(f"Caption generation failed: {e}")

    cap_es = st.text_area("Caption (ES)", height=100, key="cb_caption_es",
                          placeholder="Caption en espa\u00f1ol...")
    cap_en = st.text_area("Caption (EN)", height=100, key="cb_caption_en",
                          placeholder="English caption...")
    cap_fr = st.text_area("Caption (FR)", height=100, key="cb_caption_fr",
                          placeholder="L\u00e9gende en fran\u00e7ais...")

    # Sync backup keys whenever user edits manually
    st.session_state["_cb_gen_caption_es"] = cap_es
    st.session_state["_cb_gen_caption_en"] = cap_en
    st.session_state["_cb_gen_caption_fr"] = cap_fr

    hashtags_str = st.text_input(
        "Hashtags (comma-separated)",
        key="cb_hashtags",
        placeholder="sitges, hotel, mediterranean",
    )
    hashtags_list = [h.strip().lstrip("#") for h in hashtags_str.split(",") if h.strip()]
    st.session_state["cb_hashtags_list"] = hashtags_list

    if hashtags_list:
        st.caption(" ".join(f"#{h}" for h in hashtags_list))

    st.divider()

    # =======================================================================
    # STEP 5: Save & Publish
    # =======================================================================
    st.markdown("### Save & Publish")

    title = st.text_input("Carousel title (internal)", key="cb_title",
                          placeholder="e.g., 'Top 5 Sitges Beaches'")

    if st.button("Save Draft", type="primary", key="cb_save",
                  disabled=len(selected_ids) < 2):
        draft_id = save_carousel_draft(
            title=title or "Untitled Carousel",
            media_ids=selected_ids,
            caption_es=cap_es,
            caption_en=cap_en,
            caption_fr=cap_fr,
            hashtags=hashtags_list,
        )
        if draft_id:
            st.success(f"Draft saved! ID: {draft_id[:8]}...")
        else:
            st.error("Failed to save draft.")

    # --- Publish carousel to Instagram (shared component) ---
    from app.components.ig_publish import render_publish_carousel_to_ig

    # Prepare JPEG bytes for each selected image (cached via _download_thumb)
    _carousel_jpeg_list = []
    for _cid in selected_ids:
        _cm = media_by_id.get(_cid)
        if _cm and _cm.get("drive_file_id"):
            try:
                _carousel_jpeg_list.append(_to_jpeg_bytes(_download_thumb(_cm["drive_file_id"])))
            except Exception:
                pass

    # Build default multilingual caption
    _car_cap_parts = []
    if cap_es:
        _car_cap_parts.append(cap_es)
    if cap_en:
        _car_cap_parts.append(f"\U0001f1ec\U0001f1e7\n{cap_en}")
    if cap_fr:
        _car_cap_parts.append(f"\U0001f1eb\U0001f1f7\n{cap_fr}")
    _car_default_caption = "\n\n".join(_car_cap_parts)
    _car_default_hashtags = " ".join(f"#{h}" for h in hashtags_list)

    render_publish_carousel_to_ig(
        image_bytes_list=_carousel_jpeg_list,
        key_prefix="cb_car_pub",
        default_caption=_car_default_caption,
        default_hashtags=_car_default_hashtags,
    )

# =======================================================================
# Saved Drafts
# =======================================================================
st.divider()
st.markdown("### Saved Drafts")

draft_status = st.selectbox(
    "Filter",
    ["draft", "accepted", "rejected", "published", "all"],
    key="cb_draft_filter",
)
drafts = fetch_carousel_drafts(status=draft_status)

if not drafts:
    st.caption("No carousel drafts found.")
else:
    _status_colors = {
        "draft": "blue", "accepted": "green", "rejected": "red",
        "published": "violet", "validated": "orange",
    }
    for d in drafts:
        _color = _status_colors.get(d["status"], "gray")
        with st.expander(
            f":{_color}[{d['status'].upper()}] {d.get('title', 'Untitled')} "
            f"({len(d.get('media_ids', []))} images) \u2014 {d.get('created_at', '?')[:16]}"
        ):
            st.caption(f"ID: {d['id'][:12]}...")
            if d.get("caption_es"):
                st.text(d["caption_es"][:200])
            if d.get("hashtags"):
                st.caption(" ".join(f"#{h}" for h in d["hashtags"]))
            if d.get("ig_permalink"):
                st.markdown(f"[View on Instagram]({d['ig_permalink']})")

            # Show previous feedback/rating if any
            if d.get("feedback"):
                st.markdown(f"Feedback: *{d['feedback']}*")
            if d.get("rating"):
                st.markdown(f"Rating: {'★' * d['rating']}")

            # Accept / Reject controls
            _d_id = d["id"]
            _d_status = d["status"]
            ar1, ar2 = st.columns(2)
            with ar1:
                _acc_label = "Accepted" if _d_status == "accepted" else "Accept"
                if st.button(
                    _acc_label, key=f"cb_acc_{_d_id}",
                    type="primary" if _d_status != "accepted" else "secondary",
                    use_container_width=True,
                ):
                    update_carousel_feedback(_d_id, "accepted")
                    st.rerun()
            with ar2:
                _rej_label = "Rejected" if _d_status == "rejected" else "Reject"
                if st.button(
                    _rej_label, key=f"cb_rej_{_d_id}",
                    type="secondary",
                    use_container_width=True,
                ):
                    update_carousel_feedback(_d_id, "rejected")
                    st.rerun()

            # Load / Delete actions
            dc1, dc2 = st.columns(2)
            with dc1:
                if _d_status in ("draft", "accepted"):
                    if st.button("Load into editor", key=f"cb_load_{_d_id}"):
                        for k in ["cb_caption_es", "cb_caption_en", "cb_caption_fr", "cb_hashtags", "cb_title"]:
                            st.session_state.pop(k, None)
                        st.session_state["cb_selected_ids"] = d.get("media_ids", [])
                        st.session_state["cb_caption_es"] = d.get("caption_es", "")
                        st.session_state["cb_caption_en"] = d.get("caption_en", "")
                        st.session_state["cb_caption_fr"] = d.get("caption_fr", "")
                        st.session_state["_cb_gen_caption_es"] = d.get("caption_es", "")
                        st.session_state["_cb_gen_caption_en"] = d.get("caption_en", "")
                        st.session_state["_cb_gen_caption_fr"] = d.get("caption_fr", "")
                        st.session_state["cb_title"] = d.get("title", "")
                        ht = d.get("hashtags", [])
                        st.session_state["cb_hashtags"] = ", ".join(ht) if ht else ""
                        st.session_state["cb_hashtags_list"] = ht or []
                        st.rerun()
            with dc2:
                if _d_status in ("draft", "rejected"):
                    if st.button("Delete", key=f"cb_del_{_d_id}"):
                        delete_carousel_draft(_d_id)
                        st.rerun()
