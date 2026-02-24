"""
View 5 — AI Lab Hub
Navigate to AI transformation tools: Captions and Enhancement.
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

# --- Method cards ---
col_cap, col_enh = st.columns(2)

with col_cap:
    st.markdown("""
### Captions

Generate Instagram captions in **ES / EN / FR** with hashtags.
Choose from multiple AI models, control editorial context
(theme, season, CTA), and optionally include the image
for richer results.
""")
    st.page_link("pages/6_AI_Captions.py", label="Open Captions", icon=":material/edit_note:")

with col_enh:
    st.markdown("""
### Enhancement

**Upscale**, **AI retouch**, or **outpaint** your photos
for better quality. Compare before/after with Claude Vision
re-analysis and download enhanced images.
""")
    st.page_link("pages/7_AI_Enhancement.py", label="Open Enhancement", icon=":material/auto_awesome:")
