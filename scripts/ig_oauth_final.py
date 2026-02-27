"""Final OAuth script: accept cookies, wait for login, capture code."""
import sys, time, urllib.parse
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding="utf-8")
    except: pass
from pathlib import Path
from playwright.sync_api import sync_playwright
import httpx

APP_ID = "1260328382725906"
APP_SECRET = "e9417241b80aeda9be7ef9da401e5e15"
GRAPH_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
REDIRECT_URI = "https://www.facebook.com/connect/login_success.html"
SCOPES = "instagram_business_basic,instagram_business_content_publish,pages_show_list,pages_read_engagement"

captured_code = None


def intercept_redirect(route):
    global captured_code
    url = route.request.url
    parsed = urllib.parse.urlparse(url)
    if "/connect/login_success" in parsed.path or "/connect/blank" in parsed.path:
        params = urllib.parse.parse_qs(parsed.query)
        if "code" in params:
            captured_code = params["code"][0]
            print(f"    CODE CAPTURED!")
        route.fulfill(
            status=200, content_type="text/html",
            body="<h1>Done! Token captured. You can close this window.</h1>",
        )
    else:
        route.continue_()


def main():
    global captured_code

    with sync_playwright() as p:
        print("[1] Launching browser...")
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(Path.home() / ".playwright-ig-oauth"),
            headless=False, channel="chrome", ignore_https_errors=True,
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        print("[2] Going to Facebook...")
        page.goto("https://www.facebook.com/", wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)

        # Accept cookies via JavaScript
        print("    Accepting cookies...")
        try:
            page.evaluate("""() => {
                const buttons = document.querySelectorAll('button, [role="button"]');
                for (const b of buttons) {
                    if (b.textContent && b.textContent.includes('Autoriser tous')) {
                        b.click(); return true;
                    }
                    if (b.textContent && b.textContent.includes('Allow all')) {
                        b.click(); return true;
                    }
                }
                return false;
            }""")
        except Exception:
            pass
        time.sleep(2)

        # Wait for login
        print("[3] If you see a login page, please log in now...")
        print("    Waiting up to 3 minutes...")
        for i in range(180):
            time.sleep(1)
            try:
                has_nav = page.locator('[role="navigation"]').count() > 0
                if has_nav:
                    print("    Logged in!")
                    break
                if i > 0 and i % 30 == 0:
                    print(f"    Still waiting... ({i}s)")
            except Exception:
                pass

        # Set up intercept
        page.route("**/connect/login_success*", intercept_redirect)
        page.route("**/connect/blank*", intercept_redirect)

        # OAuth
        print("[4] Opening OAuth authorization...")
        auth_url = (
            f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth"
            f"?client_id={APP_ID}"
            f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
            f"&scope={SCOPES}"
            f"&response_type=code"
            f"&auth_type=rerequest"
        )
        page.goto(auth_url, wait_until="commit")
        print("    Authorize the app in the browser...")

        deadline = time.time() + 120
        while not captured_code and time.time() < deadline:
            time.sleep(0.5)

        page.screenshot(path="test_screenshots/oauth_final3.png")
        ctx.close()

    if not captured_code:
        print("FAILED. Check test_screenshots/oauth_final3.png")
        return

    print(f"[5] Exchanging for long-lived token...")
    r1 = httpx.get(f"{GRAPH_BASE}/oauth/access_token", params={
        "client_id": APP_ID, "client_secret": APP_SECRET,
        "redirect_uri": REDIRECT_URI, "code": captured_code,
    }, timeout=30)
    r1.raise_for_status()
    short = r1.json()["access_token"]

    r2 = httpx.get(f"{GRAPH_BASE}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": APP_ID,
        "client_secret": APP_SECRET, "fb_exchange_token": short,
    }, timeout=30)
    r2.raise_for_status()
    token = r2.json()["access_token"]
    days = r2.json().get("expires_in", 0) // 86400
    print(f"    Token OK ({days} days)")

    # Scopes
    dr = httpx.get(f"{GRAPH_BASE}/debug_token", params={
        "input_token": token, "access_token": token,
    }, timeout=15)
    if dr.status_code == 200:
        scopes = dr.json().get("data", {}).get("scopes", [])
        print(f"    Scopes: {scopes}")

    # IG Account
    print("[6] Finding IG account...")
    r3 = httpx.get(f"{GRAPH_BASE}/me/accounts", params={
        "fields": "name,instagram_business_account", "access_token": token,
    }, timeout=15)
    ig_id = ""
    for pg in r3.json().get("data", []):
        ig = pg.get("instagram_business_account")
        if ig:
            ig_id = ig["id"]
            print(f"    Found: {ig_id} on page '{pg['name']}'")

    if not ig_id:
        r4 = httpx.get(f"{GRAPH_BASE}/me/accounts", params={"access_token": token}, timeout=15)
        for pg in r4.json().get("data", []):
            pt = pg.get("access_token", "")
            if pt:
                r5 = httpx.get(f"{GRAPH_BASE}/{pg['id']}", params={
                    "fields": "instagram_business_account", "access_token": pt,
                }, timeout=15)
                ig = r5.json().get("instagram_business_account")
                if ig:
                    ig_id = ig["id"]
                    print(f"    Found via page token: {ig_id}")

    # Save to .env
    env_path = Path(__file__).parent.parent / ".env"
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
    if not fa and ig_id:
        new_lines.append(f"INSTAGRAM_ACCOUNT_ID={ig_id}")
    env_path.write_text("\n".join(new_lines) + "\n")

    print()
    print("=" * 50)
    print("SUCCESS!")
    print(f"INSTAGRAM_ACCOUNT_ID = {ig_id or '(not found)'}")
    print(f"Token expires in {days} days")
    print(f"Saved to .env")
    print("=" * 50)


if __name__ == "__main__":
    main()
