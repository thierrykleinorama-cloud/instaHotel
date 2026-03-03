"""
View 13 — Carousel Builder (AI Lab)
Build multi-image carousel posts for Instagram.
"""
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.ui import sidebar_css, page_title
from src.services.media_queries import fetch_all_media, fetch_media_by_id, fetch_distinct_values
from src.services.google_drive import download_file_bytes
from src.services.carousel_queries import (
    save_carousel_draft,
    fetch_carousel_drafts,
    update_carousel_status,
    delete_carousel_draft,
)
from src.services.publisher import publish_carousel, upload_to_supabase_storage


@st.cache_data(ttl=300)
def _download_thumb(drive_file_id: str) -> bytes:
    return download_file_bytes(drive_file_id)


sidebar_css()
page_title("Carousel Builder", "Multi-image Instagram carousel posts")

st.page_link("pages/5_AI_Lab.py", label="Back to AI Lab", icon=":material/arrow_back:")

# --- Sidebar filters (same pattern as media_selector) ---
with st.sidebar:
    st.subheader("Find Images")

    categories = fetch_distinct_values("category")
    sel_cats = st.multiselect("Category", categories, key="cb_cat")

    min_q = st.slider("Min quality", 1, 10, 5, key="cb_minq")
    search = st.text_input("Search filename", key="cb_search")

all_media = fetch_all_media(media_type="image")
if sel_cats:
    all_media = [m for m in all_media if m.get("category") in sel_cats]
all_media = [m for m in all_media if (m.get("ig_quality") or 0) >= min_q]
if search:
    all_media = [m for m in all_media if search.lower() in m.get("file_name", "").lower()]

# --- Initialize session state ---
if "cb_selected_ids" not in st.session_state:
    st.session_state["cb_selected_ids"] = []

selected_ids: list[str] = st.session_state["cb_selected_ids"]

# --- Image picker gallery ---
st.markdown("### 1. Select Images (2-10)")
st.caption(f"{len(all_media)} images match filters | {len(selected_ids)} selected")

# Display as grid with checkboxes
COLS = 5
rows = [all_media[i:i + COLS] for i in range(0, len(all_media), COLS)]

for row_items in rows:
    cols = st.columns(COLS)
    for idx, m in enumerate(row_items):
        with cols[idx]:
            is_selected = m["id"] in selected_ids
            # Show selection number if selected
            label = f"**#{selected_ids.index(m['id']) + 1}**" if is_selected else ""

            if m.get("thumbnail_url"):
                st.image(m["thumbnail_url"], width=120)
            else:
                st.caption(m.get("file_name", "?")[:20])

            if label:
                st.markdown(label)

            cb = st.checkbox(
                m.get("file_name", "?")[:18],
                value=is_selected,
                key=f"cb_sel_{m['id']}",
            )
            if cb and m["id"] not in selected_ids:
                if len(selected_ids) < 10:
                    selected_ids.append(m["id"])
                    st.rerun()
            elif not cb and m["id"] in selected_ids:
                selected_ids.remove(m["id"])
                st.rerun()

st.divider()

# --- Selected images with reorder ---
st.markdown("### 2. Selected Images & Order")

if not selected_ids:
    st.info("Select at least 2 images from the gallery above.")
elif len(selected_ids) < 2:
    st.warning("Carousel requires at least 2 images. Select one more.")
