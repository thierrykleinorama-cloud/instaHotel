"""
Playwright OAuth: intercept the redirect, capture code, exchange for token.
"""
import os
import sys
import time
import urllib.parse
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import httpx
from playwright.sync_api import sync_playwright

APP_ID = "1260328382725906"
APP_SECRET = "e9417241b80aeda9be7ef9da401e5e15"
GRAPH_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
REDIRECT_URI = "https://www.facebook.com/connect/login_success.html"
SCOPES = "instagram_business_basic,instagram_business_content_publish,pages_show_list,pages_read_engagement"

captured_code = None
captured_url = None


def exchange_code(code):
    resp = httpx.get(f"{GRAPH_BASE}/oauth/access_token", params={
        "client_id": APP_ID, "client_secret": APP_SECRET,
        "redirect_uri": REDIRECT_URI, "code": code,
    }, timeout=30)
    resp.raise_for_status()
    short_token = resp.json()["access_token"]
    print("  Short-lived token OK")
    resp2 = httpx.get(f"{GRAPH_BASE}/oauth/access_token", params={
        "grant_type": "fb_exchange_token",
        "client_id": APP_ID, "client_secret": APP_SECRET,
        "fb_exchange_token": short_token,
    }, timeout=30)
    resp2.raise_for_status()
    data = resp2.json()
    print(f"  Long-lived token OK ({data.get('expires_in', 0) // 86400} days)")
    return data["access_token"]


def find_ig_account(token):
    resp = httpx.get(f"{GRAPH_BASE}/me/accounts", params={
        "fields": "name,instagram_business_account", "access_token": token,
    }, timeout=15)
    resp.raise_for_status()
    for page in resp.json().get("data", []):
        ig = page.get("instagram_business_account")
        if ig:
            print(f"  IG account {ig['id']} on page '{page['name']}'")
            return ig["id"]
    resp2 = httpx.get(f"{GRAPH_BASE}/me/accounts", params={"access_token": token}, timeout=15)
    for page in resp2.json().get("data", []):
        pt = page.get("access_token", "")
        if pt:
            resp3 = httpx.get(f"{GRAPH_BASE}/{page['id']}", params={
                "fields": "instagram_business_account", "access_token": pt,
            }, timeout=15)
            ig = resp3.json().get("instagram_business_account")
            if ig:
                print(f"  IG account {ig['id']} via page token")
                return ig["id"]
    return None


def save_to_env(token, ig_id):
    env_path = Path(__file__).parent.parent / ".env"
    content = env_path.read_text() if env_path.exists() else ""
    lines = content.splitlines()
    new_lines, found_t, found_a = [], False, False
    for line in lines:
        if line.startswith("INSTAGRAM_ACCESS_TOKEN="):
            new_lines.append(f"INSTAGRAM_ACCESS_TOKEN={token}")
            found_t = True
        elif line.startswith("INSTAGRAM_ACCOUNT_ID="):
            new_lines.append(f"INSTAGRAM_ACCOUNT_ID={ig_id}")
            found_a = True
        else:
            new_lines.append(line)
    if not found_t:
        new_lines.append(f"INSTAGRAM_ACCESS_TOKEN={token}")
    if not found_a and ig_id:
        new_lines.append(f"INSTAGRAM_ACCOUNT_ID={ig_id}")
    env_path.write_text("\n".join(new_lines) + "\n")
    print(f"  Saved to {env_path}")


def main():
    global captured_code, captured_url
    print("\n=== Instagram OAuth ===\n")

    auth_url = (
        f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth"
        f"?client_id={APP_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&scope={SCOPES}"
        f"&response_type=code"
        f"&auth_type=rerequest"
    )

    with sync_playwright() as p:
        print("[1] Launching browser...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(Path.home() / ".playwright-ig-oauth"),
            headless=False,
            channel="chrome",
            ignore_https_errors=True,
        )
        page = context.pages[0] if context.pages else context.new_page()

        def intercept_redirect(route):
            global captured_code, captured_url
            url = route.request.url
            captured_url = url
            print(f"\n  INTERCEPTED URL: {url[:200]}")

            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            if "code" in params:
                captured_code = params["code"][0]
                print(f"  CODE FOUND: {captured_code[:30]}...")
            else:
                print(f"  URL params: {list(params.keys())}")
                # Maybe code is in fragment
                if parsed.fragment:
                    frag_params = urllib.parse.parse_qs(parsed.fragment)
                    if "code" in frag_params:
                        captured_code = frag_params["code"][0]
                        print(f"  CODE IN FRAGMENT: {captured_code[:30]}...")
                    elif "access_token" in frag_params:
                        captured_code = "TOKEN:" + frag_params["access_token"][0]
                        print(f"  TOKEN IN FRAGMENT!")

            route.fulfill(
                status=200,
                content_type="text/html",
                body="<html><body><h1>Done! Check your terminal.</h1></body></html>",
            )

        page.route("**/connect/login_success*", intercept_redirect)
        page.route("**/connect/blank*", intercept_redirect)

        print("[2] Opening Facebook auth... authorize in the browser.\n")
        page.goto(auth_url, wait_until="commit")

        deadline = time.time() + 180
        while not captured_url and time.time() < deadline:
            time.sleep(0.5)

        # Give a moment for processing
        time.sleep(2)

        context.close()

    if captured_code and captured_code.startswith("TOKEN:"):
        # Got token directly
        token = captured_code[6:]
        print(f"\n[3] Got token directly from redirect!")
        print(f"[4] Exchanging for long-lived token...")
        resp = httpx.get(f"{GRAPH_BASE}/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID, "client_secret": APP_SECRET,
            "fb_exchange_token": token,
        }, timeout=30)
        resp.raise_for_status()
        token = resp.json()["access_token"]
        print(f"  Long-lived token OK")
    elif captured_code:
        print(f"\n[3] Exchanging code for long-lived token...")
        token = exchange_code(captured_code)
    else:
        print(f"\nFAILED. Intercepted URL: {captured_url}")
        print("No code or token found.")
        return

    print(f"[4] Looking up Instagram Business Account...")
    ig_id = find_ig_account(token)

    # Debug token scopes
    print(f"\n[debug] Checking token scopes...")
    dresp = httpx.get(f"{GRAPH_BASE}/debug_token", params={
        "input_token": token, "access_token": token,
    }, timeout=15)
    if dresp.status_code == 200:
        scopes = dresp.json().get("data", {}).get("scopes", [])
        print(f"  Scopes: {scopes}")

    if ig_id:
        print(f"\n{'='*50}")
        print(f"SUCCESS!")
        print(f"INSTAGRAM_ACCOUNT_ID = {ig_id}")
        print(f"{'='*50}")
    else:
        print(f"\nToken OK but IG account not found.")
        ig_id = ""

    print(f"\n[5] Saving to .env...")
    save_to_env(token, ig_id)
    print("Done!")


if __name__ == "__main__":
    main()
