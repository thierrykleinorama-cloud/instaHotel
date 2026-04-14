"""
InstaHotel V2 — Batch Generate
Generate multiple posts at once using the content recipe from editorial rules.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.ui import sidebar_css, page_title
from src.services.batch_generator import (
    get_content_recipe,
    scale_recipe,
    estimate_batch_cost,
    generate_batch,
)
from src.services.editorial_engine import get_current_season
from src.services.caption_generator import AVAILABLE_MODELS, DEFAULT_MODEL
from src.prompts.tone_variants import TONE_LABELS, TONE_LABELS_REVERSE
from datetime import date

sidebar_css()
page_title("Batch Generate", "Generate multiple posts at once")

# -------------------------------------------------------
# Session state defaults
# -------------------------------------------------------
for _k, _v in [
    ("bg_running", False),
    ("bg_last_result", None),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# -------------------------------------------------------
# Content recipe
# -------------------------------------------------------
recipe = get_content_recipe()

if not recipe:
    st.warning("No content rules found. Go to **Content Strategy** to configure your weekly posting mix.")
    st.stop()

# Show current recipe summary
TYPE_LABELS = {
    "feed": "Image Post",
    "carousel": "Carousel",
    "reel-kling": "Reel (Kling)",
    "reel-veo": "Reel (Veo)",
    "reel-slideshow": "Slideshow",
}

# Count by type
recipe_summary = {}
for item in recipe:
    pt = item["post_type"]
    label = TYPE_LABELS.get(pt, pt)
    recipe_summary[label] = recipe_summary.get(label, 0) + 1

st.markdown("### Content Recipe")
st.caption("Based on your Content Strategy rules. Adjust the count to scale.")

recipe_cols = st.columns(len(recipe_summary))
for i, (label, count) in enumerate(recipe_summary.items()):
    with recipe_cols[i]:
        st.metric(label, f"{count}/week")

st.divider()

# -------------------------------------------------------
# Settings
# -------------------------------------------------------
st.markdown("### Settings")

col1, col2 = st.columns(2)

with col1:
    post_count = st.slider(
        "Number of posts",
        min_value=1,
        max_value=20,
        value=len(recipe),
        help=f"Default = {len(recipe)} (one week from your content recipe)",
    )

    season_options = ["auto", "printemps", "ete", "automne", "hiver"]
    season_sel = st.selectbox("Season", season_options, key="bg_season")
    season = get_current_season(date.today()) if season_sel == "auto" else season_sel

with col2:
    tone_label = st.selectbox(
        "Tone",
        list(TONE_LABELS.values()),
        key="bg_tone",
    )
    tone_key = TONE_LABELS_REVERSE[tone_label]

    min_quality = st.slider("Min quality", 1, 10, 6, key="bg_min_quality")

model_labels = {v["label"]: k for k, v in AVAILABLE_MODELS.items()}
default_label = AVAILABLE_MODELS[DEFAULT_MODEL]["label"]
sel_model_label = st.selectbox(
    "AI Model (captions & scenarios)",
    list(model_labels.keys()),
    index=list(model_labels.keys()).index(default_label),
    key="bg_model",
)
selected_model = model_labels[sel_model_label]

st.divider()

# -------------------------------------------------------
# Cost estimate
# -------------------------------------------------------
scaled = scale_recipe(recipe, post_count)
estimate = estimate_batch_cost(recipe, post_count)

st.markdown("### Cost Estimate")
est_cols = st.columns(len(estimate["breakdown"]) + 1)
for i, item in enumerate(estimate["breakdown"]):
    with est_cols[i]:
        label = TYPE_LABELS.get(item["type"], item["type"])
        st.metric(label, f"{item['count']}x", f"~${item['subtotal']:.2f}")
with est_cols[-1]:
    st.metric("Total", f"~${estimate['total_usd']:.2f}")

if estimate["total_usd"] > 2.0:
    st.warning(f"This batch will cost approximately **${estimate['total_usd']:.2f}**. Reels are the most expensive items.")

st.divider()

# -------------------------------------------------------
# Generate
# -------------------------------------------------------
if st.session_state.get("bg_running"):
    st.info("Generation in progress...")
else:
    if st.button("Generate Batch", type="primary", use_container_width=True, key="bg_generate"):
        st.session_state["bg_running"] = True
        progress_bar = st.progress(0)
        status_text = st.empty()

        def _progress(current, total, message):
            if total > 0:
                progress_bar.progress(current / total)
            status_text.caption(message)

        try:
            result = generate_batch(
                count=post_count,
                recipe=scaled,
                season=season,
                tone=tone_key,
                min_quality=min_quality,
                model=selected_model,
                include_image=False,
                progress_cb=_progress,
            )
            st.session_state["bg_last_result"] = result
            st.session_state["bg_running"] = False
            progress_bar.progress(1.0)
            status_text.caption("Done!")
        except Exception as e:
            st.session_state["bg_running"] = False
            st.error(f"Batch generation failed: {e}")

# -------------------------------------------------------
# Results
# -------------------------------------------------------
last_result = st.session_state.get("bg_last_result")
if last_result:
    st.divider()
    st.markdown("### Results")
    st.success(f"Batch complete: {last_result['summary']}")

    for r in last_result["results"]:
        if r["status"] == "ok":
            st.caption(f"Post {r['post_id'][:8]}... created")
        else:
            st.warning(f"Error: {r.get('error', 'Unknown')}")

    st.markdown("Go to **[Review Posts](/Review%20Posts)** to approve or discard these posts.")
