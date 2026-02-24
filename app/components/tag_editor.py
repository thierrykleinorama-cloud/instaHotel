"""
Reusable tag editor form for correcting AI-generated tags.
"""
import json

import streamlit as st

from src.models import VALID_CATEGORIES, VALID_SEASONS
from src.services.media_queries import update_media_tags, log_tag_correction

# Known ambiance values from the Vision prompt
AMBIANCE_OPTIONS = [
    "lumineux", "chaleureux", "romantique", "moderne", "art_nouveau",
    "mediterraneen", "intime", "elegant", "naturel", "colore",
    "festif", "zen", "luxueux", "rustique", "contemporain",
]


def render_tag_editor(media: dict, key_prefix: str = "editor") -> bool:
    """
    Render an editable tag form for a media item.

    Returns True if corrections were saved.
    """
    saved = False

    with st.form(key=f"{key_prefix}_form"):
        st.subheader("Tag Editor")

        # Category
        categories = sorted(VALID_CATEGORIES)
        current_cat = media.get("category", "")
        cat_idx = categories.index(current_cat) if current_cat in categories else 0
        new_category = st.selectbox("Category", categories, index=cat_idx, key=f"{key_prefix}_cat")

        # Subcategory
        new_subcategory = st.text_input(
            "Subcategory", value=media.get("subcategory", ""), key=f"{key_prefix}_subcat"
        )

        # Ambiance (multi-select)
        current_ambiance = media.get("ambiance", []) or []
        # Include any existing values not in options
        all_ambiance = sorted(set(AMBIANCE_OPTIONS) | set(current_ambiance))
        new_ambiance = st.multiselect(
            "Ambiance", all_ambiance, default=current_ambiance, key=f"{key_prefix}_amb"
        )

        # Season (multi-select)
        season_options = sorted(VALID_SEASONS)
        current_season = media.get("season", []) or []
        new_season = st.multiselect(
            "Season", season_options, default=current_season, key=f"{key_prefix}_season"
        )

        # Elements (text area, comma-separated)
        current_elements = media.get("elements", []) or []
        elements_str = ", ".join(current_elements)
        new_elements_str = st.text_area(
            "Elements (comma-separated)", value=elements_str, key=f"{key_prefix}_elem"
        )
        new_elements = [e.strip() for e in new_elements_str.split(",") if e.strip()]

        # Quality slider
        current_quality = media.get("ig_quality", 5) or 5
        new_quality = st.slider(
            "IG Quality", 1, 10, current_quality, key=f"{key_prefix}_qual"
        )

        # Manual notes
        new_notes = st.text_area(
            "Manual Notes",
            value=media.get("manual_notes", "") or "",
            key=f"{key_prefix}_notes",
        )

        submitted = st.form_submit_button("Save Corrections", type="primary")

        if submitted:
            updates = {}
            corrections = []

            # Compare and track changes
            if new_category != media.get("category"):
                updates["category"] = new_category
                corrections.append(("category", media.get("category", ""), new_category))

            if new_subcategory != media.get("subcategory"):
                updates["subcategory"] = new_subcategory
                corrections.append(("subcategory", media.get("subcategory", ""), new_subcategory))

            if sorted(new_ambiance) != sorted(current_ambiance):
                updates["ambiance"] = new_ambiance
                corrections.append(("ambiance", json.dumps(current_ambiance), json.dumps(new_ambiance)))

            if sorted(new_season) != sorted(current_season):
                updates["season"] = new_season
                corrections.append(("season", json.dumps(current_season), json.dumps(new_season)))

            if sorted(new_elements) != sorted(current_elements):
                updates["elements"] = new_elements
                corrections.append(("elements", json.dumps(current_elements), json.dumps(new_elements)))

            if new_quality != current_quality:
                updates["ig_quality"] = new_quality
                corrections.append(("ig_quality", str(current_quality), str(new_quality)))

            # Manual notes are always saved (not a "correction")
            if new_notes != (media.get("manual_notes") or ""):
                updates["manual_notes"] = new_notes

            if updates:
                if update_media_tags(media["id"], updates):
                    # Log corrections (skip manual_notes — it's not an AI tag fix)
                    for field, old, new in corrections:
                        log_tag_correction(media["id"], field, old, new)
                    st.success(f"Saved {len(updates)} update(s), {len(corrections)} correction(s) logged.")
                    saved = True
            else:
                st.info("No changes detected.")

    return saved
