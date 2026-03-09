-- Content Routing Migration
-- Links carousel_drafts to calendar slots, adds feedback columns.
-- Run via Supabase Management API.

-- Link carousels to calendar slots
ALTER TABLE carousel_drafts ADD COLUMN IF NOT EXISTS calendar_id UUID REFERENCES editorial_calendar(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_carousel_calendar ON carousel_drafts(calendar_id) WHERE calendar_id IS NOT NULL;

-- Feedback columns (may already exist from earlier migration — IF NOT EXISTS handles it)
ALTER TABLE carousel_drafts ADD COLUMN IF NOT EXISTS feedback TEXT;
ALTER TABLE carousel_drafts ADD COLUMN IF NOT EXISTS rating INTEGER;
