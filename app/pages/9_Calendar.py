"""
InstaHotel — Editorial Calendar
Generate, browse, and manage the posting calendar with scored media assignments.
Includes AI caption generation per slot and batch generation.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
from datetime import date, datetime, timedelta, timezone

from app.components.ui import sidebar_css, page_title
from app.components.media_grid import _fetch_thumbnail_b64
from app.components.ig_preview import render_ig_preview
from src.services.editorial_queries import (
    fetch_all_rules,
    fetch_active_theme_for_date,
    fetch_calendar_range,
    bulk_upsert_calendar,
    update_calendar_status,
    update_calendar_media,
    delete_calendar_range,
    update_calendar_publish_info,
    clear_publish_error,
)
from src.services.editorial_engine import (
    generate_calendar,
    select_best_media,
    get_current_season,
    score_media,
    _fetch_analyzed_media,
    _fetch_recent_media_ids,
)
from src.services.content_queries import (
    fetch_content_for_calendar,
    fetch_content_for_calendar_range,
    update_content,
    update_content_status,
)
from src.services.content_generator import (
    generate_for_slot,
    estimate_batch_cost,
)
from src.services.caption_generator import AVAILABLE_MODELS, DEFAULT_MODEL
from src.prompts.tone_variants import TONE_LABELS, TONE_LABELS_REVERSE

# Sonnet model picker — short labels, default first
_SONNET_OPTIONS = [
    ("Sonnet 4.6", "claude-sonnet-4-6"),
    ("Sonnet 4.5 (legacy)", "claude-sonnet-4-5-20241022"),
]

# CTA options (same as AI Captions page)
_CTA_OPTIONS = {
    "Link in bio": "link_bio",
    "Send a DM": "dm",
    "Book now": "book_now",
    "Comment": "comment",
    "Tag a friend": "tag_friend",
    "Save this post": "save_post",
    "Share": "share",
    "Visit website": "visit_website",
    "Call us": "call_us",
    "Special offer": "offer",
    "Poll": "poll",
    "Discover Sitges": "location",
}
_CTA_LABELS = list(_CTA_OPTIONS.keys())
_CTA_LABELS_WITH_AUTO = ["Auto (from theme)"] + _CTA_LABELS


@st.cache_data(ttl=300)
def _download_video_cached(drive_file_id: str) -> bytes:
    """Download video bytes from Drive. Cached 5 min."""
    from src.services.google_drive import download_file_bytes
    return download_file_bytes(drive_file_id)


sidebar_css()

# Reduce Streamlit's default wide margins while keeping it breathable
st.markdown("""
<style>
    .block-container { padding-left: 3.5rem !important; padding-right: 3.5rem !important; max-width: 100% !important; }
