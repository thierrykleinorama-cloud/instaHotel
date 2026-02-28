"""
End-to-end Playwright test of Creative Studio page.
1. Navigate to Creative Studio
2. Select image 139266A8 via sidebar
3. Generate 3 Creative Scenarios via UI
4. For each scenario, use its prompt to generate a video via UI
5. Save screenshots + prompts + videos
"""
import os
import time
import json
from pathlib import Path
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

load_dotenv(Path(".env"))

URL = "http://localhost:8502/AI_Creative"
SCREENSHOTS = Path("test_screenshots")
OUT_DIR = Path("test_outputs/creative_suite_test")
SCREENSHOTS.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_FILENAME = "139266A8"


def wait_spinner_gone(page, timeout=300_000):
    """Wait until all Streamlit spinners disappear."""
    try:
        page.wait_for_selector('[data-testid="stSpinner"]', state="attached", timeout=3000)
        page.wait_for_selector('[data-testid="stSpinner"]', state="detached", timeout=timeout)
    except PWTimeout:
        pass


def shot(page, name):
    path = SCREENSHOTS / f"cs_{name}.png"
    page.screenshot(path=str(path))
    print(f"  [screenshot] {path.name}")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})

        # ---- 1. Load page ----
        print("STEP 1: Load Creative Studio")
        page.goto(URL, wait_until="networkidle", timeout=30000)
        time.sleep(4)
        shot(page, "01_loaded")

        # ---- 2. Search for image ----
        print("STEP 2: Search for image 139266A8")
        search_input = page.locator('[data-testid="stTextInput"] input').first
        search_input.fill(TARGET_FILENAME)
        search_input.press("Enter")
        time.sleep(3)

        body = page.inner_text("body")
        if TARGET_FILENAME in body:
            print("  Image found!")
        else:
            print("  WARNING: Image not found in page text")
        shot(page, "02_filtered")

        # ---- 3. Verify metadata display ----
        print("STEP 3: Verify metadata display")
        page.evaluate("window.scrollBy(0, 300)")
        time.sleep(1)
        body = page.inner_text("body")
        checks = {
            "Category": "chambre" in body.lower(),
            "Ambiance": "elegant" in body.lower(),
            "Quality": "9/10" in body,
            "Elements": "carrelage" in body.lower() or "lit" in body.lower(),
            "Description": "aerial" in body.lower() or "Art Nouveau" in body,
        }
        for k, v in checks.items():
            status = "OK" if v else "MISSING"
            print(f"  {k}: {status}")
        shot(page, "03_metadata")

        # ---- 4. Switch to Creative Scenarios tab ----
        print("STEP 4: Switch to Creative Scenarios tab")
        tabs = page.locator('[data-baseweb="tab"]')
        for i in range(tabs.count()):
            if "Scenario" in tabs.nth(i).inner_text():
                tabs.nth(i).click()
                break
        time.sleep(2)
        page.evaluate("window.scrollBy(0, 300)")
        shot(page, "04_scenarios_tab")

        # ---- 5. Generate scenarios ----
        print("STEP 5: Generate Creative Scenarios (Claude call)")
        gen_btn = page.get_by_role("button", name="Generate Scenarios")
        if not gen_btn.is_visible():
            print("  ERROR: Button not visible!")
            shot(page, "05_error")
            browser.close()
            return

        gen_btn.click()
        print("  Waiting for Claude...")
        wait_spinner_gone(page, timeout=60_000)
        time.sleep(3)
        page.evaluate("window.scrollBy(0, 400)")

        body = page.inner_text("body")
        if "failed" in body.lower()[:500]:
            print("  ERROR: Scenario generation failed!")
            shot(page, "05_failed")
            browser.close()
            return

        shot(page, "05_scenarios_generated")
        print("  Scenarios generated!")

        # ---- 6. Open expanders, extract prompts ----
        print("STEP 6: Extract motion prompts from scenarios")
        summaries = page.locator("details summary")
        for i in range(summaries.count()):
            try:
                summaries.nth(i).click()
                time.sleep(0.3)
            except Exception:
                pass
        time.sleep(1)
        shot(page, "06_expanders_open")

        # Extract only the "Motion prompt" textareas inside scenario expanders
        # These have keys cs_sc_prompt_0, cs_sc_prompt_1, etc.
        prompts = []
        ta_blocks = page.locator('[data-testid="stTextArea"]')
        for i in range(ta_blocks.count()):
            block = ta_blocks.nth(i)
            label = block.locator("label").first.inner_text() if block.locator("label").count() > 0 else ""
            if label.strip() == "Motion prompt":
                val = block.locator("textarea").first.input_value()
                if val and len(val) > 20:
                    prompts.append(val)
                    print(f"  Prompt {len(prompts)}: {val[:80]}...")

        prompts = prompts[:3]
        print(f"  Extracted {len(prompts)} prompts")

        if not prompts:
            print("  ERROR: No prompts extracted!")
            browser.close()
            return

        # Save prompts
        with open(OUT_DIR / "prompts.txt", "w", encoding="utf-8") as f:
            for i, pr in enumerate(prompts):
                f.write(f"=== Video {i+1} ===\n{pr}\n\n")
        print("  Prompts saved to prompts.txt")

        # ---- 7. Switch to Photo-to-Video, select Manual mode ----
        print("STEP 7: Switch to Photo-to-Video tab, Manual mode")
        tabs = page.locator('[data-baseweb="tab"]')
        for i in range(tabs.count()):
            txt = tabs.nth(i).inner_text()
            if "Video" in txt and "Scenario" not in txt:
                tabs.nth(i).click()
                break
        time.sleep(2)

        radio_labels = page.locator('[data-testid="stRadio"] label')
        for i in range(radio_labels.count()):
            if "Manual" in radio_labels.nth(i).inner_text():
                radio_labels.nth(i).click()
                break
        time.sleep(1)
        shot(page, "07_video_tab_manual")

        # ---- 8. Generate videos one by one ----
        for idx, prompt in enumerate(prompts):
            print(f"\nSTEP 8.{idx+1}: Generate video {idx+1}/3")
            print(f"  Prompt: {prompt[:70]}...")

            # Fill the motion prompt textarea
            prompt_ta = page.locator('[data-testid="stTextArea"] textarea').first
            prompt_ta.fill("")
            time.sleep(0.3)
            prompt_ta.fill(prompt)
            time.sleep(1)
            shot(page, f"08_{idx+1}_prompt_filled")

            # Click Generate Video
            gen_btn = page.get_by_role("button", name="Generate Video")
            if not gen_btn.is_visible():
                print("  ERROR: Generate Video button not visible!")
                continue

            gen_btn.click()
            print(f"  Generating... (up to 10 min)")
            wait_spinner_gone(page, timeout=600_000)
            time.sleep(3)
            page.evaluate("window.scrollBy(0, 500)")
            shot(page, f"09_{idx+1}_result")

            # Check result
            body = page.inner_text("body")
            if "Video generation failed" in body:
                err = [l for l in body.split("\n") if "failed" in l.lower()]
                print(f"  FAILED: {err[0] if err else 'unknown error'}")
            elif "Download Video" in body:
                print(f"  SUCCESS! Video {idx+1} generated, Download button visible.")
                # Check for video player
                if page.locator("video").count() > 0:
                    print(f"  Video player showing on page.")
            else:
                print(f"  Result unclear — check screenshot")

            # Rate limit wait
            if idx < len(prompts) - 1:
                print(f"  Waiting 15s (rate limit)...")
                time.sleep(15)

        shot(page, "10_final")
        print("\n=== UI TEST COMPLETE ===")
        print(f"Screenshots in: {SCREENSHOTS}/")
        browser.close()

    # ---- 9. Save actual video files via API ----
    # (Playwright can't download st.download_button binary content)
    print("\n=== Saving video files via API (same prompts, same image) ===")
    save_videos_and_image(prompts)


