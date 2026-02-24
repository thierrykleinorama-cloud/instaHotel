"""
Scan a Google Drive folder recursively, categorize files by MIME type,
and print a summary. Read-only -- nothing is modified.
"""

import json
import os
import sys
from collections import defaultdict

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Force unbuffered output
def pr(msg=""):
    print(msg, flush=True)

# ── Config ──────────────────────────────────────────────────────────
FOLDER_ID = "12eYoajc5F8YKEwPmcNrgne8kmxGQG5wt"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
CREDS_FILE = r"c:\Users\michael\agents-lab\google_credentials.json"
TOKEN_FILE = r"c:\Users\michael\agents-lab\instaHotel\.google_token_drive.json"

# ── MIME-type categories ────────────────────────────────────────────
IMAGE_MIMES = {
    "image/jpeg", "image/png", "image/gif", "image/bmp", "image/webp",
    "image/tiff", "image/svg+xml", "image/heif", "image/heic",
}
VIDEO_MIMES = {
    "video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska",
    "video/webm", "video/mpeg", "video/3gpp", "video/x-flv",
}
GOOGLE_NATIVE_MIMES = {
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
    "application/vnd.google-apps.form",
    "application/vnd.google-apps.drawing",
    "application/vnd.google-apps.site",
    "application/vnd.google-apps.script",
    "application/vnd.google-apps.jam",
    "application/vnd.google-apps.map",
}

def categorize(mime: str) -> str:
    if mime in IMAGE_MIMES:
        return "image"
    if mime in VIDEO_MIMES:
        return "video"
    if mime == "application/vnd.google-apps.folder":
        return "folder"
    if mime in GOOGLE_NATIVE_MIMES:
        return "google-native"
    return "other"


def authenticate():
    """Return credentials, creating / refreshing a Drive-specific token."""
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            pr("Refreshing expired token...")
            creds.refresh(Request())
        else:
            pr("Need new authorization. A browser window will open...")
            pr("If the browser doesn't open, copy/paste the URL shown below.")
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=8099, open_browser=True)
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        pr("Token saved.")
    return creds


def list_folder(service, folder_id, path=""):
    """Recursively list all files in folder_id. Yields dicts."""
    page_token = None
    while True:
        resp = service.files().list(
            q=f"'{folder_id}' in parents and trashed = false",
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()

        for f in resp.get("files", []):
            f["_path"] = path + "/" + f["name"]
            if f["mimeType"] == "application/vnd.google-apps.folder":
                yield f
                yield from list_folder(service, f["id"], f["_path"])
            else:
                yield f

        page_token = resp.get("nextPageToken")
        if not page_token:
            break


def human_size(nbytes: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if nbytes < 1024:
            return f"{nbytes:.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:.1f} PB"


def main():
    pr("Authenticating...")
    creds = authenticate()
    service = build("drive", "v3", credentials=creds)

    pr(f"Scanning folder {FOLDER_ID} recursively...")
    pr()
    all_files = list(list_folder(service, FOLDER_ID))

    folders = [f for f in all_files if f["mimeType"] == "application/vnd.google-apps.folder"]
    files = [f for f in all_files if f["mimeType"] != "application/vnd.google-apps.folder"]

    by_cat = defaultdict(list)
    size_by_cat = defaultdict(int)
    mime_counts = defaultdict(int)

    for f in files:
        mime = f["mimeType"]
        cat = categorize(mime)
        by_cat[cat].append(f)
        mime_counts[mime] += 1
        size_by_cat[cat] += int(f.get("size", 0))

    pr("=" * 65)
    pr(f"  GOOGLE DRIVE FOLDER SCAN SUMMARY")
    pr(f"  Folder ID: {FOLDER_ID}")
    pr("=" * 65)
    pr(f"  Total sub-folders : {len(folders)}")
    pr(f"  Total files       : {len(files)}")
    total_size = sum(size_by_cat.values())
    pr(f"  Total size        : {human_size(total_size)}")
    pr("-" * 65)

    pr()
    pr("  COUNT & SIZE BY CATEGORY:")
    for cat in ("image", "video", "google-native", "other"):
        count = len(by_cat[cat])
        size = size_by_cat[cat]
        if count:
            pr(f"    {cat:20s}  {count:5d} files   {human_size(size):>12s}")
    pr()

    pr("  DETAILED MIME BREAKDOWN:")
    for mime, count in sorted(mime_counts.items(), key=lambda x: -x[1]):
        pr(f"    {mime:55s}  {count:5d}")
    pr()

    if folders:
        pr("  SUB-FOLDERS:")
        for f in folders:
            pr(f"    {f['_path']}")
        pr()

    junk = by_cat["other"] + by_cat["google-native"]
    if junk:
        pr("  NON-IMAGE / NON-VIDEO FILES (potential junk):")
        for f in sorted(junk, key=lambda x: x["_path"]):
            size_str = human_size(int(f.get("size", 0))) if f.get("size") else "(native)"
            pr(f"    [{f['mimeType']:45s}]  {size_str:>10s}  {f['_path']}")
        pr()

    pr("  FULL FILE LIST (by path):")
    for f in sorted(files, key=lambda x: x["_path"]):
        cat = categorize(f["mimeType"])
        size_str = human_size(int(f.get("size", 0))) if f.get("size") else "(native)"
        pr(f"    [{cat:14s}] {size_str:>10s}  {f['_path']}")

    pr()
    pr("Done.")


if __name__ == "__main__":
    main()
