"""
View 5 — AI Lab Hub
Navigate to AI transformation tools.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.ui import sidebar_css, page_title

sidebar_css()
page_title("AI Lab", "Test AI transformations on your media")

with st.expander("How does this work?", expanded=False):
    st.markdown("""
**AI Lab** lets you test AI transformations on your media library.

Choose a tool below to get started. Each tool has its own media selector
so you can work on different images independently.
""")

# --- 4-Step Media Pipeline Overview ---
st.markdown("### Media Pipeline")

p1, p2, p3, p4 = st.columns(4)

with p1:
    st.markdown("**Step 1: Preprocess**")
    st.caption("Improve quality — replaces original")
    st.markdown(
        ":green[&check;] AI Retouch\n\n"
        ":green[&check;] Upscale\n\n"
        ":orange[&rarr;] Object removal"
    )

with p2:
    st.markdown("**Step 2: Creative Transform**")
    st.caption("Multiply library — new entries")
    st.markdown(
        ":green[&check;] Photo-to-video (Kling + Veo)\n\n"
        ":green[&check;] Creative scenarios\n\n"
        ":green[&check;] Background music\n\n"
        ":orange[&rarr;] Seasonal variants\n\n"
        ":orange[&rarr;] Add elements\n\n"
        ":orange[&rarr;] Avatar presenter"
    )

with p3:
    st.markdown("**Step 3: Retarget**")
    st.caption("Format adaptation — same media")
    st.markdown(
        ":green[&check;] Outpaint\n\n"
        ":orange[&rarr;] Story/Reel crop\n\n"
        ":orange[&rarr;] Platform adapt"
    )

with p4:
    st.markdown("**Step 4: Content Assembly**")
    st.caption("Captions + post packaging")
    st.markdown(
        ":green[&check;] AI Captions\n\n"
        ":green[&check;] Tone variants\n\n"
        ":green[&check;] Carousel\n\n"
        ":orange[&rarr;] AI Humor"
    )

st.divider()

# --- Method cards ---
col_cap, col_enh = st.columns(2)

with col_cap:
    st.markdown("""
### Instagram Preview

Generate Instagram captions in **ES / EN / FR** with hashtags.
Choose from multiple AI models, control editorial context
(theme, season, CTA), **tone variants** (luxe, casual, humorous, romantic),
and optionally include the image for richer results.
""")
    st.page_link("pages/6_Instagram_Preview.py", label="Open Instagram Preview", icon=":material/edit_note:")

with col_enh:
    st.markdown("""
### AI Photo Enhancement

**Upscale**, **AI retouch**, or **outpaint** your photos
for better quality. Compare before/after with Claude Vision
re-analysis and download enhanced images.
""")
    st.page_link("pages/7_AI_Photo_Enhancement.py", label="Open Photo Enhancement", icon=":material/auto_awesome:")

st.divider()

col_video, col_veo = st.columns(2)

with col_video:
    st.markdown("""
### Photo to Video

**Photo-to-video** (Kling v2.1 + Veo 3.1), **creative scenario generation**
with Claude, and **background music** (MusicGen). Three tabs in one workflow:
generate video, brainstorm scenarios, add music and merge into a final MP4.
""")
    st.page_link("pages/8_Photo_to_Video.py", label="Open Photo to Video", icon=":material/movie_creation:")

with col_veo:
    st.markdown("""
### Veo 3 Video

**Google Veo 3.1** — dedicated test page for Google's video generation model.
Higher visual quality, native audio, 4/6/8s durations. Fast and Standard variants.
""")
    st.page_link("pages/12_Veo_Video.py", label="Open Veo 3 Video", icon=":material/slow_motion_video:")

st.divider()

col_carousel = st.columns(1)[0]

with col_carousel:
    st.markdown("""
### Carousel Builder

Build **multi-image carousel** posts for Instagram. Select 2-10 images,
reorder, add multilingual captions and hashtags, preview with slide dots,
save drafts, and publish directly.
""")
    st.page_link("pages/13_Carousel_Builder.py", label="Open Carousel Builder", icon=":material/view_carousel:")