def save_videos_and_image(prompts):
    """Save original image + generate videos via API."""
    from src.services.media_queries import fetch_media_by_id
    from src.services.google_drive import download_file_bytes
    from src.services.creative_transform import photo_to_video

    media = fetch_media_by_id("85dc795b-41a1-4b92-b8f9-d629cdc44344")
    image_bytes = download_file_bytes(media["drive_file_id"])

    with open(OUT_DIR / "original_suite_photo.jpg", "wb") as f:
        f.write(image_bytes)
    print(f"Original image saved ({len(image_bytes) // 1024} KB)")

    total_cost = 0
    for i, prompt in enumerate(prompts):
        if i > 0:
            print(f"Waiting 15s (rate limit)...")
            time.sleep(15)
        print(f"Generating video {i+1}/{len(prompts)}...")
        t0 = time.time()
        try:
            result = photo_to_video(
                image_bytes=image_bytes,
                prompt=prompt,
                duration=5,
                aspect_ratio="9:16",
                model="kling-v2.1",
            )
            elapsed = time.time() - t0
            fname = OUT_DIR / f"video_{i+1}.mp4"
            with open(fname, "wb") as f:
                f.write(result["video_bytes"])
            cost = result["_cost"]["cost_usd"]
            total_cost += cost
            print(f"  Saved: {fname.name} ({len(result['video_bytes']) // 1024} KB, {elapsed:.0f}s, ${cost:.2f})")
        except Exception as e:
            print(f"  FAILED: {e}")

    print(f"\nTotal video cost: ${total_cost:.2f}")
    print(f"All files in: {OUT_DIR}/")


if __name__ == "__main__":
    main()
