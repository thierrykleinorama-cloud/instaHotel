"""
Google Drive service — auth, list media files, download bytes.

Auth priority (first match wins):
  1. Service account JSON — never expires. Preferred.
     - Local: file at SERVICE_ACCOUNT_FILE
     - Streamlit Cloud: st.secrets["GOOGLE_SERVICE_ACCOUNT"]
  2. User OAuth token (legacy) — expires when in Testing mode.
     - Local: .google_token_drive.json
     - Streamlit Cloud: st.secrets["GOOGLE_DRIVE_TOKEN"]
"""
import io
import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env")

SCOPES = ["https://www.googleapis.com/auth/drive"]
CREDS_FILE = Path(r"c:\Users\michael\agents-lab\google_credentials.json")
TOKEN_FILE = _project_root / ".google_token_drive.json"
SERVICE_ACCOUNT_FILE = _project_root / ".service_account_drive.json"

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

# Singletons — separate services for read (SA-preferred) and write (OAuth-only)
_drive_service = None
_drive_creds = None
_drive_service_write = None
_drive_creds_write = None


def _load_service_account() -> Optional[ServiceAccountCredentials]:
    """Try to build service account credentials from secrets or local file."""
    # Streamlit Cloud
    try:
        import streamlit as st
        sa_json = st.secrets.get("GOOGLE_SERVICE_ACCOUNT")
        if sa_json:
            info = json.loads(sa_json) if isinstance(sa_json, str) else dict(sa_json)
            return ServiceAccountCredentials.from_service_account_info(info, scopes=SCOPES)
    except Exception:
        pass
    # Local file
    if SERVICE_ACCOUNT_FILE.exists():
        return ServiceAccountCredentials.from_service_account_file(
            str(SERVICE_ACCOUNT_FILE), scopes=SCOPES
        )
    return None


def _authenticate_user() -> Credentials:
    """Return user OAuth credentials. Used for WRITES (uploads, folder creation)
    since service accounts have no storage quota on non-Workspace Drives.
    """
    creds = None
    try:
        import streamlit as st
        token_json = st.secrets.get("GOOGLE_DRIVE_TOKEN")
        if token_json:
            info = json.loads(token_json) if isinstance(token_json, str) else dict(token_json)
            creds = Credentials.from_authorized_user_info(info, SCOPES)
    except Exception:
        pass

    if creds is None and TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
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


def _authenticate():
    """Return credentials for READ operations. Prefers service account
    (never expires, but cannot write on non-Workspace Drives). Falls back
    to user OAuth when no service account is configured.
    """
    sa_creds = _load_service_account()
    if sa_creds is not None:
        return sa_creds
    return _authenticate_user()


def _reset_drive_service():
    """Clear cached services so next call re-authenticates."""
    global _drive_service, _drive_creds, _drive_service_write, _drive_creds_write
    _drive_service = None
    _drive_creds = None
    _drive_service_write = None
    _drive_creds_write = None


def get_drive_service():
    """Drive service for READS (list, download). Uses service account when
    configured, else user OAuth. Service accounts don't expire.
    """
    global _drive_service, _drive_creds
    if _drive_service is None or (_drive_creds and _drive_creds.expired):
        _drive_creds = _authenticate()
        _drive_service = build("drive", "v3", credentials=_drive_creds)
    return _drive_service


def get_drive_service_write():
    """Drive service for WRITES (upload, create folder, delete). Always uses
    user OAuth — service accounts have no storage quota on non-Workspace Drives.
    """
    global _drive_service_write, _drive_creds_write
    if _drive_service_write is None or (_drive_creds_write and _drive_creds_write.expired):
        _drive_creds_write = _authenticate_user()
        _drive_service_write = build("drive", "v3", credentials=_drive_creds_write)
    return _drive_service_write


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
    """Download a file from Drive and return its bytes.

    Retries once with fresh credentials on auth errors (stale token).
    """
    for attempt in range(2):
        try:
            service = get_drive_service()
            request = service.files().get_media(fileId=file_id)
            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buffer.getvalue()
        except Exception as exc:
            err_msg = str(exc).lower()
            if attempt == 0 and ("invalid_grant" in err_msg or "expired" in err_msg
                                 or "401" in err_msg or "credentials" in err_msg):
                _reset_drive_service()
                continue
            raise


def classify_media_type(mime_type: str) -> Optional[str]:
    """Return 'image' or 'video' based on MIME type, or None for junk."""
    if mime_type in IMAGE_MIMES:
        return "image"
    if mime_type in VIDEO_MIMES:
        return "video"
    return None


# ---------------------------------------------------------------------------
# Upload helpers — write generated media back to Drive
# ---------------------------------------------------------------------------

def get_or_create_folder(name: str, parent_id: str) -> str:
    """Find or create a folder under parent_id. Returns folder ID."""
    service = get_drive_service_write()
    # Search for existing
    q = (
        f"name = '{name}' and '{parent_id}' in parents "
        f"and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    )
    resp = service.files().list(q=q, fields="files(id)", pageSize=1).execute()
    files = resp.get("files", [])
    if files:
        return files[0]["id"]
    # Create
    meta = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    folder = service.files().create(body=meta, fields="id").execute()
    return folder["id"]


def upload_file_to_drive(
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    folder_id: str,
) -> dict:
    """Upload a file to a specific Drive folder.

    Returns: {"id": file_id, "name": filename, "webViewLink": url}
    """
    service = get_drive_service_write()
    meta = {"name": filename, "parents": [folder_id]}
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=True)
    result = service.files().create(
        body=meta,
        media_body=media,
        fields="id, name, webViewLink",
    ).execute()
    return result


_FOLDER_CACHE: dict[str, str] = {}


def upload_to_main_folder(file_bytes: bytes, filename: str, mime_type: str) -> dict:
    """Upload a user-provided file to the main Drive folder (DRIVE_FOLDER_ID).

    Used by the Upload Media page. Files land alongside the original library —
    no subfolder, since all media are ultimately user uploads.
    """
    folder_id = os.getenv("DRIVE_FOLDER_ID")
    if not folder_id:
        raise ValueError("DRIVE_FOLDER_ID not set")
    return upload_file_to_drive(file_bytes, filename, mime_type, folder_id)


def ensure_generated_folders() -> dict[str, str]:
    """Ensure Generated/Videos, Generated/Music, Generated/Enhanced exist.

    Returns {"videos": folder_id, "music": folder_id, "enhanced": folder_id}
    """
    if _FOLDER_CACHE:
        return _FOLDER_CACHE

    root_id = os.getenv("DRIVE_FOLDER_ID")
    if not root_id:
        raise ValueError("DRIVE_FOLDER_ID not set")

    gen_id = get_or_create_folder("Generated", root_id)
    _FOLDER_CACHE["videos"] = get_or_create_folder("Videos", gen_id)
    _FOLDER_CACHE["music"] = get_or_create_folder("Music", gen_id)
    _FOLDER_CACHE["enhanced"] = get_or_create_folder("Enhanced", gen_id)
    return _FOLDER_CACHE
