"""
Shared "Publish to Instagram" widget for AI Lab pages.
Handles caption input, confirmation, upload, and IG Graph API publishing.
"""
import os
from datetime import datetime

import streamlit as st

from src.services.publisher import (
    upload_to_supabase_storage,
    create_ig_container,
    poll_container_status,
    publish_container,
    publish_carousel,
    get_post_permalink,
    delete_from_supabase_storage,
    SUPABASE_STORAGE_BUCKET,
)


def _has_ig_credentials() -> bool:
    """Check if Instagram credentials are configured."""
    try:
        import streamlit as _st
        if "INSTAGRAM_ACCESS_TOKEN" in _st.secrets and "INSTAGRAM_ACCOUNT_ID" in _st.secrets:
            return True
    except Exception:
        pass
    return bool(
        os.getenv("INSTAGRAM_ACCESS_TOKEN") and os.getenv("INSTAGRAM_ACCOUNT_ID")
    )


def render_publish_to_ig(
    media_bytes: bytes,
    media_type: str,
    filename: str,
    mime_type: str,
    key_prefix: str,
    default_caption: str = "",
    default_hashtags: str = "",
):
    """Render a 'Publish to Instagram' section with caption input and confirmation.

    Args:
        media_bytes: Raw file bytes (video or image).
        media_type: "REELS" or "IMAGE".
        filename: Filename for Supabase upload (e.g. "veo_reel_20260311.mp4").
        mime_type: MIME type (e.g. "video/mp4", "image/jpeg").
        key_prefix: Unique prefix for Streamlit widget keys.
        default_caption: Pre-fill caption text.
        default_hashtags: Pre-fill hashtags (space-separated #tags or comma-separated words).
    """
    st.markdown("---")
    st.markdown("### Publish to Instagram")

    if not _has_ig_credentials():
        st.warning(
            "Configure `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_ACCOUNT_ID` in `.env` "
            "to enable direct publishing."
        )
        return

    # Caption + hashtags inputs
    caption = st.text_area(
        "Caption",
        value=default_caption,
        height=100,
        key=f"{key_prefix}_ig_caption",
        placeholder="Write your Instagram caption...",
    )
    hashtags = st.text_input(
        "Hashtags",
        value=default_hashtags,
        key=f"{key_prefix}_ig_hashtags",
        placeholder="#sitges #hotel #mediterranean",
    )

    # Build full caption
    full_caption = caption.strip()
    if hashtags.strip():
        full_caption += "\n\n" + hashtags.strip()

    # Publish button
    confirm_key = f"{key_prefix}_ig_confirm"
    if st.button(
        "Publish to Instagram",
        key=f"{key_prefix}_ig_publish_btn",
        disabled=not full_caption,
    ):
        st.session_state[confirm_key] = True

    # Confirmation step
    if st.session_state.get(confirm_key):
        st.warning("This will publish to Instagram immediately. Are you sure?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm Publish", type="primary", key=f"{key_prefix}_ig_yes"):
                st.session_state.pop(confirm_key, None)
                _do_publish(media_bytes, media_type, filename, mime_type, full_caption, key_prefix)
        with c2:
            if st.button("Cancel", key=f"{key_prefix}_ig_no"):
                st.session_state.pop(confirm_key, None)
                st.rerun()


def _do_publish(
    media_bytes: bytes,
    media_type: str,
    filename: str,
    mime_type: str,
    caption: str,
    key_prefix: str,
):
    """Execute the upload → create container → poll → publish flow."""
    storage_filename = None

    with st.spinner("Publishing to Instagram..."):
        try:
            # 1. Get credentials
            token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
            account_id = os.getenv("INSTAGRAM_ACCOUNT_ID", "")
            try:
                import streamlit as _st
                token = _st.secrets.get("INSTAGRAM_ACCESS_TOKEN", token)
                account_id = _st.secrets.get("INSTAGRAM_ACCOUNT_ID", account_id)
            except Exception:
                pass

            # 2. Upload to Supabase Storage
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            upload_name = f"publish_{ts}_{filename}"
            public_url = upload_to_supabase_storage(media_bytes, upload_name, mime_type)
            storage_filename = public_url.split(f"{SUPABASE_STORAGE_BUCKET}/")[-1]

            # 3. Create IG container
            container_id = create_ig_container(
                account_id=account_id,
                token=token,
                media_url=public_url,
                caption=caption,
                media_type=media_type,
            )

            # 4. Poll until ready (videos need longer)
            max_wait = 180 if media_type == "REELS" else 60
            poll_container_status(container_id, token, max_wait=max_wait)

            # 5. Publish
            result = publish_container(account_id, token, container_id)
            ig_post_id = result.get("id", "")

            # 6. Get permalink
            permalink = get_post_permalink(ig_post_id, token) if ig_post_id else None

            st.success(f"Published to Instagram! Post ID: {ig_post_id}")
            if permalink:
                st.markdown(f"[View on Instagram]({permalink})")

        except Exception as e:
            st.error(f"Publish failed: {e}")

        finally:
            # Cleanup temp file from Storage
            if storage_filename:
                try:
                    delete_from_supabase_storage(storage_filename)
                except Exception:
                    pass


