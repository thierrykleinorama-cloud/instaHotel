"""
Manual OAuth flow for Drive readonly access.
Generates a URL, user authorizes, then pastes the redirect URL back.
"""
import json
import sys
import urllib.parse
import requests
import hashlib
import base64
import secrets

# Read client credentials
with open(r"c:\Users\michael\agents-lab\google_credentials.json") as f:
    cred_data = json.load(f)

# Get client_id and client_secret from the credentials file
if "installed" in cred_data:
    client_info = cred_data["installed"]
elif "web" in cred_data:
    client_info = cred_data["web"]
else:
    print("Unknown credentials format", flush=True)
    sys.exit(1)

client_id = client_info["client_id"]
client_secret = client_info["client_secret"]

REDIRECT_URI = "http://localhost:8099/"
SCOPE = "https://www.googleapis.com/auth/drive.readonly"

# Build authorization URL
state = secrets.token_urlsafe(16)
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

print("=" * 70, flush=True)
print("AUTHORIZATION NEEDED", flush=True)
print("=" * 70, flush=True)
print(f"\nOpen this URL in your browser:\n", flush=True)
print(auth_url, flush=True)
print(f"\nAfter authorizing, your browser will redirect to a localhost URL.", flush=True)
print("It may show an error page -- that's FINE.", flush=True)
print("Copy the FULL URL from your browser's address bar and paste it here.", flush=True)
print("It will look like: http://localhost:8099/?state=...&code=...&scope=...", flush=True)
print(flush=True)

redirect_url = input("Paste the redirect URL here: ").strip()

# Parse the authorization code from the redirect URL
parsed = urllib.parse.urlparse(redirect_url)
qs = urllib.parse.parse_qs(parsed.query)

if "code" not in qs:
    print(f"ERROR: No 'code' parameter found in URL. Got: {qs}", flush=True)
    sys.exit(1)

code = qs["code"][0]
print(f"\nGot authorization code: {code[:20]}...", flush=True)

# Exchange code for tokens
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
with open(r"c:\Users\michael\agents-lab\instaHotel\.google_token_drive.json", "w") as f:
    json.dump(drive_token, f, indent=2)
print("Token saved to .google_token_drive.json", flush=True)

# Quick verification
headers = {"Authorization": f"Bearer {result['access_token']}"}
test = requests.get(
    "https://www.googleapis.com/drive/v3/files",
    headers=headers,
    params={"pageSize": 1, "fields": "files(id,name)"}
)
print(f"\nVerification API call: {test.status_code}", flush=True)
if test.status_code == 200:
    print("Drive API access confirmed!", flush=True)
else:
    print(f"Error: {test.text}", flush=True)
