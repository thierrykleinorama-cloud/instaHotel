"""
Video + audio compositing via FFmpeg.
Merges generated video with generated music into a final MP4.
Also: images_to_slideshow() — Ken Burns slideshow from a list of images.
"""
import io
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def _find_ffmpeg() -> str:
    """Find ffmpeg executable. Checks PATH first, then known Windows location."""
    ff = shutil.which("ffmpeg")
    if ff:
        return ff
    # Known Windows location (ImageMagick bundle)
    win_path = r"C:\Program Files\ImageMagick-7.0.10-Q16-HDRI\ffmpeg.exe"
    if os.path.isfile(win_path):
        return win_path
    raise FileNotFoundError(
        "FFmpeg not found. Install it or add it to PATH. "
        "On Streamlit Cloud, add 'ffmpeg' to packages.txt."
    )


def get_video_duration(video_bytes: bytes) -> float:
    """Get video duration in seconds using cv2 (no ffprobe needed)."""
    try:
        import cv2
        import numpy as np
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.write(video_bytes)
        tmp.close()
        cap = cv2.VideoCapture(tmp.name)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        os.unlink(tmp.name)
        return frames / fps if fps > 0 else 0
    except ImportError:
        # Fallback: assume duration from file if cv2 not available
        return 0


def images_to_slideshow(
    image_bytes_list: list[bytes],
    duration_per_slide: float = 3.0,
    aspect_ratio: str = "9:16",
    fps: int = 30,
) -> dict:
    """Convert a list of images to a video slideshow with subtle Ken Burns zoom.

    Args:
        image_bytes_list: list of raw image bytes (JPEG, PNG, HEIC all accepted)
        duration_per_slide: seconds each slide is shown
        aspect_ratio: '9:16' (Reel, 1080x1920) or '4:5' (Feed, 1080x1350)
        fps: output frame rate

    Returns: {video_bytes, duration_sec, _cost}
    """
    from PIL import Image
    try:
        from pillow_heif import register_heif_opener
        register_heif_opener()
    except ImportError:
        pass

    if len(image_bytes_list) < 2:
        raise ValueError("Need at least 2 images for a slideshow")

    ffmpeg = _find_ffmpeg()

    # Target dimensions
    if aspect_ratio == "4:5":
        w, h = 1080, 1350
    else:
        w, h = 1080, 1920

    total_frames = int(duration_per_slide * fps)
    total_duration = len(image_bytes_list) * duration_per_slide

    tmpdir = tempfile.mkdtemp(prefix="slideshow_")
    segment_paths = []

    try:
        # --- Step 1: Prepare JPEG images at target size ---
        img_paths = []
        for i, raw in enumerate(image_bytes_list):
            img = Image.open(io.BytesIO(raw))
            if img.mode != "RGB":
                img = img.convert("RGB")
            # Resize covering target (crop to fill)
            scale = max(w / img.width, h / img.height)
            new_w, new_h = int(img.width * scale), int(img.height * scale)
            img = img.resize((new_w, new_h), Image.LANCZOS)
            # Center crop
            left = (new_w - w) // 2
            top = (new_h - h) // 2
            img = img.crop((left, top, left + w, top + h))
            path = os.path.join(tmpdir, f"slide_{i:03d}.jpg")
            img.save(path, "JPEG", quality=90)
            img_paths.append(path)

        # --- Step 2: Generate video segment per image with zoompan ---
        for i, img_path in enumerate(img_paths):
            seg_path = os.path.join(tmpdir, f"seg_{i:03d}.mp4")
            segment_paths.append(seg_path)

            # Subtle Ken Burns: zoom from 1.0 to ~1.04 over the slide duration
            # zoompan: z increments per frame, d=total frames, s=output size
            zoom_increment = 0.04 / total_frames  # total 4% zoom
            vf = (
                f"zoompan=z='min(zoom+{zoom_increment:.8f},1.04)'"
                f":d={total_frames}:s={w}x{h}:fps={fps}"
            )

            cmd = [
                ffmpeg,
                "-loop", "1",
                "-i", img_path,
                "-vf", vf,
                "-t", str(duration_per_slide),
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-r", str(fps),
                "-y",
                seg_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg zoompan failed for slide {i}: {result.stderr[:300]}"
                )

        # --- Step 3: Concat all segments ---
        concat_list = os.path.join(tmpdir, "concat.txt")
        with open(concat_list, "w") as f:
            for sp in segment_paths:
                # Use forward slashes for FFmpeg compatibility
                f.write(f"file '{sp.replace(os.sep, '/')}'\n")

        output_path = os.path.join(tmpdir, "slideshow.mp4")
        cmd = [
            ffmpeg,
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list,
            "-c", "copy",
            "-y",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg concat failed: {result.stderr[:300]}")

        with open(output_path, "rb") as f:
            video_bytes = f.read()

        # Log cost (free — local FFmpeg)
        try:
            from src.services.cost_tracker import log_cost
            log_cost("ffmpeg", "images_to_slideshow", 0.0,
                     params={"slides": len(image_bytes_list),
                             "duration_per_slide": duration_per_slide,
                             "aspect_ratio": aspect_ratio})
        except Exception:
            pass

        return {
            "video_bytes": video_bytes,
            "duration_sec": total_duration,
            "_cost": {"operation": "images_to_slideshow", "cost_usd": 0.0},
        }

    finally:
        # Cleanup temp directory
        shutil.rmtree(tmpdir, ignore_errors=True)


def composite_video_audio(
    video_bytes: bytes,
    audio_bytes: bytes,
    volume: float = 0.3,
    fade_out_sec: float = 1.5,
    audio_format: str = "wav",
) -> dict:
    """Merge video + audio into a single MP4 with AAC audio.

    Args:
        video_bytes: MP4 video data
        audio_bytes: WAV/MP3 audio data
        volume: audio volume (0.0-1.0), default 0.3 for subtle background
        fade_out_sec: fade out audio N seconds before video ends
        audio_format: input audio format hint

    Returns: {video_bytes, duration_sec, _cost}
    """
    ffmpeg = _find_ffmpeg()

    # Write inputs to temp files
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as vf:
        vf.write(video_bytes)
        video_path = vf.name

    audio_ext = ".wav" if audio_format == "wav" else ".mp3"
    with tempfile.NamedTemporaryFile(suffix=audio_ext, delete=False) as af:
        af.write(audio_bytes)
        audio_path = af.name

    output_path = tempfile.mktemp(suffix=".mp4")

    try:
        # Get video duration for fade calculation
        video_duration = get_video_duration(video_bytes)

        # Build audio filter: volume + optional fade out
        audio_filters = [f"volume={volume}"]
        if video_duration > 0 and fade_out_sec > 0:
            fade_start = max(0, video_duration - fade_out_sec)
            audio_filters.append(f"afade=t=out:st={fade_start:.1f}:d={fade_out_sec:.1f}")

        filter_str = ",".join(audio_filters)

        cmd = [
            ffmpeg,
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex", f"[1:a]{filter_str}[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",        # Don't re-encode video
            "-c:a", "aac",         # Encode audio as AAC
            "-b:a", "192k",
            "-shortest",           # Match shortest stream
            "-y",                  # Overwrite output
            output_path,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg failed: {result.stderr[:500]}")

        with open(output_path, "rb") as f:
            output_bytes = f.read()

        return {
            "video_bytes": output_bytes,
            "duration_sec": video_duration,
            "_cost": {"operation": "video_composite", "cost_usd": 0.0},
        }

    finally:
        # Cleanup temp files
        for p in [video_path, audio_path, output_path]:
            try:
                os.unlink(p)
            except OSError:
                pass
