"""
View 5 — AI Lab
Test AI transformations on media. Currently: Instagram caption generation.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.ui import sidebar_css, page_title
from src.services.media_queries import fetch_all_media, fetch_media_by_id, fetch_distinct_values
from src.services.caption_generator import (
    generate_captions,
    build_prompt,
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
)
from src.prompts.caption_generation import SYSTEM_PROMPT
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
**AI Lab** lets you test AI transformations on your media library.

**Caption Generation** (current method):
1. **Select a photo** using the sidebar filters
2. **Set editorial context** — theme, season, call-to-action
3. **Review the prompt** — see exactly what will be sent to the AI
4. **Choose the model** — trade off quality vs. cost
5. **Generate** — get 2 caption variants x 3 languages + hashtags
6. **Check cost** — see token usage and cost after generation

More AI methods will be added here (quality enhancement, photo-to-video, etc.)
""")


# --- Media selection ---
with st.sidebar:
    st.subheader("Find Media")

    categories = fetch_distinct_values("category")
    selected_cats = st.multiselect("Category", categories, key="lab_cat")

    subcategories = fetch_distinct_values("subcategory")
    selected_subcats = st.multiselect("Subcategory", subcategories, key="lab_subcat")

    ambiances = fetch_distinct_values("ambiance")
    selected_ambiances = st.multiselect("Ambiance", ambiances, key="lab_amb")

    seasons_filter = fetch_distinct_values("season")
    selected_seasons = st.multiselect("Season filter", seasons_filter, key="lab_season_filter")

    min_quality = st.slider("Min quality", 1, 10, 1, key="lab_qual")

    search = st.text_input("Search filename", key="lab_search")
    elements_search = st.text_input("Search elements", key="lab_elem_search",
                                     help="e.g. piscine, vue_mer, terrasse")

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
    all_media = [m for m in all_media if (m.get("ig_quality") or 0) >= min_quality]
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
        selected_name = st.selectbox("Select", list(media_options.keys()), key="lab_select")
        media_id = media_options[selected_name]
    else:
        st.warning("No images match the current filters.")
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
        help="OFF: metadata only. ON: sends image for richer captions.",
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

# --- Model selection ---
model_labels = {v["label"]: k for k, v in AVAILABLE_MODELS.items()}
model_details = {
    v["label"]: f"Input: ${v['input_per_mtok']}/Mtok | Output: ${v['output_per_mtok']}/Mtok"
    for v in AVAILABLE_MODELS.values()
}
default_label = AVAILABLE_MODELS[DEFAULT_MODEL]["label"]
selected_model_label = st.selectbox(
    "Model",
    list(model_labels.keys()),
    index=list(model_labels.keys()).index(default_label),
    key="lab_model",
    help="Choose AI model: better models = higher quality but more expensive",
)
st.caption(model_details[selected_model_label])
selected_model = model_labels[selected_model_label]

# --- Show prompt ---
filled_prompt = build_prompt(media, theme, season, cta_type)

with st.expander("View prompt", expanded=False):
    st.markdown("**System prompt:**")
    st.code(SYSTEM_PROMPT, language=None)
    st.markdown("**User prompt:**")
    st.code(filled_prompt, language=None)
    if include_image:
        st.caption("+ image will be attached to the request")

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
                model=selected_model,
            )
            st.session_state["lab_result"] = result
        except Exception as e:
            st.error(f"Generation failed: {e}")

# --- Display results ---
result = st.session_state.get("lab_result")
if result:
    # Cost & usage info
    usage = result.get("_usage", {})
    if usage:
        st.caption(
            f"Model: {usage.get('model_label', '?')} | "
            f"Tokens: {usage.get('input_tokens', 0):,} in / {usage.get('output_tokens', 0):,} out | "
            f"Cost: ${usage.get('cost_usd', 0):.4f}"
        )

    st.subheader("Generated Captions")

    # Short variant
    short_tab_es, short_tab_en, short_tab_fr = st.tabs(["Short ES", "Short EN", "Short FR"])
    short = result.get("short", {})
    with short_tab_es:
        st.text_area("short_es", short.get("es", ""), height=100, label_visibility="collapsed", key="lab_short_es")
    with short_tab_en:
        st.text_area("short_en", short.get("en", ""), height=100, label_visibility="collapsed", key="lab_short_en")
    with short_tab_fr:
        st.text_area("short_fr", short.get("fr", ""), height=100, label_visibility="collapsed", key="lab_short_fr")

    # Storytelling variant
    story_tab_es, story_tab_en, story_tab_fr = st.tabs(["Story ES", "Story EN", "Story FR"])
    story = result.get("storytelling", {})
    with story_tab_es:
        st.text_area("story_es", story.get("es", ""), height=220, label_visibility="collapsed", key="lab_story_es")
    with story_tab_en:
        st.text_area("story_en", story.get("en", ""), height=220, label_visibility="collapsed", key="lab_story_en")
    with story_tab_fr:
        st.text_area("story_fr", story.get("fr", ""), height=220, label_visibility="collapsed", key="lab_story_fr")

    # Hashtags
    hashtags = result.get("hashtags", [])
    if hashtags:
        st.subheader("Hashtags")
        hashtag_str = " ".join(f"#{h}" for h in hashtags)
        st.text_area("hashtags", hashtag_str, height=80, label_visibility="collapsed", key="lab_hashtags")