else:
    # Show selected images as numbered strip
    n_selected = len(selected_ids)
    strip_cols = st.columns(min(n_selected, 6))

    for i, mid in enumerate(selected_ids):
        col_idx = i % min(n_selected, 6)
        with strip_cols[col_idx]:
            m = fetch_media_by_id(mid)
            if m:
                try:
                    thumb = _download_thumb(m["drive_file_id"])
                    st.image(thumb, width=100)
                except Exception:
                    st.caption(m.get("file_name", "?")[:15])
            st.caption(f"**#{i + 1}** {(m or {}).get('file_name', '?')[:12]}")

            # Reorder buttons
            bc1, bc2, bc3 = st.columns(3)
            with bc1:
                if i > 0 and st.button(":material/arrow_upward:", key=f"cb_up_{mid}"):
                    selected_ids[i], selected_ids[i - 1] = selected_ids[i - 1], selected_ids[i]
                    st.rerun()
            with bc2:
                if i < n_selected - 1 and st.button(":material/arrow_downward:", key=f"cb_dn_{mid}"):
                    selected_ids[i], selected_ids[i + 1] = selected_ids[i + 1], selected_ids[i]
                    st.rerun()
            with bc3:
                if st.button(":material/close:", key=f"cb_rm_{mid}"):
                    selected_ids.remove(mid)
                    st.rerun()

    st.divider()

    # --- Preview with dots ---
    st.markdown("### 3. Preview")

    # Render a simple carousel preview
    from app.components.ig_preview import render_ig_preview_carousel

    # Load first image for preview
    first_media = fetch_media_by_id(selected_ids[0])
    if first_media and first_media.get("drive_file_id"):
        try:
            import base64
            first_bytes = _download_thumb(first_media["drive_file_id"])
            first_b64 = base64.b64encode(first_bytes).decode()

            # Load all images b64 for carousel preview
            all_b64 = []
            for mid in selected_ids:
                m = fetch_media_by_id(mid)
                if m and m.get("drive_file_id"):
                    try:
                        b = _download_thumb(m["drive_file_id"])
                        all_b64.append(base64.b64encode(b).decode())
                    except Exception:
                        pass

            caption_text = st.session_state.get("cb_caption_es", "")
            hashtags_text = " ".join(f"#{h}" for h in st.session_state.get("cb_hashtags_list", []))

            html, height = render_ig_preview_carousel(
                images_b64=all_b64,
                caption=caption_text,
                hashtags=hashtags_text,
            )
            st.components.v1.html(html, height=height)
        except Exception as e:
            st.warning(f"Preview unavailable: {e}")

    st.divider()

    # --- Captions ---
    st.markdown("### 4. Captions & Hashtags")

    cap_es = st.text_area("Caption (ES)", height=100, key="cb_caption_es",
                          placeholder="Caption en espa\u00f1ol...")
    cap_en = st.text_area("Caption (EN)", height=100, key="cb_caption_en",
                          placeholder="English caption...")
    cap_fr = st.text_area("Caption (FR)", height=100, key="cb_caption_fr",
                          placeholder="L\u00e9gende en fran\u00e7ais...")

    hashtags_str = st.text_input(
        "Hashtags (comma-separated)",
        key="cb_hashtags",
        placeholder="sitges, hotel, mediterranean",
    )
    hashtags_list = [h.strip().lstrip("#") for h in hashtags_str.split(",") if h.strip()]
    st.session_state["cb_hashtags_list"] = hashtags_list

    if hashtags_list:
        st.caption(" ".join(f"#{h}" for h in hashtags_list))

    st.divider()

    # --- Actions ---
    st.markdown("### 5. Save & Publish")

    title = st.text_input("Carousel title (internal)", key="cb_title",
                          placeholder="e.g., 'Top 5 Sitges Beaches'")

    ac1, ac2 = st.columns(2)

    with ac1:
        if st.button("Save Draft", type="primary", key="cb_save",
                      disabled=len(selected_ids) < 2):
            draft_id = save_carousel_draft(
                title=title or "Untitled Carousel",
                media_ids=selected_ids,
                caption_es=cap_es,
                caption_en=cap_en,
                caption_fr=cap_fr,
                hashtags=hashtags_list,
            )
            if draft_id:
                st.success(f"Draft saved! ID: {draft_id[:8]}...")
            else:
                st.error("Failed to save draft.")

    with ac2:
        if st.button("Publish to Instagram", key="cb_publish",
                      disabled=len(selected_ids) < 2):
            # Confirmation step
            st.session_state["cb_confirm_publish"] = True

    if st.session_state.get("cb_confirm_publish"):
        st.warning("This will publish the carousel to Instagram immediately.")
        cp1, cp2 = st.columns(2)
        with cp1:
            if st.button("Confirm Publish", type="primary", key="cb_confirm_yes"):
                st.session_state.pop("cb_confirm_publish", None)
                with st.spinner("Publishing carousel to Instagram..."):
                    try:
                        # Upload each image to Supabase Storage
                        image_urls = []
                        for mid in selected_ids:
                            m = fetch_media_by_id(mid)
                            if m and m.get("drive_file_id"):
                                img_bytes = _download_thumb(m["drive_file_id"])
                                url = upload_to_supabase_storage(
                                    img_bytes,
                                    f"carousel_{mid[:8]}.jpg",
                                    "image/jpeg",
                                )
                                image_urls.append(url)

                        # Build caption (stacked multilingual)
                        caption_parts = []
                        if cap_es:
                            caption_parts.append(cap_es)
                        if cap_en:
                            caption_parts.append(f"\U0001f1ec\U0001f1e7\n{cap_en}")
                        if cap_fr:
                            caption_parts.append(f"\U0001f1eb\U0001f1f7\n{cap_fr}")
                        full_caption = "\n\n".join(caption_parts)
                        if hashtags_list:
                            full_caption += "\n\n" + " ".join(f"#{h}" for h in hashtags_list)

                        result = publish_carousel(
                            image_urls=image_urls,
                            caption=full_caption,
                        )

                        if result.get("success"):
                            st.success(f"Published! Post ID: {result.get('ig_post_id')}")
                            if result.get("ig_permalink"):
                                st.markdown(f"[View on Instagram]({result['ig_permalink']})")
                        else:
                            st.error(f"Publish failed: {result.get('error')}")
                    except Exception as e:
                        st.error(f"Publish failed: {e}")
        with cp2:
            if st.button("Cancel", key="cb_confirm_no"):
                st.session_state.pop("cb_confirm_publish", None)
                st.rerun()

