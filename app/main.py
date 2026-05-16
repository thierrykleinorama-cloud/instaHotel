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
    page_title="InstaHotel — Content Studio",
    page_icon="🏨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Auth gate (Supabase: Google OAuth + email/password) ---
from src.auth import check_auth, handle_oauth_callback, login_form, logout

handle_oauth_callback()
if not check_auth():
    # Render login inside st.navigation so Streamlit's file-based pages/
    # auto-discovery doesn't leak the full nav into the sidebar.
    def _login_page():
        login_form("InstaHotel")
    st.navigation([st.Page(_login_page, title="Sign in", icon=":material/lock:")]).run()
    st.stop()

# --- Page definitions with sections ---
home = st.Page("pages/0_Home.py", title="Home", icon=":material/home:", default=True)

pg = st.navigation(
    {
        "": [home],
        "Create": [
            st.Page("pages/generate.py", title="Batch Generate", icon=":material/auto_fix_high:"),
            st.Page("pages/6_Instagram_Preview.py", title="Image Post", icon=":material/edit_note:"),
            st.Page("pages/8_Photo_to_Video.py", title="Reel", icon=":material/movie_creation:"),
            st.Page("pages/13_Carousel_Builder.py", title="Carousel", icon=":material/view_carousel:"),
            st.Page("pages/7_AI_Photo_Enhancement.py", title="Enhance Photo", icon=":material/auto_awesome:"),
        ],
        "Review": [
            st.Page("pages/review.py", title="Review Posts", icon=":material/rate_review:"),
        ],
        "Publish": [
            st.Page("pages/publish.py", title="Ready to Publish", icon=":material/publish:"),
        ],
        "Media Library": [
            st.Page("pages/1_Stats.py", title="Stats", icon=":material/bar_chart:"),
            st.Page("pages/2_Gallery.py", title="Gallery", icon=":material/photo_library:"),
            st.Page("pages/5_Upload_Media.py", title="Upload Media", icon=":material/upload:"),
            st.Page("pages/3_Image_Details.py", title="Image Details", icon=":material/image:"),
            st.Page("pages/4_Video_Details.py", title="Video Details", icon=":material/videocam:"),
        ],
        "Tools": [
            st.Page("pages/api_status.py", title="API Status", icon=":material/key:"),
            st.Page("pages/10_Rules.py", title="Content Strategy", icon=":material/tune:"),
            st.Page("pages/14_Cost_Dashboard.py", title="Cost Dashboard", icon=":material/payments:"),
            st.Page("pages/15_Prompt_Viewer.py", title="Prompts", icon=":material/description:"),
        ],
    }
)

with st.sidebar:
    st.caption(f"Logged in as {st.session_state.get('auth_user_email', '')}")
    if st.button(":material/logout: Logout", use_container_width=True):
        logout()

pg.run()
