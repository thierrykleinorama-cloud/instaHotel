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

# Page config
st.set_page_config(
    page_title="InstaHotel — Media Explorer",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Page definitions with sections ---
home = st.Page("pages/0_Home.py", title="Home", icon=":material/home:", default=True)

pg = st.navigation(
    {
        "": [home],
        "Media Library": [
            st.Page("pages/1_Stats.py", title="Stats", icon=":material/bar_chart:"),
            st.Page("pages/2_Gallery.py", title="Gallery", icon=":material/photo_library:"),
            st.Page("pages/3_Image_Details.py", title="Image Details", icon=":material/image:"),
            st.Page("pages/4_Video_Details.py", title="Video Details", icon=":material/videocam:"),
        ],
        "AI Lab": [
            st.Page("pages/6_Instagram_Preview.py", title="Captions", icon=":material/edit_note:"),
            st.Page("pages/7_AI_Photo_Enhancement.py", title="Enhancement", icon=":material/auto_awesome:"),
            st.Page("pages/8_Photo_to_Video.py", title="Photo to Video", icon=":material/movie_creation:"),
            st.Page("pages/12_Veo_Video.py", title="Veo 3 Video", icon=":material/slow_motion_video:"),
            st.Page("pages/13_Carousel_Builder.py", title="Carousel", icon=":material/view_carousel:"),
        ],
        "Production": [
            st.Page("pages/16_Batch_Creative.py", title="Production Pipeline", icon=":material/auto_fix_high:"),
            st.Page("pages/14_Cost_Dashboard.py", title="Cost Dashboard", icon=":material/payments:"),
        ],
        "Editorial": [
            st.Page("pages/9_Calendar.py", title="Calendar", icon=":material/calendar_month:"),
            st.Page("pages/10_Rules.py", title="Rules", icon=":material/tune:"),
            st.Page("pages/11_Drafts_Review.py", title="Content Drafts", icon=":material/rate_review:"),
            st.Page("pages/15_Prompt_Viewer.py", title="Prompts", icon=":material/description:"),
        ],
    }
)

pg.run()
