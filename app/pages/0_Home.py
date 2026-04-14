"""
Home — InstaHotel welcome page with DB status.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.ui import sidebar_css, page_title
from src.database import test_connection
from src.services.media_queries import fetch_all_media

sidebar_css()

# Sidebar — DB status
with st.sidebar:
    st.title("InstaHotel")
    st.caption("Instagram Content Studio")
    st.divider()

    if test_connection():
        all_media = fetch_all_media()
        images = [m for m in all_media if m["media_type"] == "image"]
        videos = [m for m in all_media if m["media_type"] == "video"]
        st.success(f"DB connected — {len(all_media)} media")
        col1, col2 = st.columns(2)
        col1.metric("Images", len(images))
        col2.metric("Videos", len(videos))
    else:
        st.error("Database connection failed")

    st.divider()
    st.caption("Navigate using pages in the sidebar above.")

# Main page
page_title("Welcome", "Instagram Content Studio")

st.markdown("""
### 3-step workflow

**1. Create** — Generate Instagram content from your media library
- **Batch Generate** — Create multiple posts at once using your content recipe
- **Image Post** — Pick a photo and generate captions (ES/EN/FR)
- **Reel** — Create video reels with scenarios, music, and compositing
- **Carousel** — Build multi-image carousel posts

**2. Review** — Approve or discard generated posts with feedback

**3. Publish** — Send approved posts to Instagram one by one

---

**Media Library** — Browse, filter, and inspect your 530+ hotel photos and videos

**Tools** — Content Strategy, Cost Dashboard, Prompt Viewer
""")
