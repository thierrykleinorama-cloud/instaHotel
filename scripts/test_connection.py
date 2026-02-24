"""
Sanity check: verify Supabase, Google Drive, and Claude connections.
Usage: python scripts/test_connection.py
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database import get_supabase, TABLE_MEDIA_LIBRARY


def check_supabase() -> bool:
    """Test Supabase connection and media_library table."""
    try:
        client = get_supabase()
        result = client.table(TABLE_MEDIA_LIBRARY).select("id").limit(1).execute()
        print(f"  Table '{TABLE_MEDIA_LIBRARY}' accessible ({len(result.data)} rows sampled)")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def check_drive() -> bool:
    """Test Google Drive API access."""
    try:
        from src.services.google_drive import get_drive_service
        service = get_drive_service()
        # Quick test: get folder metadata
        import os
        folder_id = os.getenv("DRIVE_FOLDER_ID", "12eYoajc5F8YKEwPmcNrgne8kmxGQG5wt")
        folder = service.files().get(fileId=folder_id, fields="id,name").execute()
        print(f"  Folder: {folder['name']} ({folder['id']})")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def check_claude() -> bool:
    """Test Anthropic API key."""
    try:
        import anthropic
        client = anthropic.Anthropic()
        # Minimal call to verify key
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say OK"}],
        )
        print(f"  Model: {resp.model}, response: {resp.content[0].text.strip()}")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def main():
    print("=" * 50)
    print("  InstaHotel — Connection Check")
    print("=" * 50)

    checks = [
        ("Supabase", check_supabase),
        ("Google Drive", check_drive),
        ("Claude API", check_claude),
    ]

    results = {}
    for name, fn in checks:
        print(f"\n[{name}]")
        results[name] = fn()

    print("\n" + "-" * 50)
    for name, ok in results.items():
        status = "OK" if ok else "FAIL"
        print(f"  {name:20s} [{status}]")
    print("-" * 50)

    all_ok = all(results.values())
    if not all_ok:
        print("\nSome checks failed. Fix issues above before running the indexer.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
