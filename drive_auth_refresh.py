"""
Try to get drive.readonly access by refreshing the existing token
with the new scope. If that fails, fall back to manual copy-paste OAuth flow.
"""
import json
import sys
import requests

# Read existing token
with open(r"c:\Users\michael\agents-lab\google_credentials.json") as f:
    cred_data = json.load(f)

with open(r"c:\Users\michael\agents-lab\.gws_token.json") as f:
    token_data = json.load(f)

client_id = token_data["client_id"]
client_secret = token_data["client_secret"]
refresh_token = token_data["refresh_token"]

print(f"Client ID: {client_id[:20]}...", flush=True)
print(f"Refresh token: {refresh_token[:20]}...", flush=True)

# Try refreshing -- Google may or may not honor the new scope
resp = requests.post("https://oauth2.googleapis.com/token", data={
    "client_id": client_id,
    "client_secret": client_secret,
    "refresh_token": refresh_token,
    "grant_type": "refresh_token",
    "scope": "https://www.googleapis.com/auth/drive.readonly",
})

print(f"Status: {resp.status_code}", flush=True)
result = resp.json()

if "access_token" in result:
    print("Got access token!", flush=True)
    # Save as a Drive-specific token
    drive_token = {
        "token": result["access_token"],
        "refresh_token": refresh_token,
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": client_id,
        "client_secret": client_secret,
        "scopes": ["https://www.googleapis.com/auth/drive.readonly"],
        "universe_domain": "googleapis.com",
        "account": "",
    }
    with open(r"c:\Users\michael\agents-lab\instaHotel\.google_token_drive.json", "w") as f:
        json.dump(drive_token, f, indent=2)
    print("Token saved to .google_token_drive.json", flush=True)

    # Quick test: list 1 file from root
    headers = {"Authorization": f"Bearer {result['access_token']}"}
    test = requests.get(
        "https://www.googleapis.com/drive/v3/files",
        headers=headers,
        params={"pageSize": 1, "fields": "files(id,name)"}
    )
    print(f"Test API call status: {test.status_code}", flush=True)
    if test.status_code == 200:
        print(f"Test result: {test.json()}", flush=True)
    else:
        print(f"Test error: {test.text}", flush=True)
else:
    print(f"Failed: {result}", flush=True)
    print("\nThe refresh token doesn't grant drive.readonly scope.", flush=True)
    print("You'll need to re-authorize with that scope.", flush=True)
