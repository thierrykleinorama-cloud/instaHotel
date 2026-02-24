"""
InstaHotel — Media Library Explorer
Streamlit entry point.
"""
import sys
from pathlib import Path

# Ensure project root is on sys.path (for both src.* and app.* imports)
_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.ui import sidebar_css, page_title
from src.database import test_connection
from src.services.media_queries import fetch_all_media

# Page config
st.set_page_config(
    page_title="InstaHotel — Media Explorer",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

sidebar_css()

# Sidebar — DB status
with st.sidebar:
    st.title("InstaHotel")
    st.caption("Media Library Explorer")
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
page_title("Welcome", "Media Library Explorer")

st.markdown("""
Use the sidebar to navigate between views:

- **Stats** — Overview, distribution charts, gap alerts
- **Gallery** — Browse and filter all media
- **Image Details** — View full-size image and correct AI tags
- **Video Details** — Browse videos, view scenes, and correct tags
- **AI Lab** — Test AI transformations on your media
""")
