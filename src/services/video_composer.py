"""
Video + audio compositing via FFmpeg.
Merges generated video with generated music into a final MP4.
"""
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