# --- Saved drafts list ---
st.divider()
st.markdown("### Saved Drafts")

draft_status = st.selectbox("Filter", ["draft", "validated", "published", "all"], key="cb_draft_filter")
drafts = fetch_carousel_drafts(status=draft_status)

if not drafts:
    st.caption("No carousel drafts found.")
else:
    for d in drafts:
        _status_colors = {"draft": "blue", "validated": "orange", "published": "green"}
        _color = _status_colors.get(d["status"], "gray")
        with st.expander(
            f":{_color}[{d['status'].upper()}] {d.get('title', 'Untitled')} "
            f"({len(d.get('media_ids', []))} images) — {d.get('created_at', '?')[:16]}"
        ):
            st.caption(f"ID: {d['id'][:12]}...")
            n_images = len(d.get("media_ids", []))
            st.caption(f"Images: {n_images}")
            if d.get("caption_es"):
                st.text(d["caption_es"][:200])
            if d.get("hashtags"):
                st.caption(" ".join(f"#{h}" for h in d["hashtags"]))
            if d.get("ig_permalink"):
                st.markdown(f"[View on Instagram]({d['ig_permalink']})")

            dc1, dc2 = st.columns(2)
            with dc1:
                if d["status"] == "draft":
                    if st.button("Load into editor", key=f"cb_load_{d['id']}"):
                        st.session_state["cb_selected_ids"] = d.get("media_ids", [])
                        st.session_state["cb_caption_es"] = d.get("caption_es", "")
                        st.session_state["cb_caption_en"] = d.get("caption_en", "")
                        st.session_state["cb_caption_fr"] = d.get("caption_fr", "")
                        st.session_state["cb_title"] = d.get("title", "")
                        ht = d.get("hashtags", [])
                        st.session_state["cb_hashtags"] = ", ".join(ht) if ht else ""
                        st.rerun()
            with dc2:
                if d["status"] == "draft":
                    if st.button("Delete", key=f"cb_del_{d['id']}"):
                        delete_carousel_draft(d["id"])
                        st.rerun()
