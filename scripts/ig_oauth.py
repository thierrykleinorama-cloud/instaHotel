"""
One-shot OAuth script for Instagram Business Login.
1. Starts a local web server on port 5555
2. Opens the authorization URL in your default browser
3. You authorize in the browser
4. Instagram redirects back to localhost with a code
5. Script exchanges code for a long-lived token
6. Looks up your Instagram Business Account ID
7. Saves both to .env

Usage: python scripts/ig_oauth.py <APP_ID> <APP_SECRET>
"""
import http.server
import json
import os
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import httpx

REDIRECT_URI = "https://localhost:5555/auth/"
GRAPH_VERSION = "v21.0"
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"

# Will be set from CLI args
APP_ID = None
APP_SECRET = None

# Result storage
auth_code = None
server_done = threading.Event()


class OAuthHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>OK! Token received. You can close this tab.</h1>")
            server_done.set()
        elif "error" in params:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            msg = params.get("error_description", ["Unknown error"])[0]
            self.wfile.write(f"<h1>Error: {msg}</h1>".encode())
            server_done.set()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress request logs


def exchange_code_for_token(code):
    """Exchange auth code for short-lived token, then for long-lived token."""
    # Step 1: code -> short-lived token
    resp = httpx.get(
        f"{GRAPH_BASE}/oauth/access_token",
        params={
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "redirect_uri": REDIRECT_URI,
            "code": code,
        },
        timeout=30,
    )
    resp.raise_for_status()
    short_token = resp.json()["access_token"]
    print(f"  Short-lived token obtained")

    # Step 2: short-lived -> long-lived token (60 days)
    resp2 = httpx.get(
        f"{GRAPH_BASE}/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "fb_exchange_token": short_token,
        },
        timeout=30,
    )
    resp2.raise_for_status()
    data = resp2.json()
    long_token = data["access_token"]
    expires_in = data.get("expires_in", "unknown")
    print(f"  Long-lived token obtained (expires in {expires_in}s = ~{int(expires_in)//86400} days)")
    return long_token


def find_ig_account(token):
    """Find the Instagram Business Account ID via FB Pages."""
    # Get pages
    resp = httpx.get(
        f"{GRAPH_BASE}/me/accounts",
        params={"fields": "name,instagram_business_account", "access_token": token},
        timeout=15,
    )
    resp.raise_for_status()
    pages = resp.json().get("data", [])

    for page in pages:
        ig = page.get("instagram_business_account")
        if ig:
            print(f"  Found IG account {ig['id']} on page '{page['name']}'")
            return ig["id"]

    # Fallback: try page token
    resp2 = httpx.get(
        f"{GRAPH_BASE}/me/accounts",
        params={"access_token": token},
        timeout=15,
    )
    resp2.raise_for_status()
    for page in resp2.json().get("data", []):
        page_token = page.get("access_token")
        if page_token:
            resp3 = httpx.get(
                f"{GRAPH_BASE}/{page['id']}",
                params={"fields": "instagram_business_account", "access_token": page_token},
                timeout=15,
            )
            if resp3.status_code == 200:
                ig = resp3.json().get("instagram_business_account")
                if ig:
                    print(f"  Found IG account {ig['id']} on page '{page['name']}' (via page token)")
                    return ig["id"]

    return None


def save_to_env(token, ig_account_id):
    """Append or update INSTAGRAM_* vars in .env."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print(f"  .env not found at {env_path}")
        return

    content = env_path.read_text()
    lines = content.splitlines()
    new_lines = []
    found_token = False
    found_acct = False

    for line in lines:
        if line.startswith("INSTAGRAM_ACCESS_TOKEN="):
            new_lines.append(f"INSTAGRAM_ACCESS_TOKEN={token}")
            found_token = True
        elif line.startswith("INSTAGRAM_ACCOUNT_ID="):
            new_lines.append(f"INSTAGRAM_ACCOUNT_ID={ig_account_id}")
            found_acct = True
        else:
            new_lines.append(line)

    if not found_token:
        new_lines.append(f"INSTAGRAM_ACCESS_TOKEN={token}")
    if not found_acct:
        new_lines.append(f"INSTAGRAM_ACCOUNT_ID={ig_account_id}")

    env_path.write_text("\n".join(new_lines) + "\n")
    print(f"  Saved to {env_path}")


def main():
    global APP_ID, APP_SECRET

    if len(sys.argv) < 3:
        print("Usage: python scripts/ig_oauth.py <APP_ID> <APP_SECRET>")
        sys.exit(1)

    APP_ID = sys.argv[1]
    APP_SECRET = sys.argv[2]

    # Build OAuth URL
    scopes = "instagram_business_basic,instagram_business_content_publish,pages_show_list,pages_read_engagement"
    auth_url = (
        f"https://www.facebook.com/{GRAPH_VERSION}/dialog/oauth"
        f"?client_id={APP_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI)}"
        f"&scope={scopes}"
        f"&response_type=code"
    )

    print(f"\n=== Instagram OAuth Setup ===\n")
    print(f"1. Starting local server on port 5555...")

    # We need HTTPS for the redirect. Use HTTP and hope FB accepts it,
    # or just have user copy the code from the URL.
    # Actually, let's use HTTP redirect and see.
    # FB requires HTTPS for redirect URIs. Let's use a different approach.

    # Simpler: just open the auth URL and have user paste the redirected URL
    print(f"2. Opening authorization URL in browser...\n")
    print(f"   If browser doesn't open, visit this URL:\n")
    print(f"   {auth_url}\n")
    print(f"3. After authorizing, you'll be redirected to a URL starting with")
    print(f"   {REDIRECT_URI}?code=...")
    print(f"   The page won't load (that's OK!)")
    print(f"   Copy the FULL URL from your browser's address bar and paste it here:\n")

    webbrowser.open(auth_url)

    redirected_url = input("Paste the full redirect URL here: ").strip()

    # Extract code from URL
    parsed = urllib.parse.urlparse(redirected_url)
    params = urllib.parse.parse_qs(parsed.query)
    code = params.get("code", [None])[0]

    if not code:
        print("ERROR: Could not find 'code' in the URL. Make sure you copied the full URL.")
        sys.exit(1)

    print(f"\n4. Exchanging code for long-lived token...")
    token = exchange_code_for_token(code)

    print(f"5. Looking up Instagram Business Account ID...")
    ig_id = find_ig_account(token)

    if ig_id:
        print(f"\n=== SUCCESS ===")
        print(f"INSTAGRAM_ACCESS_TOKEN={token[:20]}...{token[-10:]}")
        print(f"INSTAGRAM_ACCOUNT_ID={ig_id}")

        print(f"\n6. Saving to .env...")
        save_to_env(token, ig_id)
        print(f"\nDone! You're ready to publish to Instagram.")
    else:
        print(f"\nWARNING: Could not find Instagram Business Account.")
        print(f"Token obtained: {token[:20]}...{token[-10:]}")
        print(f"You may need to link your IG account to your FB Page first.")
        print(f"\nSaving token to .env anyway...")
        save_to_env(token, "UNKNOWN_RUN_SCRIPT_AGAIN")


if __name__ == "__main__":
    main()
