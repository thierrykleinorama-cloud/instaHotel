"""
View 1 — Stats & Gaps
Overview metrics, distribution charts, and content gap alerts.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
import pandas as pd

from app.components.ui import sidebar_css, page_title
from src.services.media_queries import fetch_all_media

sidebar_css()
page_title("Stats & Gaps", "Media library overview and content gap analysis")

# Load data
all_media = fetch_all_media()
if not all_media:
    st.warning("No analyzed media found in database.")
    st.stop()

df = pd.DataFrame(all_media)

# --- Top metrics ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Media", len(df))
col2.metric("Images", len(df[df["media_type"] == "image"]))
col3.metric("Videos", len(df[df["media_type"] == "video"]))
avg_quality = df["ig_quality"].mean()
col4.metric("Avg Quality", f"{avg_quality:.1f}" if pd.notna(avg_quality) else "N/A")

st.divider()

# --- Distribution by category ---
left, right = st.columns(2)

with left:
    st.subheader("Distribution by Category")
    cat_counts = df["category"].value_counts().sort_values(ascending=True)
    st.bar_chart(cat_counts, horizontal=True)

with right:
    st.subheader("Distribution by Season")
    # Explode season arrays
    seasons = df.explode("season")
    season_counts = seasons["season"].value_counts().sort_values(ascending=True)
    st.bar_chart(season_counts, horizontal=True)

st.divider()

# --- Avg quality per category ---
st.subheader("Average Quality by Category")
quality_by_cat = (
    df.groupby("category")["ig_quality"]
    .agg(["mean", "min", "max", "count"])
    .round(1)
    .sort_values("mean", ascending=False)
)
quality_by_cat.columns = ["Avg Quality", "Min", "Max", "Count"]
st.dataframe(quality_by_cat, use_container_width=True)

st.divider()

# --- Gap alerts ---
st.subheader("Gap Alerts")

MIN_PER_CATEGORY = 15
MIN_QUALITY = 5

gaps_found = False

# Categories with too few items
for cat, count in cat_counts.items():
    if count < MIN_PER_CATEGORY:
        st.warning(f"**{cat}**: only {count} media — recommended minimum: {MIN_PER_CATEGORY}")
        gaps_found = True

# Seasons with no photos for any category
all_seasons = {"printemps", "ete", "automne", "hiver"}
for cat in df["category"].unique():
    cat_df = df[df["category"] == cat]
    cat_seasons = set()
    for s_list in cat_df["season"].dropna():
        if isinstance(s_list, list):
            cat_seasons.update(s_list)
    missing = all_seasons - cat_seasons - {"toute_saison"}
    for ms in missing:
        st.warning(f"**{cat}**: no photos tagged for season '{ms}'")
        gaps_found = True

# Low quality media count
low_quality = df[df["ig_quality"] < MIN_QUALITY]
if len(low_quality) > 0:
    st.warning(f"**{len(low_quality)} media** with quality score < {MIN_QUALITY} — consider archiving or re-shooting")
    gaps_found = True

if not gaps_found:
    st.success("No content gaps detected!")
