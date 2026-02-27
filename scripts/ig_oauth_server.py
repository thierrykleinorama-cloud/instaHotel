"""
Instagram Business Login - Local HTTPS server OAuth flow.

Uses the CORRECT Instagram OAuth endpoint (not Facebook's).
Starts a local HTTPS server to capture the redirect automatically.

PREREQUISITE:
  Add  https://localhost:5555/  as a Valid OAuth Redirect URI
  in your Meta App > Instagram Business Login settings.

Usage: python scripts/ig_oauth_server.py
"""
import http.server
import os
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import webbrowser
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import httpx

APP_ID = "2310589572751601"          # Instagram App ID (NOT Facebook App ID)
APP_SECRET = "aa1c104f609ba2e0822e52531450fc8f"  # Instagram App Secret
REDIRECT_URI = "https://localhost:5555/"
SCOPES = "instagram_business_basic,instagram_business_content_publish"

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
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
                b"<h1>Success!</h1>"
                b"<p>Authorization code captured. You can close this tab.</p>"
                b"</body></html>"
            )
            server_done.set()
        elif "error" in params:
            error_desc = params.get("error_description", ["Unknown error"])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                f"<html><body style='font-family:sans-serif;text-align:center;padding:60px'>"
                f"<h1>Error</h1><p>{error_desc}</p>"
                f"</body></html>".encode()
            )
            server_done.set()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Waiting for authorization...</h1></body></html>")

    def log_message(self, fmt, *args):
        pass  # Suppress request logs


def generate_cert(cert_dir):
    """Generate a self-signed certificate for localhost using openssl."""
    cert_file = os.path.join(cert_dir, "cert.pem")
    key_file = os.path.join(cert_dir, "key.pem")
    subprocess.run(
        [
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", key_file, "-out", cert_file,
            "-days", "1", "-nodes",
            "-subj", "/CN=localhost",
        ],
        check=True,
        capture_output=True,
    )
    return cert_file, key_file


def exchange_code(code):
    """Exchange auth code for short-lived token via Instagram API."""
    print("    Exchanging code for short-lived token...")
    resp = httpx.post(
        "https://api.instagram.com/oauth/access_token",
        data={
            "client_id": APP_ID,
            "client_secret": APP_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code": code,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"    ERROR: {resp.status_code} {resp.text[:300]}")
        raise RuntimeError(f"Token exchange failed: {resp.text[:300]}")
    data = resp.json()
    short_token = data["access_token"]
    user_id = str(data.get("user_id", ""))
    print(f"    Short-lived token OK (user_id: {user_id})")
    return short_token, user_id


def get_long_lived_token(short_token):
    """Exchange short-lived for long-lived token (60 days)."""
    print("    Exchanging for long-lived token...")
    resp = httpx.get(
        "https://graph.instagram.com/access_token",
        params={
            "grant_type": "ig_exchange_token",
            "client_secret": APP_SECRET,
            "access_token": short_token,
        },
        timeout=30,
    )
    if resp.status_code != 200:
        print(f"    ERROR: {resp.status_code} {resp.text[:300]}")
        raise RuntimeError(f"Long-lived token exchange failed: {resp.text[:300]}")
    data = resp.json()
    token = data["access_token"]
    days = data.get("expires_in", 0) // 86400
    print(f"    Long-lived token OK ({days} days)")
    return token, days


def get_ig_info(token):
    """Get Instagram account info."""
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
    return {}


def save_to_env(token, ig_id):
    """Save token and account ID to .env."""
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print(f"    .env not found at {env_path}")
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
    print(f"    Saved to {env_path}")


def main():
    global auth_code

    print("\n" + "=" * 55)
    print("  Instagram Business Login - OAuth Flow")
    print("=" * 55 + "\n")

    # Step 1: Generate self-signed cert
    print("[1] Generating SSL certificate for localhost...")
    cert_dir = tempfile.mkdtemp()
    try:
        cert_file, key_file = generate_cert(cert_dir)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"    ERROR: Could not generate SSL cert. Is openssl installed?")
        print(f"    {e}")
        return

    # Step 2: Start HTTPS server
    print("[2] Starting HTTPS server on localhost:5555...")
    try:
        server = http.server.HTTPServer(("localhost", 5555), OAuthHandler)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(cert_file, key_file)
        server.socket = ctx.wrap_socket(server.socket, server_side=True)
    except OSError as e:
        print(f"    ERROR: Could not start server on port 5555: {e}")
        print("    Is another process using this port?")
        return

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print("    Server running.")

    # Step 3: Build and open OAuth URL
    auth_url = (
        f"https://www.instagram.com/oauth/authorize"
        f"?enable_fb_login=0"
        f"&force_authentication=1"
        f"&client_id={APP_ID}"
        f"&redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}"
        f"&scope={SCOPES}"
        f"&response_type=code"
    )

    print(f"\n[3] Opening Instagram authorization in your browser...\n")
    print(f"    If the browser doesn't open, visit this URL:\n")
    print(f"    {auth_url}\n")
    webbrowser.open(auth_url)

    print("    >> Authorize the app in your browser.")
    print("    >> After redirecting, if you see an SSL warning,")
    print("       click 'Advanced' > 'Proceed to localhost'.\n")

    # Also offer manual paste as fallback
    print("    Waiting for redirect (up to 3 minutes)...")
    print("    Or paste the redirect URL here if the server doesn't capture it:\n")

    # Wait with a fallback manual input option
    def wait_for_input():
        global auth_code
        try:
            url = input("    [paste URL or press Enter to keep waiting] ").strip()
            if url and "code=" in url:
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                if "code" in params:
                    auth_code = params["code"][0]
                    server_done.set()
        except EOFError:
            pass

    input_thread = threading.Thread(target=wait_for_input, daemon=True)
    input_thread.start()

    server_done.wait(timeout=180)
    server.shutdown()

    # Clean up cert files
    try:
        os.unlink(cert_file)
        os.unlink(key_file)
        os.rmdir(cert_dir)
    except Exception:
        pass

    if not auth_code:
        print("\n    FAILED: No authorization code received within 3 minutes.")
        return

    # Remove trailing #_ that Instagram sometimes appends
    auth_code = auth_code.rstrip("#_").rstrip("#")

    print(f"\n[4] Code captured! Exchanging for tokens...")
    try:
        short_token, user_id = exchange_code(auth_code)
    except Exception as e:
        print(f"\n    FAILED at token exchange: {e}")
        return

    try:
        long_token, days = get_long_lived_token(short_token)
    except Exception as e:
        print(f"\n    FAILED at long-lived token: {e}")
        return

    # Step 5: Get account info
    print(f"\n[5] Getting Instagram account info...")
    info = get_ig_info(long_token)
    ig_id = str(info.get("user_id", user_id))
    username = info.get("username", "unknown")
    acct_type = info.get("account_type", "unknown")
    print(f"    Account: @{username} (ID: {ig_id}, type: {acct_type})")

    # Step 6: Save
    print(f"\n[6] Saving to .env...")
    save_to_env(long_token, ig_id)

    print(f"\n{'=' * 55}")
    print(f"  SUCCESS!")
    print(f"  Instagram: @{username}")
    print(f"  INSTAGRAM_ACCOUNT_ID = {ig_id}")
    print(f"  Token expires in {days} days")
    print(f"  Saved to .env")
    print(f"{'=' * 55}\n")


if __name__ == "__main__":
    main()
