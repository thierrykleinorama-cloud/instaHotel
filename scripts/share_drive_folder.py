"""One-off: share the master media Drive folder with the designer as Viewer."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.services.google_drive import get_drive_service_write

FOLDER_ID = "12eYoajc5F8YKEwPmcNrgne8kmxGQG5wt"
EMAIL = "antonicarli@gmail.com"

service = get_drive_service_write()

folder = service.files().get(
    fileId=FOLDER_ID,
    fields="id,name,owners(emailAddress)",
    supportsAllDrives=True,
).execute()
print(f"Folder: {folder['name']} (owner: {folder.get('owners', [{}])[0].get('emailAddress')})")

perm = service.permissions().create(
    fileId=FOLDER_ID,
    body={"type": "user", "role": "reader", "emailAddress": EMAIL},
    sendNotificationEmail=True,
    emailMessage=(
        "Hi Antoni, here is the full Hotel Noucentista media library "
        "(photos + videos). You can browse, preview, or bulk-download from Drive. "
        "New uploads will appear here automatically."
    ),
    supportsAllDrives=True,
    fields="id,emailAddress,role",
).execute()
print(f"Granted: {perm}")
