"""
InstaHotel V2 — Review Posts
View all generated posts. Approve or discard with feedback.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st
import streamlit.components.v1 as components

from app.components.ui import sidebar_css, page_title
from app.components.media_grid import _fetch_thumbnail_b64
from app.components.ig_preview import render_ig_preview, render_ig_preview_carousel
from src.services.posts_queries import (
    fetch_posts,
    fetch_posts_multi_status,
    update_post_status,
    delete_post,
)
from src.database import get_supabase, TABLE_MEDIA_LIBRARY, TABLE_CREATIVE_JOBS, TABLE_CAROUSEL_DRAFTS

sidebar_css()
page_title("Review Posts", "Approve or discard generated content")

# -------------------------------------------------------
# Session state defaults
# -------------------------------------------------------
if "review_filter_type" not in st.session_state:
    st.session_state["review_filter_type"] = "All"

# -------------------------------------------------------
# Filters
# -------------------------------------------------------
POST_TYPE_LABELS = {
    "All": None,
    "Image Post": "feed",
    "Carousel": "carousel",
    "Reel (Kling)": "reel-kling",
    "Reel (Veo)": "reel-veo",
    "Reel (Slideshow)": "reel-slideshow",
}

TYPE_BADGE_COLORS = {
    "feed": "blue",
    "carousel": "orange",
    "reel-kling": "violet",
    "reel-veo": "green",
    "reel-slideshow": "red",
}

TYPE_BADGE_LABELS = {
    "feed": "Image Post",
    "carousel": "Carousel",
    "reel-kling": "Reel Kling",
    "reel-veo": "Reel Veo",
    "reel-slideshow": "Slideshow",
}

# Status tabs
tab_review, tab_approved, tab_discarded, tab_failed, tab_published = st.tabs(
    ["To Review", "Approved", "Discarded", "Failed", "Published"]
)

STATUS_MAP = {
    "To Review": ["draft", "review"],
    "Approved": ["approved"],
    "Discarded": ["discarded"],
    "Failed": ["failed"],
    "Published": ["published"],
}


def _fetch_media_info(media_id: str) -> dict:
    """Fetch basic media info for display."""
    if not media_id:
        return {}
    result = (
        get_supabase()
        .table(TABLE_MEDIA_LIBRARY)
        .select("id, drive_file_id, file_name, media_type, ig_quality, category")
        .eq("id", media_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else {}


def _fetch_video_info(video_job_id: str) -> dict:
    """Fetch video job info for reel preview."""
    if not video_job_id:
        return {}
    result = (
        get_supabase()
        .table(TABLE_CREATIVE_JOBS)
        .select("id, result_url, drive_file_id, status")
        .eq("id", video_job_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else {}


def _fetch_scenario_info(scenario_id: str) -> dict:
    """Fetch scenario used to generate a reel video."""
    if not scenario_id:
        return {}
    result = (
        get_supabase()
        .table("generated_scenarios")
        .select("id, title, description, motion_prompt, mood, caption_hook, rating, status, characters_used")
        .eq("id", scenario_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else {}


def _fetch_carousel_info(carousel_draft_id: str) -> dict:
    """Fetch carousel draft for preview."""
    if not carousel_draft_id:
        return {}
    result = (
        get_supabase()
        .table(TABLE_CAROUSEL_DRAFTS)
        .select("id, media_ids, caption_es, caption_en, caption_fr, hashtags")
        .eq("id", carousel_draft_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else {}


def _render_post_card(post: dict, allow_actions: bool = True):
    """Render a single post card with preview and actions."""
    post_id = post["id"]
    post_type = post["post_type"]
    status = post["status"]
    badge_color = TYPE_BADGE_COLORS.get(post_type, "gray")
    badge_label = TYPE_BADGE_LABELS.get(post_type, post_type)

    with st.container(border=True):
        # Header: type badge + status + date
        header_cols = st.columns([3, 1, 1])
        with header_cols[0]:
            st.markdown(f":{badge_color}[{badge_label}]  &nbsp; **{post.get('category', '')}** — {post.get('season', '')}")
        with header_cols[1]:
            if post.get("total_cost_usd"):
                st.caption(f"${float(post['total_cost_usd']):.2f}")
        with header_cols[2]:
            created = post.get("created_at", "")[:10]
            st.caption(created)

        # Content area: thumbnail + caption
        col_media, col_content = st.columns([1, 2])

        with col_media:
            if post_type == "carousel":
                carousel = _fetch_carousel_info(post.get("carousel_draft_id"))
                media_ids = carousel.get("media_ids", [])
                if media_ids:
                    # Show first image as thumbnail
                    first_media = _fetch_media_info(media_ids[0]) if media_ids else {}
                    if first_media.get("drive_file_id"):
                        try:
                            b64 = _fetch_thumbnail_b64(first_media["drive_file_id"])
                            st.markdown(
                                f'<img src="data:image/jpeg;base64,{b64}" style="width:100%;border-radius:8px;">',
                                unsafe_allow_html=True,
                            )
                            st.caption(f"{len(media_ids)} images")
                        except Exception:
                            st.caption("Carousel preview unavailable")
                else:
                    st.caption("No carousel images")

            elif post_type.startswith("reel"):
                # Show video player if available
                video_info = _fetch_video_info(post.get("video_job_id"))
                video_url = video_info.get("result_url")
                if video_url:
                    st.video(video_url)
                else:
                    # Fallback to source image thumbnail
                    media = _fetch_media_info(post.get("media_id"))
                    if media.get("drive_file_id"):
                        try:
                            b64 = _fetch_thumbnail_b64(media["drive_file_id"])
                            st.markdown(
                                f'<img src="data:image/jpeg;base64,{b64}" style="width:100%;border-radius:8px;">',
                                unsafe_allow_html=True,
                            )
                        except Exception:
                            st.caption("Preview unavailable")
                    st.caption("Video not yet generated" if not post.get("video_job_id") else "Video loading...")

            else:  # feed
                media = _fetch_media_info(post.get("media_id"))
                if media.get("drive_file_id"):
                    try:
                        b64 = _fetch_thumbnail_b64(media["drive_file_id"])
                        st.markdown(
                            f'<img src="data:image/jpeg;base64,{b64}" style="width:100%;border-radius:8px;">',
                            unsafe_allow_html=True,
                        )
                    except Exception:
                        st.caption("Preview unavailable")

        with col_content:
            # Caption preview
            caption_es = post.get("caption_es", "")
            caption_en = post.get("caption_en", "")
            caption_fr = post.get("caption_fr", "")

            if caption_es or caption_en:
                lang_tabs = st.tabs(["ES", "EN", "FR"])
                with lang_tabs[0]:
                    st.text_area("", caption_es or "(not generated)", height=100, disabled=True, key=f"cap_es_{post_id}", label_visibility="collapsed")
                with lang_tabs[1]:
                    st.text_area("", caption_en or "(not generated)", height=100, disabled=True, key=f"cap_en_{post_id}", label_visibility="collapsed")
                with lang_tabs[2]:
                    st.text_area("", caption_fr or "(not generated)", height=100, disabled=True, key=f"cap_fr_{post_id}", label_visibility="collapsed")
            else:
                st.caption("No captions generated yet")

            hashtags = post.get("hashtags") or []
            if hashtags:
                st.caption(" ".join(f"#{h}" for h in hashtags[:10]))

        # Scenario (reels only — shows the original creative brief behind the video)
        if post_type.startswith("reel") and post.get("scenario_id"):
            scenario = _fetch_scenario_info(post["scenario_id"])
            if scenario:
                with st.expander(f":violet[Scenario] — {scenario.get('title', '(untitled)')}", expanded=False):
                    if scenario.get("description"):
                        st.markdown(f"**Concept**: {scenario['description']}")
                    if scenario.get("mood"):
                        st.caption(f"Mood: {scenario['mood']}")
                    chars = scenario.get("characters_used") or []
                    if chars:
                        st.caption(f"Characters: {', '.join(chars)}")
                    if scenario.get("caption_hook"):
                        st.markdown(f"**Hook**: *{scenario['caption_hook']}*")
                    if scenario.get("motion_prompt"):
                        st.markdown("**Motion prompt sent to video model**:")
                        st.code(scenario["motion_prompt"], language=None)
                    rating = scenario.get("rating")
                    if rating:
                        st.caption(f"Rating: {rating}/5")

        # Actions
        if allow_actions and status in ("draft", "review"):
            action_cols = st.columns([2, 1, 1])
            with action_cols[0]:
                feedback = st.text_input(
                    "Feedback",
                    key=f"fb_{post_id}",
                    placeholder="Required for discard — what's wrong?",
                    label_visibility="collapsed",
                )
            with action_cols[1]:
                if st.button("Approve", key=f"approve_{post_id}", type="primary", use_container_width=True):
                    update_post_status(post_id, "approved")
                    st.rerun()
            with action_cols[2]:
                if st.button("Discard", key=f"discard_{post_id}", use_container_width=True):
                    if not feedback.strip():
                        st.error("Feedback required for discard")
                    else:
                        update_post_status(post_id, "discarded", feedback.strip())
                        st.rerun()

        elif status == "discarded":
            fb = post.get("discard_feedback", "")
            if fb:
                st.caption(f"Discard reason: {fb}")
            # Allow re-approval
            if st.button("Re-approve", key=f"reapprove_{post_id}"):
                update_post_status(post_id, "approved")
                st.rerun()

        elif status == "published":
            permalink = post.get("ig_permalink", "")
            if permalink:
                st.markdown(f"[View on Instagram]({permalink})")
            pub_date = post.get("published_at", "")[:10] if post.get("published_at") else ""
            if pub_date:
                st.caption(f"Published: {pub_date}")

        elif status == "failed":
            err = post.get("publish_error", "")
            if err:
                st.error(f"Error: {err}")
            if st.button("Retry this post", key=f"retry_{post_id}"):
                from src.services.batch_generator import retry_failed_posts
                with st.spinner("Retrying..."):
                    res = retry_failed_posts(post_ids=[post_id])
                if res["succeeded"] > 0:
                    st.success("Retried successfully!")
                    st.rerun()
                else:
                    errs = [r["error"] for r in res["results"] if r.get("error")]
                    st.error(f"Retry failed: {errs[0] if errs else 'unknown'}")

        elif status == "approved":
            st.caption("Ready to publish — go to Publish page")


def _render_tab(statuses: list[str], allow_actions: bool):
    """Render posts for a status tab."""
    # Type filter
    type_options = list(POST_TYPE_LABELS.keys())
    selected_type = st.selectbox(
        "Filter by type",
        type_options,
        key=f"type_filter_{'_'.join(statuses)}",
        label_visibility="collapsed",
    )
    post_type_filter = POST_TYPE_LABELS[selected_type]

    posts = fetch_posts_multi_status(statuses, limit=50)
    if post_type_filter:
        posts = [p for p in posts if p["post_type"] == post_type_filter]

    if not posts:
        st.info("No posts found.")
        return

    st.caption(f"{len(posts)} post(s)")
    for post in posts:
        _render_post_card(post, allow_actions=allow_actions)


# -------------------------------------------------------
# Render tabs
# -------------------------------------------------------
with tab_review:
    _render_tab(["draft", "review"], allow_actions=True)

with tab_approved:
    _render_tab(["approved"], allow_actions=False)

with tab_discarded:
    _render_tab(["discarded"], allow_actions=False)

with tab_failed:
    failed_posts = fetch_posts_multi_status(["failed"], limit=50)
    if failed_posts:
        st.caption(f"{len(failed_posts)} failed post(s)")
        if st.button("Retry All Failed", type="primary", key="retry_all_failed"):
            from src.services.batch_generator import retry_failed_posts
            _failed_ids = [p["id"] for p in failed_posts]
            _bar = st.progress(0, text="Retrying failed posts...")
            def _progress(cur, total, msg):
                _bar.progress(cur / max(total, 1), text=msg)
            res = retry_failed_posts(post_ids=_failed_ids, progress_cb=_progress)
            _bar.empty()
            st.success(f"Done: {res['succeeded']} succeeded, {res['still_failed']} still failed")
            st.rerun()
        for post in failed_posts:
            _render_post_card(post, allow_actions=True)
    else:
        st.info("No failed posts.")

with tab_published:
    _render_tab(["published"], allow_actions=False)
