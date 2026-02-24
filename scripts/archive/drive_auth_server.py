"""
Simple OAuth flow with local server on port 8099.
Opens browser automatically and waits for callback.
"""
import json
import sys
import webbrowser
import http.server
import urllib.parse
import requests
import secrets
import threading

# Read client credentials
with open(r"c:\Users\michael\agents-lab\google_credentials.json") as f:
    cred_data = json.load(f)

if "installed" in cred_data:
    client_info = cred_data["installed"]
elif "web" in cred_data:
    client_info = cred_data["web"]
else:
    print("Unknown credentials format", flush=True)
    sys.exit(1)

client_id = client_info["client_id"]
client_secret = client_info["client_secret"]

PORT = 8099
REDIRECT_URI = f"http://localhost:{PORT}/"
SCOPE = "https://www.googleapis.com/auth/drive.readonly"
state = secrets.token_urlsafe(16)

auth_code = [None]  # mutable container

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if "code" in qs:
            auth_code[0] = qs["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorization successful!</h1><p>You can close this tab.</p>")
        else:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Error</h1><p>No code received.</p>")
    
    def log_message(self, format, *args):
        print(f"[server] {format % args}", flush=True)

# Build authorization URL
params = {
    "client_id": client_id,
    "redirect_uri": REDIRECT_URI,
    "response_type": "code",
    "scope": SCOPE,
    "access_type": "offline",
    "prompt": "consent",
    "state": state,
}
auth_url = "https://accounts.google.com/o/oauth2/auth?" + urllib.parse.urlencode(params)

print(f"Starting local server on port {PORT}...", flush=True)
server = http.server.HTTPServer(("localhost", PORT), Handler)
server.timeout = 300  # 5 minutes

print(f"\nOpening browser for authorization...", flush=True)
print(f"URL: {auth_url}\n", flush=True)
webbrowser.open(auth_url)

print("Waiting for authorization callback...", flush=True)

# Handle requests until we get the code or timeout
while auth_code[0] is None:
    server.handle_request()

server.server_close()

if not auth_code[0]:
    print("ERROR: No authorization code received.", flush=True)
    sys.exit(1)

code = auth_code[0]
print(f"\nGot authorization code: {code[:20]}...", flush=True)

# Exchange code for tokens
print("Exchanging code for tokens...", flush=True)
resp = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": client_id,
    "client_secret": client_secret,
    "code": code,
    "grant_type": "authorization_code",
    "redirect_uri": REDIRECT_URI,
})

result = resp.json()
if "access_token" not in result:
    print(f"ERROR: Token exchange failed: {result}", flush=True)
    sys.exit(1)

print("Token exchange successful!", flush=True)

# Save token
drive_token = {
    "token": result["access_token"],
    "refresh_token": result.get("refresh_token", ""),
    "token_uri": "https://oauth2.googleapis.com/token",
    "client_id": client_id,
    "client_secret": client_secret,
    "scopes": [SCOPE],
    "universe_domain": "googleapis.com",
    "account": "",
}
token_path = r"c:\Users\michael\agents-lab\instaHotel\.google_token_drive.json"
with open(token_path, "w") as f:
    json.dump(drive_token, f, indent=2)
print(f"Token saved to {token_path}", flush=True)

# Quick verification
headers = {"Authorization": f"Bearer {result['access_token']}"}
test = requests.get(
    "https://www.googleapis.com/drive/v3/files",
    headers=headers,
    params={"pageSize": 1, "fields": "files(id,name)"}
)
print(f"\nVerification: {test.status_code}", flush=True)
if test.status_code == 200:
    print("Drive API access confirmed!", flush=True)
else:
    print(f"Error: {test.text}", flush=True)

print("\nDone. Now run: python drive_folder_scan.py", flush=True)
