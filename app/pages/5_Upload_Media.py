"""
Upload Media — add new images/videos to the library.

Uploads to Google Drive (main folder), runs Claude Vision analysis,
and inserts into media_library. Duplicate detection: filename + file_size.
"""
import sys
from datetime import datetime
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

import streamlit as st

from app.components.ui import sidebar_css, page_title
from src.services.google_drive import (
    upload_to_main_folder,
    IMAGE_MIMES,
    VIDEO_MIMES,
)
from src.services.media_indexer import process_image_bytes, process_video_bytes
from src.services.media_queries import (
    find_duplicate_by_name_size,
    find_any_with_filename,
)

sidebar_css()
page_title("Upload Media", "Add new photos or videos to the library")

IMAGE_EXTS = ["jpg", "jpeg", "png", "gif", "bmp", "webp", "tiff", "tif", "heic", "heif"]
VIDEO_EXTS = ["mp4", "mov", "avi", "mkv", "webm", "mpeg", "mpg", "3gp"]
ALL_EXTS = IMAGE_EXTS + VIDEO_EXTS


def _guess_mime(filename: str, browser_mime: str) -> str:
    """Return a MIME type supported by the indexer. Browsers sometimes send
    empty/wrong MIME for HEIC/MOV — fall back to extension."""
    if browser_mime and (browser_mime in IMAGE_MIMES or browser_mime in VIDEO_MIMES):
        return browser_mime
    ext = Path(filename).suffix.lower().lstrip(".")
    ext_to_mime = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
        "gif": "image/gif", "bmp": "image/bmp", "webp": "image/webp",
        "tiff": "image/tiff", "tif": "image/tiff",
        "heic": "image/heic", "heif": "image/heif",
        "mp4": "video/mp4", "mov": "video/quicktime", "avi": "video/x-msvideo",
        "mkv": "video/x-matroska", "webm": "video/webm",
        "mpeg": "video/mpeg", "mpg": "video/mpeg", "3gp": "video/3gpp",
    }
    return ext_to_mime.get(ext, browser_mime or "application/octet-stream")


def _media_type_for(mime: str) -> str | None:
    if mime in IMAGE_MIMES:
        return "image"
    if mime in VIDEO_MIMES:
        return "video"
    return None


def _rename_on_collision(filename: str) -> str:
    """Append a timestamp suffix before the extension."""
    p = Path(filename)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{p.stem}_{ts}{p.suffix}"


st.markdown(
    "Select one or more files. Each file will be uploaded to Google Drive "
    "and analyzed with Claude Vision (tags, category, quality score, description). "
    "Duplicate detection uses filename + file size."
)

uploaded = st.file_uploader(
    "Drop files here",
    type=ALL_EXTS,
    accept_multiple_files=True,
    key="upload_media_files",
)

if not uploaded:
    st.info("No files selected yet. Supported: images (JPEG, PNG, HEIC, WEBP...) and videos (MP4, MOV, MKV...).")
    st.stop()

st.caption(f"{len(uploaded)} file(s) ready to process")

if not st.button("Analyze & add to library", type="primary", key="upload_go"):
    st.stop()

results_container = st.container()
progress = st.progress(0.0, text="Starting...")

summary = {"added": 0, "skipped_dup": 0, "renamed": 0, "errors": 0}

for i, f in enumerate(uploaded, 1):
    filename = f.name
    raw_bytes = f.getvalue()
    size = len(raw_bytes)
    browser_mime = f.type or ""
    mime = _guess_mime(filename, browser_mime)
    kind = _media_type_for(mime)

    progress.progress((i - 1) / len(uploaded), text=f"[{i}/{len(uploaded)}] {filename}")

    with results_container:
        with st.status(f"Processing `{filename}` ({size // 1024} KB)", expanded=True) as status:
            if kind is None:
                st.error(f"Unsupported file type: `{mime}`")
                summary["errors"] += 1
                status.update(label=f"Skipped `{filename}` — unsupported", state="error")
                continue

            # Duplicate check
            dup = find_duplicate_by_name_size(filename, size)
            if dup:
                analyzed = dup.get("analyzed_at") or "unknown date"
                st.warning(
                    f"Skipped `{filename}` — already in your library "
                    f"(uploaded {analyzed}, identical file size)."
                )
                summary["skipped_dup"] += 1
                status.update(label=f"Skipped `{filename}` — duplicate", state="complete")
                continue

            # Rename if filename collision (different size)
            final_name = filename
            if find_any_with_filename(filename):
                final_name = _rename_on_collision(filename)
                st.info(
                    f"A different file named `{filename}` already exists. "
                    f"Uploading as `{final_name}`."
                )
                summary["renamed"] += 1

            # Upload to Drive
            try:
                st.write("Uploading to Google Drive...")
                drive_file = upload_to_main_folder(raw_bytes, final_name, mime)
                drive_id = drive_file["id"]
            except Exception as e:
                st.error(f"Drive upload failed: {e}")
                summary["errors"] += 1
                status.update(label=f"Drive upload failed: `{filename}`", state="error")
                continue

            # Analyze
            try:
                if kind == "image":
                    st.write("Analyzing image with Claude Vision...")
                    row = process_image_bytes(raw_bytes, final_name, mime, drive_id, size)
                else:
                    st.write("Detecting scenes + analyzing video with Claude Vision (this may take 30–60s)...")
                    row = process_video_bytes(raw_bytes, final_name, mime, drive_id, size)
            except Exception as e:
                st.error(f"Analysis failed: {e}")
                summary["errors"] += 1
                status.update(label=f"Analysis failed: `{filename}`", state="error")
                continue

            # Show result
            col_img, col_meta = st.columns([1, 2])
            with col_img:
                if kind == "image":
                    st.image(raw_bytes, use_container_width=True)
                else:
                    st.video(raw_bytes)
            with col_meta:
                st.markdown(f"**Added** `{final_name}`")
                st.markdown(f"- **Category**: {row.get('category')} / {row.get('subcategory')}")
                st.markdown(f"- **Quality**: {row.get('ig_quality')}/10")
                amb = row.get("ambiance") or []
                if amb:
                    st.markdown(f"- **Ambiance**: {', '.join(amb)}")
                seas = row.get("season") or []
                if seas:
                    st.markdown(f"- **Season**: {', '.join(seas)}")
                if row.get("description_en"):
                    st.markdown(f"- **Description**: {row['description_en']}")

            summary["added"] += 1
            status.update(label=f"Added `{final_name}` ({row.get('category')}, quality {row.get('ig_quality')}/10)", state="complete")

progress.progress(1.0, text="Done")

st.divider()
st.subheader("Summary")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Added", summary["added"])
c2.metric("Skipped (duplicate)", summary["skipped_dup"])
c3.metric("Renamed (name conflict)", summary["renamed"])
c4.metric("Errors", summary["errors"])

if summary["added"] > 0:
    st.cache_data.clear()
    st.success("Gallery cache cleared. New media will appear in Gallery and Stats.")