</style>
""", unsafe_allow_html=True)

page_title("Calendar", "Editorial posting calendar")

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
STATUS_COLORS = {
    "planned": "gray",
    "generated": "blue",
    "content_ready": "violet",
    "validated": "green",
    "scheduled": "blue",
    "published": "violet",
    "skipped": "orange",
}

# Track which expander the user last interacted with (persists across reruns)
if "cal_expanded_id" not in st.session_state:
    st.session_state["cal_expanded_id"] = None

# -------------------------------------------------------
# Sidebar controls
# -------------------------------------------------------
with st.sidebar:
    st.subheader("Calendar Controls")

    today = date.today()
    default_start = today - timedelta(days=today.weekday())  # Monday of current week

    start_date = st.date_input("Start Date", value=default_start, key="cal_start")
    weeks = st.slider("Weeks", 1, 8, 4, key="cal_weeks")
    end_date = start_date + timedelta(weeks=weeks) - timedelta(days=1)
    st.caption(f"Range: {start_date} → {end_date}")

    st.divider()

    overwrite = st.checkbox("Overwrite existing entries", value=False, key="cal_overwrite")

    if st.button("Generate Calendar", type="primary", use_container_width=True):
        rules = fetch_all_rules()
        if not rules:
            st.error("No editorial rules found. Configure rules first.")
        else:
            with st.spinner("Generating calendar..."):
                entries = generate_calendar(
                    start_date=start_date,
                    end_date=end_date,
                    rules=rules,
                    fetch_theme_fn=fetch_active_theme_for_date,
                    overwrite_existing=overwrite,
                )
                if entries:
                    bulk_upsert_calendar(entries)
                    st.success(f"Generated {len(entries)} calendar entries.")
                    st.rerun()
                else:
                    st.info("No new entries to generate (all slots already filled).")

    st.divider()
    status_filter = st.multiselect(
        "Filter by Status",
        ["planned", "generated", "content_ready", "validated", "scheduled", "published", "skipped"],
        default=["generated", "content_ready", "validated", "scheduled", "published", "planned"],
        key="cal_status_filter",
    )

# -------------------------------------------------------
# Fetch calendar data
# -------------------------------------------------------
calendar_data = fetch_calendar_range(start_date, end_date)

if status_filter:
    calendar_data = [e for e in calendar_data if e.get("status") in status_filter]

if not calendar_data:
    st.info("No calendar entries for this range. Use the sidebar to generate.")
    st.stop()

# Pre-fetch content for all visible calendar entries
_calendar_ids = [e["id"] for e in calendar_data]
_content_map = fetch_content_for_calendar_range(_calendar_ids)

# -------------------------------------------------------
# Sidebar — Batch Caption Generation
# -------------------------------------------------------
with st.sidebar:
    st.divider()
    st.subheader("Caption Generation")

    batch_scope = st.radio(
        "Scope",
        ["Slots without captions", "All slots with media"],
        key="cal_batch_scope",
    )

    batch_model_label = st.selectbox(
        "Model", [l for l, _ in _SONNET_OPTIONS], key="cal_batch_model",
    )
    batch_model = dict(_SONNET_OPTIONS)[batch_model_label]

    batch_cta_label = st.selectbox(
        "Call to Action", _CTA_LABELS_WITH_AUTO, key="cal_batch_cta",
        help="Auto = each slot uses its theme CTA; pick one to override all",
    )
    batch_cta = _CTA_OPTIONS.get(batch_cta_label)  # None if "Auto (from theme)"

    batch_tone_label = st.selectbox(
        "Tone", list(TONE_LABELS.values()), key="cal_batch_tone",
    )
    batch_tone = TONE_LABELS_REVERSE[batch_tone_label]

    batch_include_image = st.checkbox(
        "Include images in prompt",
        value=False,
        help="Sends photos to Claude Vision for richer captions (~2x cost)",
        key="cal_batch_include_img",
    )

    # Filter eligible entries
    if batch_scope == "Slots without captions":
        batch_entries = [
            e for e in calendar_data
            if (e.get("media_id") or e.get("manual_media_id"))
            and e["id"] not in _content_map
        ]
    else:
        batch_entries = [
            e for e in calendar_data
            if e.get("media_id") or e.get("manual_media_id")
        ]

    # Cost estimate
    if batch_entries:
        estimate = estimate_batch_cost(batch_entries, batch_model, batch_include_image)
        st.caption(
            f"{estimate['slot_count']} slots | "
            f"~${estimate['estimated_cost_usd']:.3f} "
            f"({estimate['model_label']})"
        )
    else:
        st.caption("No eligible slots")

    if st.button(
        "Generate Captions (Batch)",
        type="primary",
        use_container_width=True,
        disabled=len(batch_entries) == 0,
        key="cal_batch_gen",
    ):
        progress_bar = st.progress(0, text="Generating captions...")
        success_count = 0
        total = len(batch_entries)
        total_cost = 0.0

        for i, entry in enumerate(batch_entries):
            try:
                # Optionally download and encode image
                image_b64 = None
                if batch_include_image:
                    media_id = entry.get("manual_media_id") or entry.get("media_id")
                    if media_id:
                        from src.services.media_queries import fetch_media_by_id
                        media = fetch_media_by_id(media_id)
                        if media and media.get("drive_file_id"):
                            from src.services.google_drive import download_file_bytes
                            from src.utils import encode_image_bytes
                            raw = download_file_bytes(media["drive_file_id"])
                            image_b64 = encode_image_bytes(raw)

                result = generate_for_slot(
                    entry=entry,
                    model=batch_model,
                    include_image=batch_include_image,
                    image_base64=image_b64,
                    cta_override=batch_cta,
                    tone=batch_tone,
                )
                if result:
                    success_count += 1
                    total_cost += result.get("cost_usd", 0)
            except Exception as e:
                st.warning(f"Failed for {entry['post_date']} S{entry.get('slot_index', 1)}: {e}")

            progress_bar.progress((i + 1) / total, text=f"Generated {i + 1}/{total}...")

        progress_bar.empty()
        st.success(f"Generated captions for {success_count}/{total} slots (${total_cost:.4f})")
        st.rerun()

# -------------------------------------------------------
# Sidebar — Instagram Publishing
# -------------------------------------------------------
with st.sidebar:
    st.divider()
    st.subheader("Instagram Publishing")

    # Token status indicator
    from src.services.publisher import _get_secret as _pub_secret
    _ig_token_set = bool(_pub_secret("INSTAGRAM_ACCESS_TOKEN"))
    _ig_acct_set = bool(_pub_secret("INSTAGRAM_ACCOUNT_ID"))

    if _ig_token_set and _ig_acct_set:
        st.markdown(":green[●] IG API connected")
    else:
        missing = []
        if not _ig_token_set:
            missing.append("INSTAGRAM_ACCESS_TOKEN")
        if not _ig_acct_set:
            missing.append("INSTAGRAM_ACCOUNT_ID")
        st.markdown(f":red[●] Missing: {', '.join(missing)}")

    # Publishing variant/language selection
    _pub_lang = st.selectbox(
        "Publish Language", ["ES", "EN", "FR"],
        key="pub_lang",
    )
    _pub_variant = st.selectbox(
        "Caption Variant", ["Short", "Storytelling", "Reel"],
        key="pub_variant",
    )
    _pub_multilingual = st.checkbox(
        "Multilingual (stacked ES+EN+FR)", value=True,
        key="pub_multilingual",
        help="If checked, all 3 languages are stacked in one post",
    )

    # Batch publish validated slots
    _validated_entries = [
        e for e in calendar_data
        if e.get("status") == "validated"
        and e["id"] in _content_map
    ]

    if _validated_entries:
        st.caption(f"{len(_validated_entries)} validated slots ready to publish")
    else:
        st.caption("No validated slots to publish")

    if st.button(
        "Schedule All Validated",
        type="primary",
        use_container_width=True,
        disabled=len(_validated_entries) == 0 or not (_ig_token_set and _ig_acct_set),
        key="pub_batch",
    ):
        from src.services.publisher import publish_slot as _pub_slot
        from src.services.media_queries import fetch_media_by_id as _fetch_media

        _pub_progress = st.progress(0, text="Publishing...")
        _pub_ok = 0
        _pub_err = 0
        _pub_total = len(_validated_entries)

        for _pi, _pe in enumerate(_validated_entries):
            try:
                _pc = _content_map.get(_pe["id"])
                _mid = _pe.get("manual_media_id") or _pe.get("media_id")
                _pm = _fetch_media(_mid) if _mid else None
                if _pc and _pm:
                    _pr = _pub_slot(
                        entry=_pe,
                        content=_pc,
                        media=_pm,
                        variant=_pub_variant.lower(),
                        language=_pub_lang.lower(),
                        multilingual=_pub_multilingual,
                    )
                    if _pr.get("success"):
                        _pub_ok += 1
                    else:
                        _pub_err += 1
                        st.warning(f"{_pe['post_date']} S{_pe.get('slot_index', 1)}: {_pr.get('error', 'Unknown')}")
                else:
                    _pub_err += 1
            except Exception as _ex:
                _pub_err += 1
                st.warning(f"{_pe['post_date']}: {_ex}")

            _pub_progress.progress((_pi + 1) / _pub_total, text=f"Published {_pi + 1}/{_pub_total}...")

        _pub_progress.empty()
        st.success(f"Done: {_pub_ok} published/scheduled, {_pub_err} errors")
        st.rerun()

# -------------------------------------------------------
# View toggle
# -------------------------------------------------------
view_mode = st.radio("View", ["Week Grid", "List"], horizontal=True, key="cal_view")

with st.expander("Status workflow & actions guide", expanded=False):
    st.markdown("""
