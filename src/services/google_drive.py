"""
Google Drive service — OAuth, list media files, download bytes.
Local dev: uses project-local token file (.google_token_drive.json).
Streamlit Cloud: reads token JSON from st.secrets["GOOGLE_DRIVE_TOKEN"].
"""
import io
import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env")

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
CREDS_FILE = Path(r"c:\Users\michael\agents-lab\google_credentials.json")
TOKEN_FILE = _project_root / ".google_token_drive.json"

# MIME types we want to process
IMAGE_MIMES = {
    "image/jpeg", "image/png", "image/gif", "image/bmp", "image/webp",
    "image/tiff", "image/heif", "image/heic",
}
VIDEO_MIMES = {
    "video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska",
    "video/webm", "video/mpeg", "video/3gpp",
}
MEDIA_MIMES = IMAGE_MIMES | VIDEO_MIMES

# Singleton
_drive_service = None


def _authenticate() -> Credentials:
    """Return credentials, creating/refreshing token as needed.

    On Streamlit Cloud: reads token JSON from st.secrets["GOOGLE_DRIVE_TOKEN"].
    Locally: uses the project-local token file.
    """
    creds = None

    # Try Streamlit Cloud secrets first
    try:
        import streamlit as st
        token_json = st.secrets.get("GOOGLE_DRIVE_TOKEN")
        if token_json:
            info = json.loads(token_json) if isinstance(token_json, str) else dict(token_json)
            creds = Credentials.from_authorized_user_info(info, SCOPES)
    except Exception:
        pass

    # Fall back to local token file
    if creds is None and TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # Persist refreshed token locally if possible
            try:
                TOKEN_FILE.write_text(creds.to_json())
            except Exception:
                pass
        else:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=8099, open_browser=True)
            TOKEN_FILE.write_text(creds.to_json())
    return creds


def get_drive_service():
    """Get or create Google Drive API service (singleton)."""
    global _drive_service
    if _drive_service is None:
        creds = _authenticate()
        _drive_service = build("drive", "v3", credentials=creds)
    return _drive_service


def list_media_files(folder_id: Optional[str] = None) -> list[dict]:
    """
    Recursively list all image and video files in the Drive folder.
    Returns list of dicts with: id, name, mimeType, size, modifiedTime, _path.
    Filters out non-media files (PDFs, Excel, etc).
    """
    if folder_id is None:
        folder_id = os.getenv("DRIVE_FOLDER_ID")
    if not folder_id:
        raise ValueError("DRIVE_FOLDER_ID not set")

    service = get_drive_service()
    all_files = []

    def _scan(fid: str, path: str = ""):
        page_token = None
        while True:
            resp = service.files().list(
                q=f"'{fid}' in parents and trashed = false",
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime)",
                pageSize=1000,
                pageToken=page_token,
            ).execute()

            for f in resp.get("files", []):
                f["_path"] = path + "/" + f["name"]
                if f["mimeType"] == "application/vnd.google-apps.folder":
                    _scan(f["id"], f["_path"])
                elif f["mimeType"] in MEDIA_MIMES:
                    all_files.append(f)

            page_token = resp.get("nextPageToken")
            if not page_token:
                break

    _scan(folder_id)
    return all_files


def download_file_bytes(file_id: str) -> bytes:
    """Download a file from Drive and return its bytes."""
    service = get_drive_service()
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue()


def classify_media_type(mime_type: str) -> Optional[str]:
    """Return 'image' or 'video' based on MIME type, or None for junk."""
    if mime_type in IMAGE_MIMES:
        return "image"
    if mime_type in VIDEO_MIMES:
        return "video"
    return None
