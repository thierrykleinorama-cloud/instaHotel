"""
Video analyzer — scene detection via OpenCV histogram diff, keyframe extraction,
and per-scene Claude Vision analysis.
"""
import os
import tempfile
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from src.models import VisionAnalysis, SceneAnalysis
from src.utils import encode_cv2_frame, get_aspect_ratio_from_dimensions
from src.services.vision_analyzer import analyze_frames, _parse_json_response

# Scene detection: histogram difference threshold (0-1, higher = fewer scenes)
SCENE_THRESHOLD = 0.4
# Sample rate for scene detection (check every N seconds)
SCENE_SAMPLE_INTERVAL = 0.5
# Frame extraction: 1 frame every N seconds within a scene
FRAME_EXTRACT_INTERVAL = 5.0
# Max frames per scene to send to Claude
MAX_FRAMES_PER_SCENE = 5


def _compute_histogram(frame) -> np.ndarray:
    """Compute normalized color histogram for a frame."""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
    cv2.normalize(hist, hist)
    return hist.flatten()


def detect_scenes(video_path: str) -> list[tuple[float, float]]:
    """
    Detect scene boundaries using color histogram differences.
    Returns list of (start_sec, end_sec) tuples.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps

    sample_interval_frames = int(fps * SCENE_SAMPLE_INTERVAL)
    if sample_interval_frames < 1:
        sample_interval_frames = 1

    prev_hist = None
    scene_boundaries = [0.0]  # always start at 0

    frame_idx = 0
    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        hist = _compute_histogram(frame)
        if prev_hist is not None:
            diff = cv2.compareHist(
                prev_hist.reshape(-1, 1).astype(np.float32),
                hist.reshape(-1, 1).astype(np.float32),
                cv2.HISTCMP_BHATTACHARYYA,
            )
            if diff > SCENE_THRESHOLD:
                timestamp = frame_idx / fps
                # Avoid very short scenes (< 2s)
                if timestamp - scene_boundaries[-1] >= 2.0:
                    scene_boundaries.append(timestamp)

        prev_hist = hist
        frame_idx += sample_interval_frames

    cap.release()

    # Build (start, end) pairs
    scene_boundaries.append(duration)
    scenes = []
    for i in range(len(scene_boundaries) - 1):
        scenes.append((scene_boundaries[i], scene_boundaries[i + 1]))

    return scenes


def extract_scene_frames(
    video_path: str,
    start_sec: float,
    end_sec: float,
) -> list[np.ndarray]:
    """Extract frames from a scene at regular intervals. Min 1 frame per scene."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    frames = []
    t = start_sec
    while t < end_sec and len(frames) < MAX_FRAMES_PER_SCENE:
        frame_idx = int(t * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)
        t += FRAME_EXTRACT_INTERVAL

    # Ensure at least 1 frame
    if not frames:
        mid = int((start_sec + end_sec) / 2 * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, mid)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)

    cap.release()
    return frames


def get_video_metadata(video_path: str) -> dict:
    """Extract video metadata: duration, resolution, fps."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    cap.release()

    return {
        "duration_seconds": round(duration, 2),
        "width": width,
        "height": height,
        "fps": round(fps, 2),
        "total_frames": total_frames,
        "aspect_ratio": get_aspect_ratio_from_dimensions(width, height),
    }


def analyze_video(video_bytes: bytes, file_name: str = "") -> dict:
    """
    Full video analysis pipeline:
    1. Save to temp file
    2. Detect scenes
    3. Extract frames per scene
    4. Claude Vision call per scene
    5. Return aggregated results

    Returns dict with: scenes, category, subcategory, ambiance, elements,
    season, ig_quality, description_fr, duration_seconds, aspect_ratio,
    analysis_raw, analysis_model
    """
    # Save to temp file
    suffix = ".mp4"
    if file_name:
        ext = Path(file_name).suffix
        if ext:
            suffix = ext

    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(video_bytes)
    tmp.close()
    tmp_path = tmp.name

    try:
        # Get metadata
        meta = get_video_metadata(tmp_path)

        # Detect scenes
        scenes = detect_scenes(tmp_path)

        # Analyze each scene
        scene_results = []
        all_raw = []

        for idx, (start, end) in enumerate(scenes):
            frames = extract_scene_frames(tmp_path, start, end)
            if not frames:
                continue

            frames_b64 = [encode_cv2_frame(f) for f in frames]
            context = f"Scène {idx + 1}/{len(scenes)} d'une vidéo de l'hôtel ({file_name}). Durée de la scène: {end - start:.1f}s."

            try:
                analysis = analyze_frames(frames_b64, context=context)
                scene_data = {
                    "scene_index": idx,
                    "start_sec": round(start, 2),
                    "end_sec": round(end, 2),
                    "frame_count": len(frames),
                    "category": analysis.category,
                    "subcategory": analysis.subcategory,
                    "ambiance": analysis.ambiance,
                    "elements": analysis.elements,
                    "description_fr": analysis.description_fr,
                    "description_en": analysis.description_en,
                    "ig_quality": analysis.ig_quality,
                }
                scene_results.append(scene_data)
                all_raw.append({
                    "scene_index": idx,
                    "analysis": analysis.model_dump(),
                })
            except Exception as e:
                scene_results.append({
                    "scene_index": idx,
                    "start_sec": round(start, 2),
                    "end_sec": round(end, 2),
                    "frame_count": len(frames),
                    "error": str(e),
                })

        # Dominant scene = longest duration
        if scene_results:
            valid_scenes = [s for s in scene_results if "error" not in s]
            if valid_scenes:
                dominant = max(valid_scenes, key=lambda s: s["end_sec"] - s["start_sec"])
            else:
                dominant = scene_results[0]
        else:
            dominant = {}

        return {
            "scenes": scene_results,
            "category": dominant.get("category"),
            "subcategory": dominant.get("subcategory"),
            "ambiance": dominant.get("ambiance", []),
            "elements": dominant.get("elements", []),
            "season": dominant.get("season", []),
            "ig_quality": dominant.get("ig_quality"),
            "description_fr": dominant.get("description_fr"),
            "description_en": dominant.get("description_en"),
            "duration_seconds": meta["duration_seconds"],
            "aspect_ratio": meta["aspect_ratio"],
            "analysis_raw": {"scenes": all_raw, "metadata": meta},
            "analysis_model": "claude-sonnet-4-20250514",
        }
    finally:
        # Cleanup temp file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
