"""
View 5b — AI Enhancement
Upscale, AI retouch, or outpaint photos for better quality.
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
from app.components.media_selector import render_media_selector
from src.utils import encode_image_bytes, get_aspect_ratio
from src.services.image_enhancer import (
    stability_upscale,
    stability_outpaint,
    replicate_upscale,
    replicate_retouch,
    compute_outpaint_padding,
    STABILITY_METHODS,
    TARGET_RATIOS,
    RETOUCH_RESOLUTIONS,
    RETOUCH_COSTS,
)
from src.prompts.enhancement import (
    UPSCALE_PROMPT,
    RETOUCH_PROMPT,
)
from src.services.vision_analyzer import get_raw_response as vision_reanalyze


sidebar_css()
page_title("AI Enhancement", "Upscale, retouch, or outpaint your photos")

st.page_link("pages/5_AI_Lab.py", label="Back to AI Lab", icon=":material/arrow_back:")

# --- Shared media selector ---
media, raw_bytes = render_media_selector("enh")

# --- Image metadata ---
img = Image.open(io.BytesIO(raw_bytes))
orig_w, orig_h = img.size
aspect = get_aspect_ratio(raw_bytes)
quality = media.get("ig_quality", "?")
st.markdown(
    f"**Dimensions:** {orig_w} x {orig_h} &nbsp;|&nbsp; "
    f"**Aspect ratio:** {aspect} &nbsp;|&nbsp; "
    f"**Quality score:** {quality}/10"
)

st.divider()

# --- Operation selector ---
operation = st.radio(
    "Operation", ["Upscale", "AI Retouch", "Outpaint"], horizontal=True, key="enh_op"
)

if operation == "Upscale":
    st.info(
        "**Increase resolution** with AI super-resolution. "
        "Adds realistic detail instead of just stretching pixels. "
        "Best for: making small images sharper for full-screen display."
    )
    backend = st.selectbox("Backend", ["Stability AI", "Replicate"], key="enh_backend")

    if backend == "Stability AI":
        st.caption(
            "Fast \\$0.02 / Conservative \\$0.40 / Creative \\$0.60 "
            "— [buy credits](https://platform.stability.ai/account/credits)"
        )
        method_options = {v["description"]: k for k, v in STABILITY_METHODS.items()}
        method_label = st.selectbox("Method", list(method_options.keys()), key="enh_stab_method")
        method = method_options[method_label]

        if method in ("conservative", "creative"):
            upscale_prompt = st.text_area(
                "Upscale prompt",
                value=UPSCALE_PROMPT,
                height=80,
                key="enh_upscale_prompt",
                help="Describe the image content to guide the upscaler. Editable per generation.",
            )
        if method == "conservative":
            upscale_creativity = st.slider(
                "Creativity", 0.1, 0.5, 0.35, 0.05, key="enh_upscale_creativity",
                help="Higher = more detail added. Default 0.35.",
            )
    else:
        scale_options = {
            "2x — double resolution (~$0.006)": 2,
            "4x — quadruple resolution (~$0.012)": 4,
        }
        scale_label = st.selectbox("Scale", list(scale_options.keys()), index=1, key="enh_rep_scale")
        scale = scale_options[scale_label]
        st.caption(
            f"Real-ESRGAN: {orig_w}x{orig_h} → ~{orig_w * scale}x{orig_h * scale} "
            f"(output may be slightly smaller if input is downscaled for GPU)"
        )

elif operation == "AI Retouch":
    st.info(
        "**AI reimagines the photo** with better lighting, colors, and clarity "
        "using **Nano Banana Pro** (via Replicate). You control the prompt below. "
        "The scene stays the same — only visual quality improves. "
        "Best for: fixing poor lighting, dull colors, or flat atmosphere."
    )
    retouch_resolution = st.selectbox(
        "Resolution",
        RETOUCH_RESOLUTIONS,
        index=1,
        key="enh_retouch_res",
        help="1K/2K = $0.15, 4K = $0.30",
    )
    retouch_prompt = st.text_area(
        "Retouch prompt",
        value=RETOUCH_PROMPT,
        height=120,
        key="enh_retouch_prompt",
        help="Editable per generation. Describe what to improve. Keep 'same scene/composition' to avoid hallucinations.",
    )

elif operation == "Outpaint":
    st.info(
        "**Extend the image** beyond its borders with AI-generated content. "
        "Converts landscape (16:9) to portrait (4:5) for Instagram by generating "
        "new pixels at top/bottom — no cropping needed. "
        "Best for: adapting photos to Instagram's preferred aspect ratios. "
        "Cost: \\$0.04 — [buy credits](https://platform.stability.ai/account/credits)"
    )
    target_ratio = st.selectbox("Target ratio", list(TARGET_RATIOS.keys()), key="enh_ratio")
    creativity = st.slider("Creativity", 0.1, 1.0, 0.5, 0.1, key="enh_creativity")

    # Output size preview
    padding = compute_outpaint_padding(orig_w, orig_h, target_ratio)
    if any(padding[k] > 0 for k in ("left", "right", "top", "bottom")):
        st.caption(
            f"Output: {orig_w}x{orig_h} → **{padding['new_w']}x{padding['new_h']}** ({target_ratio})"
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
                    kwargs = {"method": method}
                    if method in ("conservative", "creative"):
                        kwargs["prompt"] = upscale_prompt
                    if method == "conservative":
                        kwargs["creativity"] = upscale_creativity
                    enh_result = stability_upscale(raw_bytes, **kwargs)
                else:
                    enh_result = replicate_upscale(raw_bytes, scale=scale)
            elif operation == "AI Retouch":
                enh_result = replicate_retouch(
                    raw_bytes,
                    prompt=retouch_prompt,
                    resolution=retouch_resolution,
                )
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
