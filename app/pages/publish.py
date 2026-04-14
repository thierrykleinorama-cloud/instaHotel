"""
InstaHotel V2 — Publish to Instagram
Show approved posts and publish them one by one.
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
from src.services.posts_queries import fetch_posts, update_post, update_post_status
from src.services.publisher import publish_post, _resolve_post_caption
from src.database import get_supabase, TABLE_MEDIA_LIBRARY, TABLE_CREATIVE_JOBS, TABLE_CAROUSEL_DRAFTS

sidebar_css()
page_title("Publish", "Send approved posts to Instagram")

# -------------------------------------------------------
# Session state
# -------------------------------------------------------
if "publish_confirm" not in st.session_state:
    st.session_state["publish_confirm"] = None

# -------------------------------------------------------
# Check IG credentials
# -------------------------------------------------------
def _check_ig_credentials() -> bool:
    from src.services.publisher import _get_secret
    token = _get_secret("INSTAGRAM_ACCESS_TOKEN")
    account = _get_secret("INSTAGRAM_ACCOUNT_ID")
    return bool(token and account)


if not _check_ig_credentials():
    st.warning("Instagram credentials not configured. Set `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_ACCOUNT_ID` in `.env`.")
    st.stop()

st.success("Instagram connected", icon=":material/check_circle:")

# -------------------------------------------------------
# Fetch approved posts
# -------------------------------------------------------
posts = fetch_posts(status="approved", limit=50)

if not posts:
    st.info("No approved posts ready to publish. Go to **Review** to approve some posts first.")
    st.stop()

st.caption(f"{len(posts)} post(s) ready to publish")

# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

TYPE_LABELS = {
    "feed": "Image Post",
    "carousel": "Carousel",
    "reel-kling": "Reel (Kling)",
    "reel-veo": "Reel (Veo)",
    "reel-slideshow": "Reel (Slideshow)",
}


def _fetch_media(media_id):
    if not media_id:
        return {}
    r = get_supabase().table(TABLE_MEDIA_LIBRARY).select("*").eq("id", media_id).limit(1).execute()
    return r.data[0] if r.data else {}


def _fetch_carousel_media_ids(carousel_draft_id):
    if not carousel_draft_id:
        return []
    r = get_supabase().table(TABLE_CAROUSEL_DRAFTS).select("media_ids").eq("id", carousel_draft_id).limit(1).execute()
    return r.data[0].get("media_ids", []) if r.data else []


# -------------------------------------------------------
# Render each approved post
# -------------------------------------------------------
for post in posts:
    post_id = post["id"]
    post_type = post["post_type"]
    label = TYPE_LABELS.get(post_type, post_type)

    with st.container(border=True):
        st.markdown(f"### {label} — {post.get('category', '')}")

        col_preview, col_publish = st.columns([2, 1])

        with col_preview:
            # Show IG preview
            try:
                if post_type == "carousel":
                    media_ids = _fetch_carousel_media_ids(post.get("carousel_draft_id"))
                    images_b64 = []
                    for mid in media_ids[:10]:
                        m = _fetch_media(mid)
                        if m.get("drive_file_id"):
                            try:
                                images_b64.append(_fetch_thumbnail_b64(m["drive_file_id"]))
                            except Exception:
                                pass
                    if images_b64:
                        caption_text = post.get("caption_es", "") or ""
                        hashtag_str = " ".join(f"#{h}" for h in (post.get("hashtags") or []))
                        html, height = render_ig_preview_carousel(images_b64, caption_text, hashtag_str)
                        components.html(html, height=height)
                    else:
                        st.caption("Carousel preview unavailable")

                elif post_type.startswith("reel"):
                    # Show video player
                    vid_id = post.get("video_job_id")
                    if vid_id:
                        r = get_supabase().table(TABLE_CREATIVE_JOBS).select("result_url").eq("id", vid_id).limit(1).execute()
                        if r.data and r.data[0].get("result_url"):
                            st.video(r.data[0]["result_url"])
                        else:
                            st.caption("Video not available")
                    else:
                        st.caption("No video linked")

                else:  # feed
                    media = _fetch_media(post.get("media_id"))
                    if media.get("drive_file_id"):
                        b64 = _fetch_thumbnail_b64(media["drive_file_id"])
                        caption_text = post.get("caption_es", "") or ""
                        hashtag_str = " ".join(f"#{h}" for h in (post.get("hashtags") or []))
                        html, height = render_ig_preview(b64, caption_text, hashtag_str)
                        components.html(html, height=height)
            except Exception as e:
                st.caption(f"Preview error: {e}")

        with col_publish:
            # Editable caption (last-minute tweaks)
            edited_es = st.text_area(
                "Caption (ES)",
                post.get("caption_es", ""),
                height=120,
                key=f"pub_cap_{post_id}",
            )

            # Language / multilingual toggle
            multilingual = st.checkbox("Multilingual (ES+EN+FR)", value=True, key=f"pub_ml_{post_id}")

            # Carousel music warning
            if post_type == "carousel":
                st.info("Music must be added manually in the Instagram app after publishing.", icon=":material/music_note:")

            # Cost info
            if post.get("total_cost_usd"):
                st.caption(f"Generation cost: ${float(post['total_cost_usd']):.2f}")

            # Save caption edits if changed
            if edited_es != post.get("caption_es", ""):
                if st.button("Save caption edit", key=f"save_cap_{post_id}"):
                    update_post(post_id, {"caption_es": edited_es})
                    st.success("Caption updated")
                    st.rerun()

            st.divider()

            # Publish button with confirmation
            confirm_key = f"confirm_{post_id}"
            if st.session_state.get("publish_confirm") == post_id:
                st.warning("Publish this post to Instagram?")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("Yes, publish", key=f"yes_{post_id}", type="primary"):
                        st.session_state["publish_confirm"] = None
                        # Update caption if edited
                        final_post = dict(post)
                        if edited_es != post.get("caption_es", ""):
                            update_post(post_id, {"caption_es": edited_es})
                            final_post["caption_es"] = edited_es

                        with st.spinner("Publishing to Instagram..."):
                            result = publish_post(final_post, multilingual=multilingual)

                        if result.get("success"):
                            st.success(f"Published! [View on Instagram]({result.get('ig_permalink', '')})")
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"Publish failed: {result.get('error', 'Unknown error')}")
                with c2:
                    if st.button("Cancel", key=f"cancel_{post_id}"):
                        st.session_state["publish_confirm"] = None
                        st.rerun()
            else:
                if st.button("Publish Now", key=f"pub_{post_id}", type="primary", use_container_width=True):
                    st.session_state["publish_confirm"] = post_id
                    st.rerun()

            # Option to send back to review
            if st.button("Back to Review", key=f"back_{post_id}"):
                update_post_status(post_id, "review")
                st.rerun()
