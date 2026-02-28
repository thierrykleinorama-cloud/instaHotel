"""Playwright test: open Calendar, find video slot 2026-02-27, check Reel tabs + IG Preview."""
from playwright.sync_api import sync_playwright
import os

os.makedirs("test_screenshots", exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    page.goto("http://localhost:8501/Calendar")
    page.wait_for_timeout(6000)

    # Switch to List view
    page.locator('label:has-text("List")').click()
    page.wait_for_timeout(3000)

    # Find all expanders, look for 02-27
    expanders = page.locator("details summary")
    count = expanders.count()
    target_idx = None
    for i in range(count):
        text = expanders.nth(i).inner_text()
        if "02-27" in text:
            target_idx = i
            break

    if target_idx is None:
        page.screenshot(path="test_screenshots/reel_err_no_slot.png", full_page=True)
        browser.close()
        raise SystemExit("Could not find 2026-02-27 slot")

    # Expand the video slot
    expanders.nth(target_idx).scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    expanders.nth(target_idx).click()
    page.wait_for_timeout(3000)

    # Scroll to see caption section
    page.evaluate("window.scrollBy(0, 400)")
    page.wait_for_timeout(1000)
    page.screenshot(path="test_screenshots/reel_02_slot_expanded.png", full_page=False)

    # Check for Reel text area
    reel_ta = page.locator('textarea[aria-label="Reel"]')
    reel_count = reel_ta.count()

    # Scroll down more to see all tabs
    page.evaluate("window.scrollBy(0, 400)")
    page.wait_for_timeout(500)
    page.screenshot(path="test_screenshots/reel_03_caption_tabs.png", full_page=False)

    # Click "Show IG Preview" checkbox
    preview_cb = page.locator('label:has-text("Show IG Preview")').last
    if preview_cb.is_visible():
        preview_cb.click()
        page.wait_for_timeout(2000)

        # Scroll to see preview section
        page.evaluate("window.scrollBy(0, 300)")
        page.wait_for_timeout(1000)
        page.screenshot(path="test_screenshots/reel_04_preview_with_variant.png", full_page=False)

        # Try selecting "Reel" in Variant dropdown
        # Find the variant selectbox
        variant_selects = page.locator('div[data-testid="stSelectbox"]')
        for i in range(variant_selects.count()):
            label = variant_selects.nth(i).locator("label").inner_text()
            if "Variant" in label:
                variant_selects.nth(i).locator("div[data-baseweb='select']").click()
                page.wait_for_timeout(500)
                # Look for Reel option
                reel_option = page.locator('li:has-text("Reel")').first
                if reel_option.is_visible():
                    reel_option.click()
                    page.wait_for_timeout(2000)
                    page.evaluate("window.scrollBy(0, 200)")
                    page.wait_for_timeout(1000)
                    page.screenshot(path="test_screenshots/reel_05_reel_preview.png", full_page=False)
                break

        # Also try Multilingual Short
        for i in range(variant_selects.count()):
            label = variant_selects.nth(i).locator("label").inner_text()
            if "Variant" in label:
                variant_selects.nth(i).locator("div[data-baseweb='select']").click()
                page.wait_for_timeout(500)
                ml_option = page.locator('li:has-text("Multilingual Short")').first
                if ml_option.is_visible():
                    ml_option.click()
                    page.wait_for_timeout(2000)
                    page.evaluate("window.scrollBy(0, 200)")
                    page.wait_for_timeout(1000)
                    page.screenshot(path="test_screenshots/reel_06_multilingual_preview.png", full_page=False)
                break

    # Take full-page screenshot
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(500)
    page.screenshot(path="test_screenshots/reel_07_full_page.png", full_page=True)

    browser.close()
    print(f"Reel text areas found: {reel_count}")
    print("All screenshots saved!")
