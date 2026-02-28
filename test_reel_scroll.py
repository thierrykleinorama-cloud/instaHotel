"""Scroll down to capture the rendered IG preview cards for Reel and Multilingual."""
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1400, "height": 900})

    page.goto("http://localhost:8501/Calendar")
    page.wait_for_timeout(6000)

    # Switch to List
    page.locator('label:has-text("List")').click()
    page.wait_for_timeout(3000)

    # Expand 02-27
    expanders = page.locator("details summary")
    for i in range(expanders.count()):
        if "02-27" in expanders.nth(i).inner_text():
            expanders.nth(i).click()
            break
    page.wait_for_timeout(3000)

    # Enable IG Preview
    preview_cb = page.locator('label:has-text("Show IG Preview")').last
    preview_cb.scroll_into_view_if_needed()
    page.wait_for_timeout(500)
    preview_cb.click()
    page.wait_for_timeout(3000)

    # Select "Reel" variant
    variant_selects = page.locator('div[data-testid="stSelectbox"]')
    for i in range(variant_selects.count()):
        label = variant_selects.nth(i).locator("label").inner_text()
        if "Variant" in label:
            variant_selects.nth(i).locator("div[data-baseweb='select']").click()
            page.wait_for_timeout(500)
            page.locator('li:has-text("Reel")').first.click()
            page.wait_for_timeout(3000)
            break

    # Scroll down to see the IG card
    iframe = page.locator("iframe").last
    if iframe.count() > 0:
        iframe.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
    else:
        page.evaluate("window.scrollBy(0, 800)")
        page.wait_for_timeout(1000)

    page.screenshot(path="test_screenshots/reel_08_reel_card.png", full_page=False)
    print("Reel card screenshot saved")

    # Now switch to Multilingual Short
    for i in range(variant_selects.count()):
        label = variant_selects.nth(i).locator("label").inner_text()
        if "Variant" in label:
            variant_selects.nth(i).scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            variant_selects.nth(i).locator("div[data-baseweb='select']").click()
            page.wait_for_timeout(500)
            page.locator('li:has-text("Multilingual Short")').first.click()
            page.wait_for_timeout(3000)
            break

    iframe = page.locator("iframe").last
    if iframe.count() > 0:
        iframe.scroll_into_view_if_needed()
        page.wait_for_timeout(1000)
    else:
        page.evaluate("window.scrollBy(0, 800)")
        page.wait_for_timeout(1000)

    page.screenshot(path="test_screenshots/reel_09_multilingual_card.png", full_page=False)
    print("Multilingual card screenshot saved")

    browser.close()
