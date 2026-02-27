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
from src.prompts.tone_variants import TONES, TONE_LABELS, TONE_LABELS_REVERSE
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

    st.divider()
    st.subheader("Tone")
    tone_label = st.selectbox(
        "Caption Tone",
        list(TONE_LABELS.values()),
        key="cap_tone",
        help="Changes the writing style of generated captions",
    )
    tone_key = TONE_LABELS_REVERSE[tone_label]
    tone_info = TONES[tone_key]
    st.caption(tone_info["description"])

    st.divider()
    include_image = st.checkbox(
        "Include image in prompt",
        value=False,
        help="OFF: metadata only. ON: sends image for richer captions.",
        key="cap_include_img",
    )

# --- Model selection ---
model_labels = {v["label"]: k for k, v in AVAILABLE_MODELS.items()}
default_label = AVAILABLE_MODELS[DEFAULT_MODEL]["label"]
selected_model_label = st.selectbox(
    "Model",
    list(model_labels.keys()),
    index=list(model_labels.keys()).index(default_label),
    key="cap_model",
    help="Choose AI model: better models = higher quality but more expensive",
)
_sel_info = AVAILABLE_MODELS[model_labels[selected_model_label]]
st.caption(
    f"Input: {_sel_info['input_per_mtok']}/Mtok "
    f"| Output: {_sel_info['output_per_mtok']}/Mtok"
)
selected_model = model_labels[selected_model_label]

# --- Editable prompts ---
filled_prompt = build_prompt(media, theme, season, cta_type, tone=tone_key)

system_prompt = st.text_area(
    "System prompt",
    value=SYSTEM_PROMPT,
    height=100,
    key="cap_system_prompt",
    help="Editable per generation. Defines the AI's role and tone.",
)
user_prompt = st.text_area(
    "User prompt",
    value=filled_prompt,
    height=200,
    key="cap_user_prompt",
    help="Editable per generation. Auto-filled from media metadata + editorial context above.",
)
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
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                tone=tone_key,
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

    # Reel variant (only for video media)
    reel = result.get("reel", {})
    if media.get("media_type") == "video" and reel:
        reel_tab_es, reel_tab_en, reel_tab_fr = st.tabs(["Reel ES", "Reel EN", "Reel FR"])
        with reel_tab_es:
            st.text_area("reel_es", reel.get("es", ""), height=100, label_visibility="collapsed", key="cap_reel_es")
        with reel_tab_en:
            st.text_area("reel_en", reel.get("en", ""), height=100, label_visibility="collapsed", key="cap_reel_en")
        with reel_tab_fr:
            st.text_area("reel_fr", reel.get("fr", ""), height=100, label_visibility="collapsed", key="cap_reel_fr")

    # Hashtags
    hashtags = result.get("hashtags", [])
    if hashtags:
        st.subheader("Hashtags")
        hashtag_str = " ".join(f"#{h}" for h in hashtags)
        st.text_area("hashtags", hashtag_str, height=80, label_visibility="collapsed", key="cap_hashtags")
