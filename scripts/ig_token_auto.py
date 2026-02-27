"""
Step 10: Add instagram_business_content_publish permission, then regenerate token.
"""
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import httpx
from playwright.sync_api import sync_playwright

FB_APP_ID = "1260328382725906"
IG_APP_SECRET = "aa1c104f609ba2e0822e52531450fc8f"
PROFILE_DIR = str(Path.home() / ".playwright-ig-oauth")
SCREENSHOTS = Path(__file__).parent.parent / "test_screenshots"
SCREENSHOTS.mkdir(exist_ok=True)


def screenshot(page, name):
    path = str(SCREENSHOTS / name)
    page.screenshot(path=path, full_page=False)
    print(f"  Screenshot: test_screenshots/{name}")


def accept_cookies(page):
    for text in ["Autoriser tous les cookies", "Allow all cookies"]:
        try:
            btn = page.locator(f"text=/{text}/i").first
            if btn.is_visible(timeout=2000):
                btn.click()
                time.sleep(2)
                return
        except Exception:
            pass


def save_to_env(token, ig_id):
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    content = env_path.read_text()
    lines = content.splitlines()
    new_lines, ft, fa = [], False, False
    for line in lines:
        if line.startswith("INSTAGRAM_ACCESS_TOKEN="):
            new_lines.append(f"INSTAGRAM_ACCESS_TOKEN={token}")
            ft = True
        elif line.startswith("INSTAGRAM_ACCOUNT_ID="):
            new_lines.append(f"INSTAGRAM_ACCOUNT_ID={ig_id}")
            fa = True
        else:
            new_lines.append(line)
    if not ft:
        new_lines.append(f"INSTAGRAM_ACCESS_TOKEN={token}")
    if not fa:
        new_lines.append(f"INSTAGRAM_ACCOUNT_ID={ig_id}")
    env_path.write_text("\n".join(new_lines) + "\n")
    print(f"  Saved to {env_path}")


def main():
    print("\n=== Add content_publish Permission + New Token ===\n")

    with sync_playwright() as p:
        print("[1] Launching browser...")
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            channel="chrome",
            ignore_https_errors=True,
            viewport={"width": 1400, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        # ===============================================================
        # PART 1: Go to Permissions page and add content_publish
        # ===============================================================
        print("[2] Going to Permissions page...")
        perms_url = (
            f"https://developers.facebook.com/apps/{FB_APP_ID}"
            f"/use_cases/customize/"
            f"?use_case_enum=INSTAGRAM_BUSINESS"
            f"&product_route=instagram-business"
            f"&selected_tab=permissions"
        )
        page.goto(perms_url, wait_until="domcontentloaded", timeout=30000)
        time.sleep(15)
        screenshot(page, "s10_01_permissions.png")

        # Get all text to understand the page
        try:
            text = page.inner_text("body")[:5000]
            print("  Page content (permission-related):")
            for line in text.split("\n"):
                line = line.strip()
                if line and any(kw in line.lower() for kw in [
                    "content_publish", "publish", "instagram_business",
                    "permission", "autoris", "ajouter", "add",
                    "activ", "request", "demander",
                ]):
                    print(f"    {line}")
        except Exception:
            pass

        # Scroll down to see more
        page.evaluate("window.scrollTo(0, 500)")
        time.sleep(3)
        screenshot(page, "s10_02_permissions_scrolled.png")

        page.evaluate("window.scrollTo(0, 1000)")
        time.sleep(3)
        screenshot(page, "s10_03_permissions_scrolled2.png")

        # Look for content_publish toggle/button
        print("\n[3] Looking for 'content_publish' permission...")
        found = False
        try:
            # Try to find by text
            cp = page.locator("text=/content_publish/i")
            count = cp.count()
            print(f"  Found {count} elements with 'content_publish'")
            if count > 0:
                for i in range(count):
                    try:
                        el = cp.nth(i)
                        txt = el.inner_text(timeout=2000)
                        print(f"    [{i}] '{txt}'")
                    except Exception:
                        pass

                # Find the "Add" or "Ajouter" or toggle button near it
                # Look for a button/link near content_publish text
                parent = cp.first.locator("xpath=ancestor::*[contains(@class, 'row') or contains(@class, 'item') or contains(@class, 'card')]").first
                try:
                    btns = parent.locator("button, a, [role='switch'], [role='button']").all()
                    for btn in btns:
                        txt = btn.inner_text(timeout=1000)
                        print(f"    Nearby button: '{txt}'")
                except Exception:
                    pass
        except Exception as e:
            print(f"  Search error: {e}")

        # Alternative: use JS to find and interact
        print("\n[4] Using JS to find and enable content_publish...")
        result = page.evaluate("""() => {
            const results = [];
            const allElements = document.querySelectorAll('*');
            for (const el of allElements) {
                const text = el.textContent || '';
                if (text.includes('content_publish') && el.children.length < 3) {
                    results.push({
                        tag: el.tagName,
                        text: text.substring(0, 100),
                        class: el.className.substring(0, 80),
                        parent: el.parentElement ? el.parentElement.tagName : 'none',
                    });
                }
            }
            return results.slice(0, 10);
        }""")
        print(f"  JS found: {result}")

        # Try to find "Ajouter" or toggle buttons on the permissions page
        print("\n[5] Looking for all 'Ajouter' / 'Add' / toggle buttons on page...")
        try:
            buttons = page.locator("button:visible, [role='switch']:visible, [role='button']:visible").all()
            print(f"  Found {len(buttons)} visible buttons")
            for i, btn in enumerate(buttons[:20]):
                try:
                    txt = btn.inner_text(timeout=1000).strip()
                    if txt and len(txt) < 80:
                        print(f"    [{i}] '{txt}'")
                except Exception:
                    pass
        except Exception as e:
            print(f"  Error: {e}")

        # ===============================================================
        # PART 2: Full page screenshot with scroll for analysis
        # ===============================================================
        print("\n[6] Taking full page scroll screenshots...")
        for scroll_y in [0, 400, 800, 1200, 1600]:
            page.evaluate(f"window.scrollTo(0, {scroll_y})")
            time.sleep(1)
            screenshot(page, f"s10_04_scroll_{scroll_y}.png")

        # Keep browser open for manual interaction
        print("\n[7] Browser open 60s — you can also manually find the permission...")
        print("    Look for 'instagram_business_content_publish' on the page")
        print("    and click 'Add' or the toggle next to it.")
        time.sleep(60)
        screenshot(page, "s10_99_final.png")

        ctx.close()

    print("\nDone.\n")


if __name__ == "__main__":
    main()
