"""
View 15 — Prompt Viewer (Editorial)
Browse all AI prompts used in the pipeline, with context about where they're used.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from app.components.ui import sidebar_css, page_title


sidebar_css()
page_title("Prompt Viewer", "All AI prompts used in the content pipeline")

# ---------------------------------------------------------------------------
# Registry of prompt files with metadata
# ---------------------------------------------------------------------------
PROMPT_FILES = [
    {
        "file": "src/prompts/caption_generation.py",
        "title": "Caption Generation",
        "description": "System + user prompts for generating multilingual Instagram captions (ES/EN/FR). "
                       "Used by `src/services/caption_generator.py` when generating captions from the Captions page.",
        "used_by": ["app/pages/6_Instagram_Preview.py", "src/services/caption_generator.py"],
    },
    {
        "file": "src/prompts/destination_content.py",
        "title": "Destination Content",
        "description": "Prompts for destination-focused captions about Sitges and surroundings. "
                       "Used when editorial focus is set to 'destination' in the calendar.",
        "used_by": ["src/services/caption_generator.py", "src/services/content_generator.py"],
    },
    {
        "file": "src/prompts/carousel_prompts.py",
        "title": "Carousel AI",
        "description": "3 prompt sets: (1) Theme suggestion from media library stats, "
                       "(2) Image selection + ordering for a theme, (3) Multilingual carousel caption generation.",
        "used_by": ["src/services/carousel_ai.py", "app/pages/13_Carousel_Builder.py"],
    },
    {
        "file": "src/prompts/creative_transform.py",
        "title": "Creative Transforms",
        "description": "Prompts for generating video scenarios from hotel photos. "
                       "Includes realism constraints (banned words) and scenario templates. "
                       "Used by Photo-to-Video page for Kling/Veo video generation.",
        "used_by": ["src/services/creative_transform.py", "app/pages/8_Photo_to_Video.py"],
    },
    {
        "file": "src/prompts/enhancement.py",
        "title": "Image Enhancement",
        "description": "Prompts for Claude Vision to analyze image quality and suggest enhancements. "
                       "Used by the AI Photo Enhancement page.",
        "used_by": ["src/services/image_enhancer.py", "app/pages/7_AI_Photo_Enhancement.py"],
    },
    {
        "file": "src/prompts/music_generation.py",
        "title": "Music Generation",
        "description": "Mappings from hotel ambiance/category/mood to music style descriptions. "
                       "Builds text prompts for MusicGen (Replicate). "
                       "Used by Photo-to-Video music tab and Carousel reel export.",
        "used_by": ["src/services/music_generator.py", "app/pages/8_Photo_to_Video.py"],
    },
    {
        "file": "src/prompts/tone_variants.py",
        "title": "Tone Variants",
        "description": "5 caption tone definitions (Warm, Playful, Luxurious, Adventurous, Poetic) "
                       "with example style guides. Used to steer caption personality.",
        "used_by": ["src/services/caption_generator.py"],
    },
]


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
st.markdown(f"**{len(PROMPT_FILES)} prompt files** in `src/prompts/`")

for entry in PROMPT_FILES:
    filepath = Path(_root) / entry["file"]

    with st.expander(f"**{entry['title']}** — `{entry['file']}`", expanded=False):
        st.markdown(entry["description"])

        # Show which files use this prompt
        st.markdown("**Used by:**")
        for ub in entry["used_by"]:
            st.markdown(f"- `{ub}`")

        st.divider()

        # Show the actual prompt file content
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            st.code(content, language="python", line_numbers=True)
        else:
            st.warning(f"File not found: {filepath}")
