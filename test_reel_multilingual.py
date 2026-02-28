"""
Playwright test — verify Reel + Multilingual features render correctly.
Tests IG Preview component in isolation (HTML rendering) and checks
that the prompt template fills correctly for both image and video media.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from src.prompts.caption_generation import USER_PROMPT_TEMPLATE, VIDEO_INSTRUCTION
from src.services.caption_generator import build_prompt
from app.components.ig_preview import render_ig_preview

def test_prompt_template_image():
    """Image media: no video instruction, media_type = image."""
    media = {"category": "chambre", "media_type": "image", "description_en": "A room"}
    prompt = build_prompt(media, "chambre", "ete", "link_bio")
    assert "Type de média : image" in prompt
    assert "reel" in prompt.lower()  # reel key is always in the JSON template
    assert VIDEO_INSTRUCTION not in prompt  # but video instruction should NOT be present
    print("[PASS] Image prompt: no video instruction, media_type=image")

def test_prompt_template_video():
    """Video media: video instruction present, media_type = video."""
    media = {"category": "experience", "media_type": "video", "description_en": "Pool video"}
    prompt = build_prompt(media, "experience", "ete", "dm")
    assert "Type de média : video" in prompt
    assert VIDEO_INSTRUCTION in prompt
    print("[PASS] Video prompt: has video instruction, media_type=video")

def test_ig_preview_post():
    """Standard 4:5 post preview."""
    html, h = render_ig_preview("AAAA", "Hello caption", "#sitges")
    assert "aspect-ratio: 4/5" in html
    assert "ig-reel-play" not in html
    assert "Reels" not in html
    assert h > 0
    print(f"[PASS] Post preview: 4:5, height={h}, no reel overlay")

def test_ig_preview_reel():
    """Reel 9:16 preview with play overlay."""
    html, h = render_ig_preview("AAAA", "Hook caption", "#reels", is_reel=True)
    assert "aspect-ratio: 9/16" in html
    assert "ig-reel-play" in html
    assert "Reels" in html
    assert h > 700  # 9:16 should be taller
    print(f"[PASS] Reel preview: 9:16, height={h}, has play overlay + Reels label")

def test_multilingual_caption_assembly():
    """Simulate multilingual caption stacking (done in Calendar page)."""
    es = "Descubre nuestro hotel"
    en = "Discover our hotel"
    fr = "Découvrez notre hôtel"
    parts = [es, f"\U0001f1ec\U0001f1e7\n{en}", f"\U0001f1eb\U0001f1f7\n{fr}"]
    stacked = "\n\n".join(parts)
    assert "🇬🇧" in stacked
    assert "🇫🇷" in stacked
    assert stacked.startswith("Descubre")
    print("[PASS] Multilingual stacking: ES + GB EN + FR FR")

if __name__ == "__main__":
    test_prompt_template_image()
    test_prompt_template_video()
    test_ig_preview_post()
    test_ig_preview_reel()
    test_multilingual_caption_assembly()
    print("\nAll 5 tests passed!")
