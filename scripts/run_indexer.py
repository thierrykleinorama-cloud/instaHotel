"""
CLI for the media indexer.
Usage:
  python scripts/run_indexer.py                    # index all
  python scripts/run_indexer.py --limit 5          # index first 5 files
  python scripts/run_indexer.py --dry-run          # download but don't call Claude
  python scripts/run_indexer.py --reindex-errors   # retry failed files
  python scripts/run_indexer.py --folder-id XYZ    # custom folder ID
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.media_indexer import run_indexer


def main():
    parser = argparse.ArgumentParser(description="InstaHotel Media Indexer")
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Max number of files to process"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Download files but don't call Claude Vision"
    )
    parser.add_argument(
        "--reindex-errors", action="store_true",
        help="Re-process files that previously failed"
    )
    parser.add_argument(
        "--folder-id", type=str, default=None,
        help="Google Drive folder ID (overrides .env)"
    )
    args = parser.parse_args()

    print("=" * 50)
    print("  InstaHotel Media Indexer")
    print("=" * 50)
    if args.dry_run:
        print("  MODE: Dry run (no Claude calls)")
    if args.limit:
        print(f"  LIMIT: {args.limit} files")
    if args.reindex_errors:
        print("  REINDEX: Error files will be retried")
    print()

    stats = run_indexer(
        folder_id=args.folder_id,
        limit=args.limit,
        dry_run=args.dry_run,
        reindex_errors=args.reindex_errors,
    )

    return 0 if stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
