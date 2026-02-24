"""
View 5a — AI Captions
Generate Instagram captions in ES/EN/FR with hashtags.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.ui import sidebar_css, page_title
from app.components.media_selector import render_media_selector
from src.services.caption_generator import (
    generate_captions,
    build_prompt,
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
)
from src.prompts.caption_generation import SYSTEM_PROMPT
from src.utils import encode_image_bytes


@st.cache_data(ttl=300)
def _download_and_encode(drive_file_id: str) -> str:
    """Download image from Drive and return base64. Cached 5 min."""
    from src.services.google_drive import download_file_bytes
    image_bytes = download_file_bytes(drive_file_id)
    return encode_image_bytes(image_bytes)


sidebar_css()
page_title("AI Captions", "Generate Instagram captions in 3 languages")

st.page_link("pages/5_AI_Lab.py", label="Back to AI Lab", icon=":material/arrow_back:")

# --- Shared media selector ---
media, image_bytes = render_media_selector("cap")

# --- Editorial context in sidebar ---
with st.sidebar:
    st.divider()
    st.subheader("Editorial Context")

    theme = st.selectbox(
        "Theme",
        ["chambre", "destination", "experience", "gastronomie", "offre"],
        key="cap_theme",
    )
    season = st.selectbox(
        "Season",
        ["printemps", "ete", "automne", "hiver", "toute_saison"],
        key="cap_season",
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
        key="cap_cta",
    )
    cta_type = CTA_OPTIONS[cta_label]

    include_image = st.checkbox(
        "Include image in prompt",
        value=False,
        help="OFF: metadata only. ON: sends image for richer captions.",
        key="cap_include_img",
    )

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
    key="cap_model",
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
            st.session_state["cap_result"] = result
        except Exception as e:
            st.error(f"Generation failed: {e}")

# --- Display results ---
result = st.session_state.get("cap_result")
if result:
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
        st.text_area("short_es", short.get("es", ""), height=100, label_visibility="collapsed", key="cap_short_es")
    with short_tab_en:
        st.text_area("short_en", short.get("en", ""), height=100, label_visibility="collapsed", key="cap_short_en")
    with short_tab_fr:
        st.text_area("short_fr", short.get("fr", ""), height=100, label_visibility="collapsed", key="cap_short_fr")

    # Storytelling variant
    story_tab_es, story_tab_en, story_tab_fr = st.tabs(["Story ES", "Story EN", "Story FR"])
    story = result.get("storytelling", {})
    with story_tab_es:
        st.text_area("story_es", story.get("es", ""), height=220, label_visibility="collapsed", key="cap_story_es")
    with story_tab_en:
        st.text_area("story_en", story.get("en", ""), height=220, label_visibility="collapsed", key="cap_story_en")
    with story_tab_fr:
        st.text_area("story_fr", story.get("fr", ""), height=220, label_visibility="collapsed", key="cap_story_fr")

    # Hashtags
    hashtags = result.get("hashtags", [])
    if hashtags:
        st.subheader("Hashtags")
        hashtag_str = " ".join(f"#{h}" for h in hashtags)
        st.text_area("hashtags", hashtag_str, height=80, label_visibility="collapsed", key="cap_hashtags")
