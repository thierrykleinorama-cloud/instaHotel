"""Refresh Google Drive OAuth token interactively."""
import json
import webbrowser
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]
CREDS_PATH = Path("c:/Users/michael/agents-lab/google_credentials.json")
TOKEN_PATH = Path(__file__).resolve().parent.parent / ".google_token_drive.json"

flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_PATH), SCOPES)
creds = flow.run_local_server(
    port=8893,
    open_browser=True,
    prompt="consent",
    success_message="Token refreshed! You can close this tab.",
)

with open(TOKEN_PATH, "w") as f:
    json.dump(json.loads(creds.to_json()), f, indent=2)

print(f"\nToken saved to {TOKEN_PATH}")
print("Done!")
