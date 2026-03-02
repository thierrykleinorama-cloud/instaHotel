"""
InstaHotel — Editorial Rules & Seasonal Themes
Configure weekly posting schedule and seasonal editorial context.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from datetime import date

from app.components.ui import sidebar_css, page_title
from src.services.editorial_queries import (
    fetch_all_rules,
    upsert_rule,
    delete_rule,
    fetch_all_themes,
    upsert_theme,
    delete_theme,
)

sidebar_css()
page_title("Rules & Themes", "Configure editorial strategy")

CATEGORIES = ["chambre", "commun", "exterieur", "gastronomie", "experience"]
FORMATS = ["feed", "story", "reel"]
ASPECT_RATIOS = ["1:1", "4:5", "9:16", "16:9", "3:4"]
SEASONS = ["printemps", "ete", "automne", "hiver"]
DAY_NAMES = {1: "Monday", 2: "Tuesday", 3: "Wednesday", 4: "Thursday", 5: "Friday", 6: "Saturday", 7: "Sunday"}
AMBIANCE_OPTIONS = [
    "lumineux", "chaleureux", "romantique", "moderne", "art_nouveau",
    "mediterraneen", "intime", "elegant", "naturel", "colore",
    "festif", "zen", "luxueux", "rustique", "contemporain",
]

# -------------------------------------------------------
# Tabs
# -------------------------------------------------------
tab_rules, tab_themes = st.tabs(["Weekly Rules", "Seasonal Themes"])

# -------------------------------------------------------
# Tab 1: Weekly Rules
# -------------------------------------------------------
with tab_rules:
    rules = fetch_all_rules()

    st.markdown("### Weekly Posting Schedule")
    st.caption("One row per posting slot. Main daily posts (slot 1) + optional bonus slots (slot 2).")

    if not rules:
        st.info("No rules found. Run the Phase 2 SQL migration first.")
    else:
        for rule in rules:
            day_name = DAY_NAMES.get(rule["day_of_week"], "?")
            slot = rule["slot_index"]
            label = f"{day_name} — Slot {slot}"
            is_active = rule.get("is_active", True)
            icon = "" if is_active else " (inactive)"

            with st.expander(f"{label}{icon}", expanded=False):
                with st.form(key=f"rule_{rule['id']}"):
                    col1, col2, col3 = st.columns(3)

                    with col1:
                        cat_idx = CATEGORIES.index(rule["default_category"]) if rule.get("default_category") in CATEGORIES else 0
                        category = st.selectbox("Category", CATEGORIES, index=cat_idx, key=f"rcat_{rule['id']}")
                        time_val = st.text_input("Preferred Time", value=rule.get("preferred_time") or "10:00", key=f"rtime_{rule['id']}")

                    with col2:
                        fmt_idx = FORMATS.index(rule["preferred_format"]) if rule.get("preferred_format") in FORMATS else 0
                        fmt = st.selectbox("Format", FORMATS, index=fmt_idx, key=f"rfmt_{rule['id']}")
                        ar_idx = ASPECT_RATIOS.index(rule["preferred_aspect_ratio"]) if rule.get("preferred_aspect_ratio") in ASPECT_RATIOS else 0
                        aspect = st.selectbox("Aspect Ratio", ASPECT_RATIOS, index=ar_idx, key=f"rar_{rule['id']}")

                    with col3:
                        min_q = st.slider("Min Quality", 1, 10, value=rule.get("min_quality") or 6, key=f"rq_{rule['id']}")
                        active = st.checkbox("Active", value=is_active, key=f"ract_{rule['id']}")

                    notes = st.text_input("Notes", value=rule.get("notes") or "", key=f"rnotes_{rule['id']}")

                    col_save, col_del = st.columns([3, 1])
                    submitted = col_save.form_submit_button("Save", type="primary")
                    deleted = col_del.form_submit_button("Delete", type="secondary")

                    if submitted:
                        upsert_rule({
                            "id": rule["id"],
                            "day_of_week": rule["day_of_week"],
                            "slot_index": slot,
                            "default_category": category,
                            "preferred_time": time_val,
                            "preferred_format": fmt,
                            "preferred_aspect_ratio": aspect,
                            "min_quality": min_q,
                            "is_active": active,
                            "notes": notes,
                        })
                        st.success("Rule saved.")
                        st.rerun()

                    if deleted:
                        delete_rule(rule["id"])
                        st.success("Rule deleted.")
                        st.rerun()

    # Add new rule
    st.markdown("---")
    st.markdown("#### Add New Rule")
    with st.form("new_rule_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            new_dow = st.selectbox("Day", options=list(DAY_NAMES.keys()), format_func=lambda d: DAY_NAMES[d], key="new_dow")
            new_slot = st.number_input("Slot Index", min_value=1, max_value=3, value=1, key="new_slot")
        with c2:
            new_cat = st.selectbox("Category", CATEGORIES, key="new_cat")
            new_fmt = st.selectbox("Format", FORMATS, key="new_fmt")
        with c3:
            new_ar = st.selectbox("Aspect Ratio", ASPECT_RATIOS, key="new_ar")
            new_mq = st.slider("Min Quality", 1, 10, 6, key="new_mq")
        new_time = st.text_input("Time", value="10:00", key="new_time")
        new_notes = st.text_input("Notes", key="new_notes")

        if st.form_submit_button("Add Rule", type="primary"):
            upsert_rule({
                "day_of_week": new_dow,
                "slot_index": new_slot,
                "default_category": new_cat,
                "preferred_time": new_time,
                "preferred_format": new_fmt,
                "preferred_aspect_ratio": new_ar,
                "min_quality": new_mq,
                "is_active": True,
                "notes": new_notes,
            })
            st.success("New rule added.")
            st.rerun()


# -------------------------------------------------------
# Tab 2: Seasonal Themes
# -------------------------------------------------------
with tab_themes:
    themes = fetch_all_themes()

    st.markdown("### Seasonal Themes")
    st.caption("Define date ranges with editorial context. Higher priority wins on overlapping dates.")

    if not themes:
        st.info("No themes found. Run the Phase 2 SQL migration first.")
    else:
        for theme in themes:
            priority = theme.get("priority", 1)
            active = theme.get("is_active", True)
            icon = "" if active else " (inactive)"
            label = f"{theme['theme_name']} — {theme.get('start_date', '?')} → {theme.get('end_date', '?')}  [P{priority}]{icon}"

            with st.expander(label, expanded=False):
                with st.form(key=f"theme_{theme['id']}"):
                    name = st.text_input("Theme Name", value=theme["theme_name"], key=f"tname_{theme['id']}")

                    c1, c2, c3 = st.columns(3)
                    with c1:
                        start_d = st.date_input("Start Date", value=date.fromisoformat(str(theme["start_date"])), key=f"tstart_{theme['id']}")
                        end_d = st.date_input("End Date", value=date.fromisoformat(str(theme["end_date"])), key=f"tend_{theme['id']}")
                    with c2:
                        s_idx = SEASONS.index(theme["season"]) if theme.get("season") in SEASONS else 0
                        season = st.selectbox("Season", SEASONS, index=s_idx, key=f"tseas_{theme['id']}")
                        pri = st.number_input("Priority", min_value=1, max_value=100, value=priority, key=f"tpri_{theme['id']}")
                    with c3:
                        t_active = st.checkbox("Active", value=active, key=f"tact_{theme['id']}")
                        cta = st.text_input("CTA Focus", value=theme.get("cta_focus") or "", key=f"tcta_{theme['id']}")

                    ambiances = st.multiselect("Preferred Ambiances", AMBIANCE_OPTIONS, default=theme.get("preferred_ambiances") or [], key=f"tamb_{theme['id']}")
                    elements_str = st.text_input("Preferred Elements (comma-separated)", value=", ".join(theme.get("preferred_elements") or []), key=f"telem_{theme['id']}")
                    tone = st.text_input("Editorial Tone", value=theme.get("editorial_tone") or "", key=f"ttone_{theme['id']}")
                    hashtags_str = st.text_input("Hashtags (comma-separated)", value=", ".join(theme.get("hashtags") or []), key=f"thash_{theme['id']}")

                    col_save, col_del = st.columns([3, 1])
                    submitted = col_save.form_submit_button("Save", type="primary")
                    deleted = col_del.form_submit_button("Delete", type="secondary")

                    if submitted:
                        elements = [e.strip() for e in elements_str.split(",") if e.strip()]
                        hashtags = [h.strip() for h in hashtags_str.split(",") if h.strip()]
                        upsert_theme({
                            "id": theme["id"],
                            "theme_name": name,
                            "start_date": start_d.isoformat(),
                            "end_date": end_d.isoformat(),
                            "season": season,
                            "preferred_ambiances": ambiances,
                            "preferred_elements": elements,
                            "editorial_tone": tone,
                            "cta_focus": cta,
                            "hashtags": hashtags,
                            "priority": pri,
                            "is_active": t_active,
                        })
                        st.success("Theme saved.")
                        st.rerun()

                    if deleted:
                        delete_theme(theme["id"])
                        st.success("Theme deleted.")
                        st.rerun()

    # Add new theme
    st.markdown("---")
    st.markdown("#### Add New Theme")
    with st.form("new_theme_form"):
        new_name = st.text_input("Theme Name", key="nt_name")
        c1, c2, c3 = st.columns(3)
        with c1:
            nt_start = st.date_input("Start Date", key="nt_start")
            nt_end = st.date_input("End Date", key="nt_end")
        with c2:
            nt_season = st.selectbox("Season", SEASONS, key="nt_season")
            nt_pri = st.number_input("Priority", 1, 100, 1, key="nt_pri")
        with c3:
            nt_cta = st.text_input("CTA Focus", key="nt_cta")
        nt_ambiances = st.multiselect("Preferred Ambiances", AMBIANCE_OPTIONS, key="nt_amb")
        nt_elements = st.text_input("Preferred Elements (comma-separated)", key="nt_elem")
        nt_tone = st.text_input("Editorial Tone", key="nt_tone")
        nt_hashtags = st.text_input("Hashtags (comma-separated)", key="nt_hash")

        if st.form_submit_button("Add Theme", type="primary"):
            elements = [e.strip() for e in nt_elements.split(",") if e.strip()]
            hashtags = [h.strip() for h in nt_hashtags.split(",") if h.strip()]
            upsert_theme({
                "theme_name": new_name,
                "start_date": nt_start.isoformat(),
                "end_date": nt_end.isoformat(),
                "season": nt_season,
                "preferred_ambiances": nt_ambiances,
                "preferred_elements": elements,
                "editorial_tone": nt_tone,
                "cta_focus": nt_cta,
                "hashtags": hashtags,
                "priority": nt_pri,
                "is_active": True,
            })
            st.success("New theme added.")
            st.rerun()
