"""Final visual check: all 3 Enhancement operations + Captions"""
import asyncio
from playwright.async_api import async_playwright

BASE = "http://localhost:8501"


async def select_image_and_screenshot(page, search_term, operation, screenshot_name):
    """Navigate to Enhancement, select image, switch operation, screenshot."""
    await page.goto(f"{BASE}/AI_Enhancement", timeout=30000)
    await page.wait_for_load_state("networkidle")
    await asyncio.sleep(8)

    # Search filename
    search_inputs = await page.query_selector_all('input[type="text"]')
    for inp in search_inputs:
        placeholder = await inp.get_attribute("placeholder") or ""
        aria = await inp.get_attribute("aria-label") or ""
        if "filename" in placeholder.lower() or "filename" in aria.lower() or "search" in placeholder.lower():
            await inp.fill(search_term)
            await asyncio.sleep(2)
            break

    # Click Select
    for btn in await page.query_selector_all("button"):
        if (await btn.inner_text()).strip() == "Select":
            await btn.scroll_into_view_if_needed()
            await btn.click()
            break
    await asyncio.sleep(8)

    # Switch operation if needed
    if operation != "Upscale":
        label = await page.query_selector(f'text={operation}')
        if label:
            await label.click()
            await asyncio.sleep(5)

    # Scroll down to capture full content
    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    await asyncio.sleep(2)

    await page.screenshot(path=f"test_outputs/{screenshot_name}", full_page=True)

    errors = await page.query_selector_all(".stException")
    return len(errors) == 0


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1400, "height": 1200})

        # Enhancement: Upscale (default)
        ok = await select_image_and_screenshot(page, "IMG_4176", "Upscale", "final_enh_upscale.png")
        print(f"Upscale: {'OK' if ok else 'ERROR'}")

        # Enhancement: AI Retouch
        ok = await select_image_and_screenshot(page, "IMG_4176", "AI Retouch", "final_enh_retouch.png")
        print(f"AI Retouch: {'OK' if ok else 'ERROR'}")

        # Enhancement: Outpaint
        ok = await select_image_and_screenshot(page, "IMG_4176", "Outpaint", "final_enh_outpaint.png")
        print(f"Outpaint: {'OK' if ok else 'ERROR'}")

        # Captions
        await page.goto(f"{BASE}/AI_Captions", timeout=30000)
        await page.wait_for_load_state("networkidle")
        await asyncio.sleep(8)
        for inp in await page.query_selector_all('input[type="text"]'):
            placeholder = await inp.get_attribute("placeholder") or ""
            aria = await inp.get_attribute("aria-label") or ""
            if "filename" in placeholder.lower() or "filename" in aria.lower() or "search" in placeholder.lower():
                await inp.fill("IMG_4176")
                await asyncio.sleep(2)
                break
        for btn in await page.query_selector_all("button"):
            if (await btn.inner_text()).strip() == "Select":
                await btn.scroll_into_view_if_needed()
                await btn.click()
                break
        await asyncio.sleep(8)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(2)
        await page.screenshot(path="test_outputs/final_captions.png", full_page=True)
        errors = await page.query_selector_all(".stException")
        print(f"Captions: {'OK' if not errors else 'ERROR'}")

        await browser.close()
        print("\nDone!")


asyncio.run(main())