**Slot statuses** — each calendar slot progresses through this workflow:

| Status | Meaning |
|---|---|
| :gray[●] **planned** | Slot created, media assigned but no captions yet |
| :blue[●] **generated** | AI captions have been generated (draft) |
| :violet[●] **content_ready** | Captions linked and ready for review |
| :green[●] **validated** | You reviewed and approved the post — ready to publish |
| :blue[●] **scheduled** | Sent to Instagram with a future publish time — IG will auto-publish |
| :violet[●] **published** | Post has been published on Instagram |
| :orange[●] **skipped** | Slot intentionally skipped (holiday, no content, etc.) |

**Caption actions:**
- **Save Edits** — save your manual edits to the captions (sets status to *edited*)
- **Approve** — mark captions as final and move slot to *validated*
- **Regenerate** — discard current captions and generate new ones with AI

**Slot actions:**
- **Validate** — mark the slot as ready to publish (even without captions)
- **Skip** — mark the slot as intentionally skipped
- **Published** — mark the slot as already published
- **Reset** — revert slot back to *generated* status
- **Swap Media** — replace the assigned photo with an alternative
""")

# -------------------------------------------------------
# Week Grid View
# -------------------------------------------------------
if view_mode == "Week Grid":
    # Group entries by week start (Monday)
    entries_by_date: dict[str, list[dict]] = {}
    for e in calendar_data:
        entries_by_date.setdefault(e["post_date"], []).append(e)

    # Iterate week by week
    current_week_start = start_date
    while current_week_start <= end_date:
        week_end = current_week_start + timedelta(days=6)
        st.markdown(f"#### Week of {current_week_start.strftime('%b %d')}")

        cols = st.columns(7)
        for i, col in enumerate(cols):
            day = current_week_start + timedelta(days=i)
            day_str = day.isoformat()
            day_entries = entries_by_date.get(day_str, [])

            with col:
                is_today = day == today
                header = f"**{DAY_NAMES[i]} {day.day}**" if not is_today else f"**:red[{DAY_NAMES[i]} {day.day}]**"
                st.markdown(header)

                if not day_entries:
                    st.caption("—")
                else:
                    for entry in day_entries:
                        status = entry.get("status", "planned")
                        cat = entry.get("target_category") or "?"
                        score = entry.get("media_score")
                        slot = entry.get("slot_index", 1)
                        media_id = entry.get("manual_media_id") or entry.get("media_id")
                        has_content = entry["id"] in _content_map

                        # Show thumbnail if media assigned
                        if media_id:
                            score_str = f"{score:.0f}" if score else "—"
                            caption_icon = " &check;" if has_content else ""
                            st.markdown(f":{STATUS_COLORS.get(status, 'gray')}[●] {cat}{caption_icon}")
                            st.caption(f"S{slot} | {score_str}pts")
                        else:
                            st.markdown(f":gray[○] {cat}")
                            st.caption(f"S{slot} | no media")

        st.divider()
        current_week_start += timedelta(days=7)

# -------------------------------------------------------
# List View
# -------------------------------------------------------
else:
    for entry in calendar_data:
        post_date = entry["post_date"]
        status = entry.get("status", "planned")
        cat = entry.get("target_category") or "?"
        fmt = entry.get("target_format") or "?"
        score = entry.get("media_score")
        theme = entry.get("theme_name") or "—"
        slot = entry.get("slot_index", 1)
        season = entry.get("season_context") or "—"
        media_id = entry.get("manual_media_id") or entry.get("media_id")
        media = None
        has_content = entry["id"] in _content_map

        score_str = f"{score:.1f}" if score else "—"
        color = STATUS_COLORS.get(status, "gray")
        caption_tag = " | captions" if has_content else ""

        _is_expanded = st.session_state.get("cal_expanded_id") == entry["id"]
        with st.expander(f":{color}[●] {post_date} — S{slot} | {cat} | {score_str}pts | {status}{caption_tag}", expanded=_is_expanded):
            c1, c2 = st.columns([2, 1])

            with c1:
                st.markdown(f"**Date:** {post_date}  \n**Slot:** {slot}  \n**Category:** {cat}  \n**Format:** {fmt}")
                st.markdown(f"**Season:** {season}  \n**Theme:** {theme}")
                st.markdown(f"**Score:** {score_str}  \n**Status:** :{color}[{status}]")

                breakdown = entry.get("score_breakdown")
                if breakdown:
                    parts = [f"{dim}: {pts}" for dim, pts in breakdown.items()]
                    st.caption("Score breakdown — " + " · ".join(parts))

            with c2:
                if media_id:
                    from src.services.media_queries import fetch_media_by_id
                    media = fetch_media_by_id(media_id)
                    if media and media.get("drive_file_id"):
                        _is_video_media = media.get("media_type") == "video"
                        if _is_video_media:
                            try:
                                _vid_bytes = _download_video_cached(media["drive_file_id"])
                                st.video(_vid_bytes)
                            except Exception:
                                st.caption("(video unavailable)")
                        else:
                            try:
                                thumb = _fetch_thumbnail_b64(media["drive_file_id"])
                                if thumb:
                                    st.image(f"data:image/jpeg;base64,{thumb}", use_container_width=True)
                            except Exception:
                                st.caption("(thumbnail unavailable)")
                    _fname = media["file_name"] if media else media_id[:8]
                    _iq = media.get("ig_quality") if media else None
                    st.caption(f"{_fname} — quality: {_iq}/10" if _iq else _fname)
                    _desc_en = media.get("description_en") if media else None
                    if _desc_en:
                        st.caption(_desc_en)
                else:
                    st.caption("No media assigned")

            # -----------------------------------------------
            # Caption section
            # -----------------------------------------------
            st.markdown("---")

            content = _content_map.get(entry["id"])

            if content:
                def _pin_this(eid=entry["id"]):
                    st.session_state["cal_expanded_id"] = eid

                content_status = content.get("content_status", "draft")
                _status_color = {"draft": "gray", "edited": "blue", "approved": "green"}.get(content_status, "gray")
                st.markdown(f"**Captions** — :{_status_color}[{content_status}]")

                # Usage info
                if content.get("model"):
                    st.caption(
                        f"Model: {content['model']} | "
                        f"Tokens: {content.get('input_tokens', 0):,} in / {content.get('output_tokens', 0):,} out | "
                        f"Cost: ${content.get('cost_usd', 0):.4f}"
                    )

                # Detect video for reel variant
                _is_video = media and media.get("media_type") == "video"

                # Tabs for languages
                tab_es, tab_en, tab_fr = st.tabs(["ES", "EN", "FR"])

                with tab_es:
                    if _is_video:
                        new_reel_es = st.text_area(
                            "Reel", content.get("caption_reel_es", ""),
                            height=80, key=f"cap_reel_es_{entry['id']}"
                        )
                    else:
                        new_short_es = st.text_area(
                            "Short", content.get("caption_short_es", ""),
                            height=80, key=f"cap_short_es_{entry['id']}"
                        )
                        new_story_es = st.text_area(
                            "Storytelling", content.get("caption_story_es", ""),
                            height=150, key=f"cap_story_es_{entry['id']}"
                        )

                with tab_en:
                    if _is_video:
                        new_reel_en = st.text_area(
                            "Reel", content.get("caption_reel_en", ""),
                            height=80, key=f"cap_reel_en_{entry['id']}"
                        )
                    else:
                        new_short_en = st.text_area(
                            "Short", content.get("caption_short_en", ""),
                            height=80, key=f"cap_short_en_{entry['id']}"
                        )
                        new_story_en = st.text_area(
                            "Storytelling", content.get("caption_story_en", ""),
                            height=150, key=f"cap_story_en_{entry['id']}"
                        )

                with tab_fr:
                    if _is_video:
                        new_reel_fr = st.text_area(
                            "Reel", content.get("caption_reel_fr", ""),
                            height=80, key=f"cap_reel_fr_{entry['id']}"
                        )
                    else:
                        new_short_fr = st.text_area(
                            "Short", content.get("caption_short_fr", ""),
                            height=80, key=f"cap_short_fr_{entry['id']}"
                        )
                        new_story_fr = st.text_area(
                            "Storytelling", content.get("caption_story_fr", ""),
                            height=150, key=f"cap_story_fr_{entry['id']}"
                        )

                # Hashtags
                existing_hashtags = content.get("hashtags", [])
                hashtag_str = " ".join(f"#{h}" for h in existing_hashtags) if existing_hashtags else ""
                new_hashtags = st.text_area(
                    "Hashtags", hashtag_str, height=60,
                    key=f"cap_hashtags_{entry['id']}"
                )

                # IG Preview
                _preview_key = f"ig_preview_{entry['id']}"
                st.checkbox("Show IG Preview", key=_preview_key, on_change=_pin_this)

                if st.session_state.get(_preview_key):
                    # Build variant options based on media type (multilingual first = default)
                    if _is_video:
                        _pv_variants = ["Multilingual Reel", "Reel"]
                    else:
                        _pv_variants = ["Multilingual Short", "Multilingual Story", "Short", "Storytelling"]

                    _pv_c1, _pv_c2 = st.columns([1, 1])
                    with _pv_c1:
                        _pv_lang = st.selectbox("Language", ["ES", "EN", "FR"], key=f"ig_pv_lang_{entry['id']}", on_change=_pin_this)
                    with _pv_c2:
                        _pv_var = st.selectbox("Variant", _pv_variants, key=f"ig_pv_var_{entry['id']}", on_change=_pin_this)

                    _pv_is_multilingual = _pv_var.startswith("Multilingual")
                    _pv_is_reel = "Reel" in _pv_var

                    if _pv_is_multilingual:
                        # Determine base variant: short, story, or reel
                        if "Short" in _pv_var:
                            _pv_base = "short"
                        elif "Story" in _pv_var:
                            _pv_base = "story"
                        else:
                            _pv_base = "reel"
                        _es = content.get(f"caption_{_pv_base}_es", "")
                        _en = content.get(f"caption_{_pv_base}_en", "")
                        _fr = content.get(f"caption_{_pv_base}_fr", "")
                        _parts = [p for p in [_es, f"\U0001f1ec\U0001f1e7\n{_en}" if _en else "", f"\U0001f1eb\U0001f1f7\n{_fr}" if _fr else ""] if p]
                        _pv_caption = "\n\n".join(_parts)
                    else:
                        # Single-language variant
                        _var_key = {"Short": "short", "Storytelling": "story", "Reel": "reel"}.get(_pv_var, "short")
                        _pv_field = f"caption_{_var_key}_{_pv_lang.lower()}"
                        _pv_caption = content.get(_pv_field, "")

                    _pv_tags = " ".join(f"#{h}" for h in (content.get("hashtags") or [])) if content.get("hashtags") else ""

                    # Fetch image for preview
                    _pv_img = None
                    if media_id and media and media.get("drive_file_id"):
                        try:
                            _pv_img = _fetch_thumbnail_b64(media["drive_file_id"])
                        except Exception:
                            pass

                    if _pv_img and _pv_caption:
                        from streamlit.components.v1 import html as _st_html
                        _pv_html, _pv_h = render_ig_preview(_pv_img, _pv_caption, _pv_tags, is_reel=_pv_is_reel)
                        _st_html(_pv_html, height=_pv_h)
                    elif not _pv_caption:
                        st.caption("No caption text for this language/variant yet.")
                    else:
                        st.caption("No image available for preview.")

                # Caption actions
                cap_cols = st.columns(3)

                with cap_cols[0]:
                    if st.button("Save Edits", key=f"cap_save_{entry['id']}", use_container_width=True, on_click=_pin_this, help="Save your manual text edits (sets status to 'edited')"):
                        parsed_tags = [t.lstrip("#").strip() for t in new_hashtags.split() if t.strip()]
                        if _is_video:
                            updates = {
                                "caption_reel_es": st.session_state.get(f"cap_reel_es_{entry['id']}", ""),
                                "caption_reel_en": st.session_state.get(f"cap_reel_en_{entry['id']}", ""),
                                "caption_reel_fr": st.session_state.get(f"cap_reel_fr_{entry['id']}", ""),
                                "hashtags": parsed_tags,
                                "content_status": "edited",
                            }
                        else:
                            updates = {
                                "caption_short_es": new_short_es,
                                "caption_short_en": new_short_en,
                                "caption_short_fr": new_short_fr,
                                "caption_story_es": new_story_es,
                                "caption_story_en": new_story_en,
                                "caption_story_fr": new_story_fr,
                                "hashtags": parsed_tags,
                                "content_status": "edited",
                            }
                        if update_content(content["id"], updates):
                            st.success("Saved!")
                            st.rerun()

                with cap_cols[1]:
                    if st.button(
                        "Approve", key=f"cap_approve_{entry['id']}",
                        type="primary", use_container_width=True,
                        disabled=content_status == "approved",
                        on_click=_pin_this,
                        help="Mark captions as final — moves slot to 'validated' status",
                    ):
                        update_content_status(content["id"], "approved")
                        update_calendar_status(entry["id"], "validated")
                        st.rerun()

                with cap_cols[2]:
                    _regen_clicked = st.button("Regenerate", key=f"cap_regen_{entry['id']}", use_container_width=True, on_click=_pin_this, help="Generate new AI captions (replaces current ones)")

                # Regenerate options (only shown when clicked or via expander)
                if _regen_clicked:
                    st.session_state[f"regen_open_{entry['id']}"] = True

                if st.session_state.get(f"regen_open_{entry['id']}"):
                    def _pin_regen(eid=entry["id"]):
                        st.session_state["cal_expanded_id"] = eid

                    _rc1, _rc2, _rc3, _rc4, _rc5 = st.columns([1, 1, 1, 1, 1])
                    with _rc1:
                        regen_model_label = st.selectbox("Model", [l for l, _ in _SONNET_OPTIONS], key=f"cap_regen_model_{entry['id']}", on_change=_pin_regen)
                    with _rc2:
                        regen_cta_label = st.selectbox("CTA", _CTA_LABELS, key=f"cap_regen_cta_{entry['id']}", on_change=_pin_regen)
                    with _rc3:
                        regen_tone_label = st.selectbox("Tone", list(TONE_LABELS.values()), key=f"cap_regen_tone_{entry['id']}", on_change=_pin_regen)
                    with _rc4:
                        regen_img = st.selectbox("Image in prompt", ["No", "Yes"], key=f"cap_regen_img_{entry['id']}", on_change=_pin_regen)
                    with _rc5:
                        st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)
                        _regen_go = st.button("Confirm Regenerate", key=f"cap_regen_go_{entry['id']}", type="primary", use_container_width=True)
                    regen_model = dict(_SONNET_OPTIONS)[regen_model_label]
                    regen_cta = _CTA_OPTIONS[regen_cta_label]
                    regen_tone = TONE_LABELS_REVERSE[regen_tone_label]
                    regen_include = regen_img == "Yes"
                    from src.services.caption_generator import compute_cost as _cc
                    _rest = _cc(regen_model, 2000 if regen_include else 800, 600)
                    st.caption(f"Est. ~${_rest:.4f}")
                    if _regen_go:
                        with st.spinner("Regenerating captions..."):
                            try:
                                image_b64 = None
                                if regen_include and media_id:
                                    from src.services.media_queries import fetch_media_by_id as _fetch
                                    from src.services.google_drive import download_file_bytes
                                    from src.utils import encode_image_bytes
                                    _m = _fetch(media_id)
                                    if _m and _m.get("drive_file_id"):
                                        image_b64 = encode_image_bytes(download_file_bytes(_m["drive_file_id"]))
                                result = generate_for_slot(entry=entry, model=regen_model, include_image=regen_include, image_base64=image_b64, cta_override=regen_cta, tone=regen_tone)
                                if result:
                                    st.session_state[f"regen_open_{entry['id']}"] = False
                                    st.success("New captions generated!")
                                    st.rerun()
                                else:
                                    st.error("Generation failed — no media assigned?")
                            except Exception as e:
                                st.error(f"Generation failed: {e}")

            else:
                # No captions yet
                if media_id:
                    def _pin_expander(eid=entry["id"]):
                        st.session_state["cal_expanded_id"] = eid

                    _gc1, _gc2, _gc3, _gc4, _gc5 = st.columns([1, 1, 1, 1, 1])
                    with _gc1:
                        slot_model_label = st.selectbox("Model", [l for l, _ in _SONNET_OPTIONS], key=f"cap_model_{entry['id']}", on_change=_pin_expander)
                    with _gc2:
                        slot_cta_label = st.selectbox("CTA", _CTA_LABELS, key=f"cap_cta_{entry['id']}", on_change=_pin_expander)
                    with _gc3:
                        slot_tone_label = st.selectbox("Tone", list(TONE_LABELS.values()), key=f"cap_tone_{entry['id']}", on_change=_pin_expander)
                    with _gc4:
                        slot_img_sel = st.selectbox("Image in prompt", ["No", "Yes"], key=f"cap_img_{entry['id']}", on_change=_pin_expander)
                    with _gc5:
                        st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)
                        _gen_clicked = st.button("Generate Captions", key=f"cap_gen_{entry['id']}", type="primary", use_container_width=True, on_click=_pin_expander)
                    slot_model = dict(_SONNET_OPTIONS)[slot_model_label]
                    slot_cta = _CTA_OPTIONS[slot_cta_label]
                    slot_tone = TONE_LABELS_REVERSE[slot_tone_label]
                    inc_img = slot_img_sel == "Yes"
                    from src.services.caption_generator import compute_cost
                    _est = compute_cost(slot_model, 2000 if inc_img else 800, 600)
                    st.caption(f"Est. ~${_est:.4f}")
                    if _gen_clicked:
                        with st.spinner("Generating captions..."):
                            try:
                                image_b64 = None
                                if inc_img:
                                    from src.services.media_queries import fetch_media_by_id as _fetch
                                    from src.services.google_drive import download_file_bytes
                                    from src.utils import encode_image_bytes
                                    _m = _fetch(media_id)
                                    if _m and _m.get("drive_file_id"):
                                        image_b64 = encode_image_bytes(download_file_bytes(_m["drive_file_id"]))
                                result = generate_for_slot(entry=entry, model=slot_model, include_image=inc_img, image_base64=image_b64, cta_override=slot_cta, tone=slot_tone)
                                if result:
                                    st.success("Captions generated!")
                                    st.rerun()
                                else:
                                    st.error("Generation failed — check media assignment.")
                            except Exception as e:
                                st.error(f"Generation failed: {e}")
                else:
                    st.caption("Assign media first to generate captions.")

            # -----------------------------------------------
            # Publishing info (scheduled / published)
            # -----------------------------------------------
            if status in ("scheduled", "published"):
                st.markdown("---")
                _ig_id = entry.get("ig_post_id")
                _ig_link = entry.get("ig_permalink")
                _sched_t = entry.get("scheduled_publish_time")
                _pub_at = entry.get("published_at")

                if status == "scheduled":
                    _sched_display = _sched_t[:16].replace("T", " ") if _sched_t else "unknown"
                    st.info(f"Scheduled for {_sched_display}  \nIG Post ID: `{_ig_id}`")
                elif status == "published":
                    _pub_display = _pub_at[:16].replace("T", " ") if _pub_at else "—"
                    if _ig_link:
                        st.success(f"Published {_pub_display} — [{_ig_link}]({_ig_link})")
                    else:
                        st.success(f"Published {_pub_display}  \nIG Post ID: `{_ig_id}`")

            # Show any publish error
            _pub_error = entry.get("publish_error")
            if _pub_error:
                st.error(f"Last publish error: {_pub_error}")

            # -----------------------------------------------
            # Status actions
            # -----------------------------------------------
            st.markdown("---")
            action_cols = st.columns(6)

            with action_cols[0]:
                if st.button("Validate", key=f"val_{entry['id']}", type="primary", disabled=status in ("validated", "scheduled", "published"), help="Mark slot as ready to publish"):
                    update_calendar_status(entry["id"], "validated")
                    st.rerun()

            with action_cols[1]:
                # Real Publish to IG button
                _can_publish = (
                    status == "validated"
                    and has_content
                    and media_id
                    and _ig_token_set
                    and _ig_acct_set
                )
                _pub_clicked = st.button(
                    "Publish to IG",
                    key=f"pub_ig_{entry['id']}",
                    type="primary",
                    disabled=not _can_publish,
                    help="Publish or schedule this post on Instagram" if _can_publish else "Validate slot first + configure IG token",
                )

            with action_cols[2]:
                if st.button("Skip", key=f"skip_{entry['id']}", disabled=status == "skipped", help="Intentionally skip this slot (holiday, no content, etc.)"):
                    update_calendar_status(entry["id"], "skipped")
                    st.rerun()

            with action_cols[3]:
                if st.button("Published", key=f"pub_{entry['id']}", disabled=status == "published", help="Mark as already published on Instagram (manual)"):
                    update_calendar_status(entry["id"], "published")
                    st.rerun()

            with action_cols[4]:
                if st.button("Reset", key=f"reset_{entry['id']}", disabled=status in ("generated", "planned"), help="Revert slot back to 'generated' status"):
                    update_calendar_status(entry["id"], "generated")
                    st.rerun()

            # Swap media — show top 5 alternatives
            with action_cols[5]:
                swap_clicked = st.button("Swap Media", key=f"swap_btn_{entry['id']}")

            # Handle Publish to IG click
            if _pub_clicked:
                from src.services.publisher import publish_slot as _do_publish
                from src.services.media_queries import fetch_media_by_id as _fetch_pub_media

                with st.spinner("Publishing to Instagram..."):
                    _pub_content = _content_map.get(entry["id"])
                    _pub_media = _fetch_pub_media(media_id) if media_id else None
                    if _pub_content and _pub_media:
                        _pub_result = _do_publish(
                            entry=entry,
                            content=_pub_content,
                            media=_pub_media,
                            variant=st.session_state.get("pub_variant", "Short").lower(),
                            language=st.session_state.get("pub_lang", "ES").lower(),
                            multilingual=st.session_state.get("pub_multilingual", True),
                        )
                        if _pub_result.get("success"):
                            _r_status = _pub_result.get("status", "published")
                            if _r_status == "scheduled":
                                st.success(f"Scheduled! IG Post ID: {_pub_result.get('ig_post_id')}")
                            else:
                                _link = _pub_result.get("ig_permalink", "")
                                st.success(f"Published! {_link}")
                            st.rerun()
                        else:
                            st.error(f"Publish failed: {_pub_result.get('error')}")
                    else:
                        st.error("Missing content or media for this slot.")

            if swap_clicked:
                st.session_state[f"swap_open_{entry['id']}"] = True

            if st.session_state.get(f"swap_open_{entry['id']}"):
                st.markdown("**Alternative Media (top 5):**")
                all_media = _fetch_analyzed_media()
                recently_used = _fetch_recent_media_ids()
                target_season = entry.get("season_context") or get_current_season(date.fromisoformat(post_date))
                theme_data = None
                if entry.get("theme_id"):
                    theme_data = fetch_active_theme_for_date(date.fromisoformat(post_date))

                # Exclude currently assigned media from candidates
                batch_used = set()
                current_media = entry.get("manual_media_id") or entry.get("media_id")

                candidates = select_best_media(
                    all_media=all_media,
                    target_category=entry.get("target_category"),
                    target_season=target_season,
                    target_format=entry.get("target_format"),
                    min_quality=1,  # Show all quality levels for swap
                    theme=theme_data,
                    recently_used_ids=recently_used,
                    batch_used_ids=batch_used,
                    today=date.fromisoformat(post_date),
                    top_n=6,
                )

                # Filter out currently assigned
                candidates = [(m, s, b) for m, s, b in candidates if m["id"] != current_media][:5]

                if not candidates:
                    st.caption("No alternative candidates found.")
                else:
                    swap_cols = st.columns(5)
                    for idx, (cand, cand_score, cand_bd) in enumerate(candidates):
                        with swap_cols[idx]:
                            # Thumbnail
                            try:
                                thumb = _fetch_thumbnail_b64(cand["drive_file_id"])
                                if thumb:
                                    st.image(f"data:image/jpeg;base64,{thumb}", use_container_width=True)
                            except Exception:
                                pass
                            st.caption(f"{cand.get('category', '?')} | {cand_score:.0f}pts")
                            if st.button("Use", key=f"use_{entry['id']}_{cand['id']}"):
                                update_calendar_media(entry["id"], cand["id"], cand_score, cand_bd)
                                st.session_state[f"swap_open_{entry['id']}"] = False
                                st.rerun()

                if st.button("Cancel", key=f"swap_cancel_{entry['id']}"):
                    st.session_state[f"swap_open_{entry['id']}"] = False
                    st.rerun()

# -------------------------------------------------------
# Summary stats
# -------------------------------------------------------
st.divider()
st.markdown("### Summary")
total = len(calendar_data)
by_status = {}
for e in calendar_data:
    s = e.get("status", "planned")
    by_status[s] = by_status.get(s, 0) + 1

captions_count = len(_content_map)

metric_cols = st.columns(len(by_status) + 2)
metric_cols[0].metric("Total Entries", total)
for i, (s, count) in enumerate(sorted(by_status.items()), 1):
    metric_cols[i].metric(s.capitalize(), count)
metric_cols[len(by_status) + 1].metric("Captions Generated", captions_count)

filled = sum(1 for e in calendar_data if e.get("media_id") or e.get("manual_media_id"))
avg_score = 0.0
scored = [e["media_score"] for e in calendar_data if e.get("media_score")]
if scored:
    avg_score = sum(scored) / len(scored)

c1, c2 = st.columns(2)
c1.metric("Media Assigned", f"{filled}/{total}")
c2.metric("Avg Score", f"{avg_score:.1f}")
