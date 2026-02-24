"""
View 5 — AI Lab
Test AI transformations on media: caption generation + image enhancement.
"""
import io
import os
import sys
import tempfile
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from PIL import Image

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
from src.utils import encode_image_bytes, get_aspect_ratio
from src.services.image_enhancer import (
    stability_upscale,
    stability_outpaint,
    replicate_upscale,
    compute_outpaint_padding,
    STABILITY_METHODS,
    TARGET_RATIOS,
)
from src.services.vision_analyzer import get_raw_response as vision_reanalyze


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

**Captions** — Generate Instagram captions in 3 languages with hashtags.
**Enhancement** — Upscale or outpaint images using Stability AI or Replicate, compare before/after quality.
""")


# ===================================================================
# Sidebar: shared media selection
# ===================================================================
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

# ===================================================================
# Top-level tabs
# ===================================================================
tab_captions, tab_enhancement = st.tabs(["Captions", "Enhancement"])

# ===================================================================
# TAB 1: Captions (existing functionality)
# ===================================================================
with tab_captions:
    # --- Editorial context in sidebar (only relevant for captions) ---
    with st.sidebar:
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


# ===================================================================
# TAB 2: Enhancement
# ===================================================================
with tab_enhancement:
    # --- Image metadata ---
    if media.get("drive_file_id"):
        try:
            raw_bytes = _download_raw(media["drive_file_id"])
            img = Image.open(io.BytesIO(raw_bytes))
            orig_w, orig_h = img.size
            aspect = get_aspect_ratio(raw_bytes)
            quality = media.get("ig_quality", "?")
            st.markdown(
                f"**Dimensions:** {orig_w} x {orig_h} &nbsp;|&nbsp; "
                f"**Aspect ratio:** {aspect} &nbsp;|&nbsp; "
                f"**Quality score:** {quality}/10"
            )
        except Exception as e:
            st.error(f"Could not load image: {e}")
            st.stop()
    else:
        st.warning("No Drive file linked to this media.")
        st.stop()

    st.divider()

    # --- Operation selector ---
    operation = st.radio("Operation", ["Upscale", "Outpaint"], horizontal=True, key="enh_op")

    if operation == "Upscale":
        backend = st.selectbox("Backend", ["Stability AI", "Replicate"], key="enh_backend")

        if backend == "Stability AI":
            method_options = {v["description"]: k for k, v in STABILITY_METHODS.items()}
            method_label = st.selectbox("Method", list(method_options.keys()), key="enh_stab_method")
            method = method_options[method_label]
        else:
            st.caption("Model: Real-ESRGAN 4x (~$0.01)")
            scale = st.selectbox("Scale", [2, 4], index=1, key="enh_rep_scale")

    elif operation == "Outpaint":
        target_ratio = st.selectbox("Target ratio", list(TARGET_RATIOS.keys()), key="enh_ratio")
        creativity = st.slider("Creativity", 0.1, 1.0, 0.5, 0.1, key="enh_creativity")

        # Padding preview
        padding = compute_outpaint_padding(orig_w, orig_h, target_ratio)
        if any(padding[k] > 0 for k in ("left", "right", "top", "bottom")):
            parts = []
            if padding["top"] > 0:
                parts.append(f"Top: {padding['top']}px")
            if padding["bottom"] > 0:
                parts.append(f"Bottom: {padding['bottom']}px")
            if padding["left"] > 0:
                parts.append(f"Left: {padding['left']}px")
            if padding["right"] > 0:
                parts.append(f"Right: {padding['right']}px")
            st.info(
                f"Padding: {', '.join(parts)} => "
                f"{padding['new_w']}x{padding['new_h']}"
            )
        else:
            st.success("Image already matches the target ratio.")

    st.divider()

    # --- Enhance button ---
    if st.button("Enhance", type="primary", use_container_width=True, key="enh_go"):
        with st.spinner("Enhancing image..."):
            try:
                if operation == "Upscale":
                    if backend == "Stability AI":
                        enh_result = stability_upscale(raw_bytes, method=method)
                    else:
                        enh_result = replicate_upscale(raw_bytes, scale=scale)
                else:
                    enh_result = stability_outpaint(
                        raw_bytes,
                        target_ratio=target_ratio,
                        creativity=creativity,
                    )

                # Save enhanced image to temp file (too large for session state)
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                tmp.write(enh_result["image_bytes"])
                tmp.close()
                st.session_state["enh_result"] = {
                    "tmp_path": tmp.name,
                    "width": enh_result["width"],
                    "height": enh_result["height"],
                    "_cost": enh_result["_cost"],
                }

                # Track session cost
                if "enh_session_costs" not in st.session_state:
                    st.session_state["enh_session_costs"] = []
                st.session_state["enh_session_costs"].append(enh_result["_cost"])

            except Exception as e:
                import traceback
                st.error(f"Enhancement failed: {e}")
                st.code(traceback.format_exc())

    # --- Display results ---
    enh_meta = st.session_state.get("enh_result")
    if enh_meta and os.path.exists(enh_meta.get("tmp_path", "")):
        enhanced_bytes = Path(enh_meta["tmp_path"]).read_bytes()

        st.subheader("Before / After")
        col_before, col_after = st.columns(2)
        with col_before:
            st.image(raw_bytes, caption=f"Original ({orig_w}x{orig_h})", use_container_width=True)
        with col_after:
            st.image(
                enhanced_bytes,
                caption=f"Enhanced ({enh_meta['width']}x{enh_meta['height']})",
                use_container_width=True,
            )

        st.divider()

        # --- Re-analyze + Download ---
        col_reanalyze, col_download = st.columns(2)

        with col_download:
            st.download_button(
                "Download Enhanced Image",
                data=enhanced_bytes,
                file_name=f"enhanced_{media.get('file_name', 'image')}.png",
                mime="image/png",
                use_container_width=True,
            )

        with col_reanalyze:
            if st.button("Re-analyze with Claude Vision", use_container_width=True, key="enh_reanalyze"):
                with st.spinner("Re-analyzing enhanced image..."):
                    try:
                        enhanced_b64 = encode_image_bytes(enhanced_bytes)
                        vision_result = vision_reanalyze(enhanced_b64, media_type="image/jpeg")
                        st.session_state["enh_vision_result"] = vision_result
                    except Exception as e:
                        st.error(f"Re-analysis failed: {e}")

        # --- Quality comparison ---
        vision_result = st.session_state.get("enh_vision_result")
        if vision_result:
            parsed = vision_result.get("parsed", {})
            new_quality = parsed.get("ig_quality", "?")
            old_quality = media.get("ig_quality", "?")

            st.divider()
            st.subheader("Quality Comparison")

            if isinstance(old_quality, (int, float)) and isinstance(new_quality, (int, float)):
                delta = new_quality - old_quality
                sign = "+" if delta > 0 else ""
                col_q1, col_q2, col_q3 = st.columns(3)
                col_q1.metric("Original", f"{old_quality}/10")
                col_q2.metric("Enhanced", f"{new_quality}/10", delta=f"{sign}{delta}")
                col_q3.metric("Tokens", f"{vision_result.get('usage', {}).get('input_tokens', 0):,} in")
            else:
                st.write(f"Original: {old_quality}/10 | Enhanced: {new_quality}/10")

            with st.expander("Full re-analysis JSON"):
                st.json(parsed)

        # --- Session cost summary ---
        costs = st.session_state.get("enh_session_costs", [])
        if costs:
            st.divider()
            total = sum(c["cost_usd"] for c in costs)
            ops = len(costs)
            st.caption(f"Session: {ops} operation{'s' if ops != 1 else ''}, ${total:.3f} total")
