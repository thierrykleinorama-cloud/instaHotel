"""
Get Instagram token via Meta Developer Dashboard + Playwright.
Navigates to the API Setup page, takes screenshots to guide the user.
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

# Instagram Business Login app credentials
IG_APP_ID = "2310589572751601"
IG_APP_SECRET = "aa1c104f609ba2e0822e52531450fc8f"
FB_APP_ID = "1260328382725906"

DASHBOARD_URL = (
    f"https://developers.facebook.com/apps/{FB_APP_ID}"
    f"/use_cases/customize/"
    f"?use_case_enum=INSTAGRAM_BUSINESS"
    f"&product_route=instagram-business"
    f"&selected_tab=API-Setup"
)

PROFILE_DIR = str(Path.home() / ".playwright-ig-oauth")
SCREENSHOTS = Path(__file__).parent.parent / "test_screenshots"
SCREENSHOTS.mkdir(exist_ok=True)


def save_to_env(token: str, ig_id: str):
    """Save token and account ID to .env."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print(f"  .env not found at {env_path}")
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


def get_long_lived_token(short_token: str) -> tuple[str, int]:
    """Exchange short-lived IG token for long-lived (60 days)."""
    print("  Exchanging for long-lived token...")
    resp = httpx.get(
        "https://graph.instagram.com/access_token",
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": IG_APP_SECRET,
            "access_token": short_token,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"  Long-lived exchange failed: {resp.status_code} {resp.text[:300]}")
        # If it fails, the token might already be long-lived
        return short_token, 0
    data = resp.json()
    days = data.get("expires_in", 0) // 86400
    return data["access_token"], days


def get_ig_info(token: str) -> dict:
    """Get IG account info from the token."""
    resp = httpx.get(
        "https://graph.instagram.com/v21.0/me",
        params={
            "fields": "user_id,username,account_type,name",
            "access_token": token,
        },
        timeout=15,
    )
    if resp.status_code == 200:
        return resp.json()
    print(f"  IG info failed: {resp.status_code} {resp.text[:200]}")
    return {}


def main():
    print("\n" + "=" * 55)
    print("  Instagram Token — Dashboard Approach")
    print("=" * 55 + "\n")

    with sync_playwright() as p:
        print("[1] Launching browser with saved Facebook session...")
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            channel="chrome",
            ignore_https_errors=True,
            viewport={"width": 1400, "height": 900},
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        print(f"[2] Navigating to Meta Developer Dashboard...")
        print(f"    {DASHBOARD_URL[:80]}...\n")
        page.goto(DASHBOARD_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(5)

        # Screenshot the initial state
        page.screenshot(path=str(SCREENSHOTS / "dashboard_01_initial.png"), full_page=False)
        print(f"  Screenshot saved: test_screenshots/dashboard_01_initial.png")

        # Check if we need to log in
        current_url = page.url
        if "login" in current_url.lower() or "checkpoint" in current_url.lower():
            print("\n  >>> You need to log into Facebook in the browser window.")
            print("  >>> After logging in, the page should redirect to the dashboard.")
            print("  >>> Waiting up to 3 minutes...\n")
            for i in range(180):
                time.sleep(1)
                if "developers.facebook.com/apps" in page.url:
                    print("  Logged in! Continuing...")
                    time.sleep(3)
                    break
                if i > 0 and i % 30 == 0:
                    print(f"  Still waiting... ({i}s)")
            page.screenshot(path=str(SCREENSHOTS / "dashboard_02_after_login.png"), full_page=False)

        print("\n[3] Looking for token generation UI...")
        print("    The browser should show the Instagram API Setup page.")
        print("    Please interact with the browser to:")
        print("    1. Click 'Add account' / 'Ajouter un compte' if needed")
        print("    2. Authorize the Instagram account")
        print("    3. Click 'Generate token' / 'Generer un token'")
        print("    4. Copy the token from the dialog that appears")
        print()

        # Wait for user to get the token and paste it
        print("=" * 55)
        token_input = input("  Paste the token here (or 'q' to quit): ").strip()
        print("=" * 55)

        if not token_input or token_input.lower() == "q":
            print("\n  Aborted.")
            page.screenshot(path=str(SCREENSHOTS / "dashboard_03_final.png"), full_page=False)
            ctx.close()
            return

        # Take final screenshot
        page.screenshot(path=str(SCREENSHOTS / "dashboard_03_final.png"), full_page=False)
        ctx.close()

    # Process the token
    print(f"\n[4] Processing token...")
    token = token_input.strip().strip('"').strip("'")

    # Try to exchange for long-lived
    long_token, days = get_long_lived_token(token)
    if days > 0:
        print(f"  Long-lived token obtained ({days} days)")
        token = long_token
    else:
        print("  Using token as-is (may already be long-lived)")

    # Get account info
    print(f"\n[5] Getting Instagram account info...")
    info = get_ig_info(token)
    ig_id = str(info.get("user_id", ""))
    username = info.get("username", "unknown")
    acct_type = info.get("account_type", "unknown")

    if ig_id:
        print(f"  Account: @{username} (ID: {ig_id}, type: {acct_type})")
    else:
        print(f"  Could not get user_id from token. Response: {info}")
        ig_id = input("  Enter the Instagram Account ID manually (or press Enter to skip): ").strip()

    # Save
    if token:
        print(f"\n[6] Saving to .env...")
        save_to_env(token, ig_id)

        print(f"\n{'=' * 55}")
        print(f"  SUCCESS!")
        if username != "unknown":
            print(f"  Instagram: @{username}")
        print(f"  INSTAGRAM_ACCOUNT_ID = {ig_id}")
        if days > 0:
            print(f"  Token expires in {days} days")
        print(f"  Saved to .env")
        print(f"{'=' * 55}\n")
    else:
        print("\n  No token to save.")


if __name__ == "__main__":
    main()