def render_publish_carousel_to_ig(
    image_bytes_list: list[bytes],
    key_prefix: str,
    default_caption: str = "",
    default_hashtags: str = "",
):
    """Render a 'Publish Carousel to Instagram' section.

    Uses the multi-child container flow: upload N images → create N children →
    create carousel parent → poll → publish.

    Args:
        image_bytes_list: List of JPEG image bytes (2-10 images, already converted).
        key_prefix: Unique prefix for Streamlit widget keys.
        default_caption: Pre-fill caption text.
        default_hashtags: Pre-fill hashtags.
    """
    st.markdown("---")
    st.markdown("### Publish Carousel to Instagram")

    if not _has_ig_credentials():
        st.warning(
            "Configure `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_ACCOUNT_ID` in `.env` "
            "to enable direct publishing."
        )
        return

    n_images = len(image_bytes_list)
    if n_images < 2:
        st.info(f"Need at least 2 images for a carousel (currently {n_images}).")
        return
    if n_images > 10:
        st.warning(f"Instagram carousels support at most 10 images ({n_images} selected).")
        return

    st.caption(f"{n_images} images selected")

    # Caption + hashtags inputs
    caption = st.text_area(
        "Caption",
        value=default_caption,
        height=100,
        key=f"{key_prefix}_ig_caption",
        placeholder="Write your Instagram caption...",
    )
    hashtags = st.text_input(
        "Hashtags",
        value=default_hashtags,
        key=f"{key_prefix}_ig_hashtags",
        placeholder="#sitges #hotel #mediterranean",
    )

    full_caption = caption.strip()
    if hashtags.strip():
        full_caption += "\n\n" + hashtags.strip()

    confirm_key = f"{key_prefix}_ig_confirm"
    if st.button(
        "Publish Carousel to Instagram",
        key=f"{key_prefix}_ig_publish_btn",
        disabled=not full_caption,
    ):
        st.session_state[confirm_key] = True

    if st.session_state.get(confirm_key):
        st.warning("This will publish the carousel to Instagram immediately.")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm Publish", type="primary", key=f"{key_prefix}_ig_yes"):
                st.session_state.pop(confirm_key, None)
                _do_carousel_publish(image_bytes_list, full_caption, key_prefix)
        with c2:
            if st.button("Cancel", key=f"{key_prefix}_ig_no"):
                st.session_state.pop(confirm_key, None)
                st.rerun()


def _do_carousel_publish(
    image_bytes_list: list[bytes],
    caption: str,
    key_prefix: str,
):
    """Upload images to Supabase Storage, then publish as carousel via IG Graph API."""
    uploaded_filenames: list[str] = []

    with st.spinner(f"Publishing carousel ({len(image_bytes_list)} images) to Instagram..."):
        try:
            # 1. Upload all images to Supabase Storage
            image_urls = []
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            for i, img_bytes in enumerate(image_bytes_list):
                upload_name = f"carousel_{ts}_{i}.jpg"
                url = upload_to_supabase_storage(img_bytes, upload_name, "image/jpeg")
                image_urls.append(url)
                uploaded_filenames.append(
                    url.split(f"{SUPABASE_STORAGE_BUCKET}/")[-1]
                )

            # 2. Publish carousel (children → parent → poll → publish)
            result = publish_carousel(
                image_urls=image_urls,
                caption=caption,
            )

            if result.get("success"):
                st.success(f"Carousel published! Post ID: {result.get('ig_post_id')}")
                if result.get("ig_permalink"):
                    st.markdown(f"[View on Instagram]({result['ig_permalink']})")
            else:
                st.error(f"Publish failed: {result.get('error')}")

        except Exception as e:
            st.error(f"Publish failed: {e}")

        finally:
            # Cleanup temp images from Storage
            for fname in uploaded_filenames:
                try:
                    delete_from_supabase_storage(fname)
                except Exception:
                    pass
