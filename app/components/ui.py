"""
Shared UI helpers — CSS, page title, common widgets.
"""
import streamlit as st


def sidebar_css():
    """Inject custom CSS for cleaner sidebar and thumbnails."""
    st.markdown(
        """
        <style>
        /* Tighter sidebar padding */
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1rem;
        }
        /* Thumbnail grid */
        .thumb-container {
            position: relative;
            border-radius: 8px;
            overflow: hidden;
            aspect-ratio: 1;
            background: #1e1e1e;
        }
        .thumb-container img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .thumb-badge {
            position: absolute;
            bottom: 4px;
            left: 4px;
            background: rgba(0,0,0,0.7);
            color: white;
            font-size: 11px;
            padding: 2px 6px;
            border-radius: 4px;
        }
        .thumb-quality {
            position: absolute;
            top: 4px;
            right: 4px;
            background: rgba(0,0,0,0.7);
            color: #4ade80;
            font-size: 12px;
            font-weight: bold;
            padding: 2px 6px;
            border-radius: 4px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_title(icon_text: str, title: str):
    """Render a consistent page title."""
    st.markdown(f"## {icon_text}")
    st.caption(title)
