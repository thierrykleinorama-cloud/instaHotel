"""One-off end-to-end test of the upload page's backend flow.

Uploads one image and one video via the same code path as the UI,
verifies DB insertion, then cleans up (deletes Drive file + DB row).
"""
import sys
import time
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from src.database import get_supabase, TABLE_MEDIA_LIBRARY
from src.services.google_drive import (
    upload_to_main_folder,
    get_drive_service,
)
from src.services.media_indexer import process_image_bytes, process_video_bytes
from src.services.media_queries import find_duplicate_by_name_size

IMAGE = _root / "test_char_picks" / "pick3_terrace_sunset.jpg"
VIDEO = _root / "test_outputs" / "creative_pool_test" / "1_cat_critic.mp4"

# Use names we can easily spot + clean up
TEST_IMG_NAME = "__upload_test_image__.jpg"
TEST_VID_NAME = "__upload_test_video__.mp4"

assert IMAGE.exists() and VIDEO.exists(), "test assets missing"

results = {}

def cleanup(drive_id: str, filename: str):
    try:
        get_drive_service().files().delete(fileId=drive_id).execute()
        print(f"  [cleanup] Drive file deleted: {drive_id}")
    except Exception as e:
        print(f"  [cleanup] WARN Drive delete failed: {e}")
    try:
        get_supabase().table(TABLE_MEDIA_LIBRARY).delete().eq(
            "drive_file_id", drive_id
        ).execute()
        print(f"  [cleanup] DB row deleted for {filename}")
    except Exception as e:
        print(f"  [cleanup] WARN DB delete failed: {e}")


print("=" * 60)
print("TEST 1: Image upload")
print("=" * 60)
img_bytes = IMAGE.read_bytes()
img_size = len(img_bytes)
print(f"Source: {IMAGE.name}, {img_size/1024:.1f} KB")

# Dup check (should be None)
dup = find_duplicate_by_name_size(TEST_IMG_NAME, img_size)
print(f"Dup check: {dup}")
assert dup is None, "unexpected dup"

print("Uploading to Drive...")
drive_file = upload_to_main_folder(img_bytes, TEST_IMG_NAME, "image/jpeg")
img_drive_id = drive_file["id"]
print(f"Drive ID: {img_drive_id}")

print("Analyzing with Claude Vision...")
t0 = time.time()
row = process_image_bytes(img_bytes, TEST_IMG_NAME, "image/jpeg", img_drive_id, img_size)
print(f"Analysis took {time.time()-t0:.1f}s")
print(f"  category={row.get('category')}, subcat={row.get('subcategory')}")
print(f"  ig_quality={row.get('ig_quality')}, ambiance={row.get('ambiance')}")
print(f"  desc_en={row.get('description_en')}")

# Verify insertion
client = get_supabase()
db_row = client.table(TABLE_MEDIA_LIBRARY).select("*").eq(
    "drive_file_id", img_drive_id
).execute().data
assert db_row, "image not in DB"
assert db_row[0]["status"] == "analyzed"
print(f"DB row confirmed: id={db_row[0]['id'][:8]}..., status={db_row[0]['status']}")

# Dup check now should return the row
dup2 = find_duplicate_by_name_size(TEST_IMG_NAME, img_size)
assert dup2 and dup2["drive_file_id"] == img_drive_id, "dup check failed after insert"
print("Dup check after insert: correctly identifies duplicate")

results["image_ok"] = True
img_drive_id_for_cleanup = img_drive_id

print()
print("=" * 60)
print("TEST 2: Video upload")
print("=" * 60)
vid_bytes = VIDEO.read_bytes()
vid_size = len(vid_bytes)
print(f"Source: {VIDEO.name}, {vid_size/1024/1024:.2f} MB")

print("Uploading to Drive...")
drive_file = upload_to_main_folder(vid_bytes, TEST_VID_NAME, "video/mp4")
vid_drive_id = drive_file["id"]
print(f"Drive ID: {vid_drive_id}")

print("Analyzing with Claude Vision (scene split + per-scene analysis)...")
t0 = time.time()
try:
    row = process_video_bytes(vid_bytes, TEST_VID_NAME, "video/mp4", vid_drive_id, vid_size)
    print(f"Analysis took {time.time()-t0:.1f}s")
    print(f"  category={row.get('category')}, subcat={row.get('subcategory')}")
    print(f"  ig_quality={row.get('ig_quality')}, duration={row.get('duration_seconds')}s")
    print(f"  scenes={len(row.get('scenes') or [])}, aspect={row.get('aspect_ratio')}")
    print(f"  desc_en={row.get('description_en')}")

    db_row = client.table(TABLE_MEDIA_LIBRARY).select("*").eq(
        "drive_file_id", vid_drive_id
    ).execute().data
    assert db_row, "video not in DB"
    assert db_row[0]["status"] == "analyzed"
    print(f"DB row confirmed: id={db_row[0]['id'][:8]}..., status={db_row[0]['status']}")
    results["video_ok"] = True
except Exception as e:
    print(f"VIDEO TEST FAILED: {e}")
    results["video_ok"] = False
    results["video_error"] = str(e)

print()
print("=" * 60)
print("CLEANUP")
print("=" * 60)
cleanup(img_drive_id_for_cleanup, TEST_IMG_NAME)
cleanup(vid_drive_id, TEST_VID_NAME)

print()
print("=" * 60)
print("RESULTS")
print("=" * 60)
for k, v in results.items():
    print(f"  {k}: {v}")
