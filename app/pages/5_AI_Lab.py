"""
View 4 — Test Lab
Generate Instagram captions from media metadata (and optionally the image).
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import io

import streamlit as st

from app.components.ui import sidebar_css, page_title
from app.components.media_grid import render_media_grid
from src.services.media_queries import fetch_all_media, fetch_media_by_id
from src.services.caption_generator import generate_captions
from src.services.google_drive import download_file_bytes
from src.utils import encode_image_bytes


@st.cache_data(ttl=300)
def _download_and_encode(drive_file_id: str) -> str:
    """Download image from Drive and return base64. Cached 5 min."""
    image_bytes = download_file_bytes(drive_file_id)
    return encode_image_bytes(image_bytes)


@st.cache_data(ttl=300)
def _download_raw(drive_file_id: str) -> bytes:
    """Download raw image bytes from Drive for display."""
    return download_file_bytes(drive_file_id)


sidebar_css()
page_title("AI Lab", "Test AI transformations on your media")

with st.expander("How does this work?", expanded=False):
    st.markdown("""
**Test Lab** lets you generate Instagram captions for any photo in your library using Claude AI.

**How to use:**
1. **Select a photo** from the sidebar (search by filename or browse the list)
2. **Set editorial context** — choose a theme, season, and call-to-action type
3. **Click "Generate Captions"** — Claude generates 2 caption variants in 3 languages:
   - **Short**: 2-3 punchy lines, great for quick posts
   - **Storytelling**: 5-6 emotional lines, great for engagement
   - Each variant in **Spanish, English, and French**
   - Plus **20 optimized hashtags**
4. **"Regenerate"** creates fresh new captions (never cached)

**Include image toggle:**
- **OFF** (default): sends only metadata (description, tags, ambiance) — fast, ~$0.003/call
- **ON**: also sends the actual photo to Claude — richer results, ~$0.01/call

Use `st.code()` blocks to easily copy captions for manual posting.
""")


# --- Media selection ---
with st.sidebar:
    st.subheader("Select Media")
    all_media = fetch_all_media(media_type="image")

    # Search by name
    search = st.text_input("Search by filename", key="lab_search")
    if search:
        all_media = [m for m in all_media if search.lower() in m.get("file_name", "").lower()]

    # Quick select from list
    media_options = {m["file_name"]: m["id"] for m in all_media[:100]}
    if media_options:
        selected_name = st.selectbox("File", list(media_options.keys()), key="lab_select")
        media_id = media_options[selected_name]
    else:
        st.warning("No images found.")
        st.stop()

    st.divider()
    st.subheader("Editorial Context")

    theme = st.selectbox(
        "Theme",
        ["chambre", "destination", "experience", "gastronomie", "offre"],
        key="lab_theme",
    )
    season = st.selectbox(
        "Season",
        ["printemps", "ete", "automne", "hiver", "toute_saison"],
        key="lab_season",
    )
    CTA_OPTIONS = {
        "Link in bio — Drive to profile link": "link_bio",
        "Send a DM — Encourage direct messages": "dm",
        "Book now — Direct booking push": "book_now",
        "Comment — Ask a question to drive engagement": "comment",
        "Tag a friend — Organic reach boost": "tag_friend",
        "Save this post — Signal quality to algorithm": "save_post",
        "Share — Encourage sharing for virality": "share",
        "Visit website — Drive to hotel website": "visit_website",
        "Call us — Direct phone conversion": "call_us",
        "Special offer — Promo code or discount": "offer",
        "Poll — A or B question for interaction": "poll",
        "Discover Sitges — Destination-driven soft sell": "location",
    }
    cta_label = st.selectbox(
        "Call to Action",
        list(CTA_OPTIONS.keys()),
        key="lab_cta",
    )
    cta_type = CTA_OPTIONS[cta_label]

    include_image = st.checkbox(
        "Include image in prompt",
        value=False,
        help="OFF: metadata only (~$0.003). ON: sends image for richer captions (~$0.01).",
        key="lab_include_img",
    )

# --- Load selected media ---
media = fetch_media_by_id(media_id)
if not media:
    st.error("Media not found.")
    st.stop()

# Show preview
col_preview, col_info = st.columns([1, 2])
with col_preview:
    if media.get("drive_file_id"):
        try:
            preview_bytes = _download_raw(media["drive_file_id"])
            st.image(preview_bytes, width=300)
        except Exception:
            st.caption(media.get("file_name", ""))
with col_info:
    st.markdown(f"**{media.get('file_name', '')}**")
    st.caption(f"Category: {media.get('category')} | Quality: {media.get('ig_quality')}")
    st.text(media.get("description_en", ""))

st.divider()

# --- Generate captions ---
col_gen, col_regen = st.columns([1, 1])
generate_clicked = col_gen.button("Generate Captions", type="primary", use_container_width=True)
regenerate_clicked = col_regen.button("Regenerate", use_container_width=True)

if generate_clicked or regenerate_clicked:
    image_b64 = None
    if include_image and media.get("drive_file_id"):
        with st.spinner("Downloading image..."):
            image_b64 = _download_and_encode(media["drive_file_id"])

    with st.spinner("Generating captions..."):
        try:
            result = generate_captions(
                media=media,
                theme=theme,
                season=season,
                cta_type=cta_type,
                include_image=include_image,
                image_base64=image_b64,
            )
            st.session_state["lab_result"] = result
        except Exception as e:
            st.error(f"Generation failed: {e}")

# --- Display results ---
result = st.session_state.get("lab_result")
if result:
    st.subheader("Generated Captions")

    # Short variant
    short_tab_es, short_tab_en, short_tab_fr = st.tabs(["Short ES", "Short EN", "Short FR"])
    short = result.get("short", {})
    with short_tab_es:
        st.code(short.get("es", ""), language=None)
    with short_tab_en:
        st.code(short.get("en", ""), language=None)
    with short_tab_fr:
        st.code(short.get("fr", ""), language=None)

    # Storytelling variant
    story_tab_es, story_tab_en, story_tab_fr = st.tabs(["Story ES", "Story EN", "Story FR"])
    story = result.get("storytelling", {})
    with story_tab_es:
        st.code(story.get("es", ""), language=None)
    with story_tab_en:
        st.code(story.get("en", ""), language=None)
    with story_tab_fr:
        st.code(story.get("fr", ""), language=None)

    # Hashtags
    hashtags = result.get("hashtags", [])
    if hashtags:
        st.subheader("Hashtags")
        hashtag_str = " ".join(f"#{h}" for h in hashtags)
        st.code(hashtag_str, language=None)
