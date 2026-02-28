"""Generate captions with reel variant for a video calendar slot."""
import sys; sys.path.insert(0, ".")
from src.database import get_supabase
from src.services.content_generator import generate_for_slot

sb = get_supabase()

cr = sb.table("editorial_calendar").select("*").eq("post_date", "2026-02-27").eq("slot_index", 1).limit(1).execute()
entry = cr.data[0]
mid = entry.get("manual_media_id") or entry.get("media_id")
print(f"Entry: {entry['post_date']} S{entry['slot_index']} | media={mid[:12]}...")

result = generate_for_slot(entry=entry, model="claude-sonnet-4-6")
if result:
    print(f"Content ID: {result['id']}")
    print(f"Short ES: {(result.get('caption_short_es') or '')[:100]}...")
    print(f"Reel ES:  {result.get('caption_reel_es', '(none)')}")
    print(f"Reel EN:  {result.get('caption_reel_en', '(none)')}")
    print(f"Reel FR:  {result.get('caption_reel_fr', '(none)')}")
    print(f"Cost: ${result.get('cost_usd', 0):.4f}")
else:
    print("Generation failed!")
