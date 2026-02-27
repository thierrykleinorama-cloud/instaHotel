-- Phase 5a: Instagram Publishing columns on editorial_calendar
-- Run via Supabase Management API or SQL Editor

-- Publishing metadata
ALTER TABLE editorial_calendar
  ADD COLUMN IF NOT EXISTS ig_post_id TEXT,
  ADD COLUMN IF NOT EXISTS ig_permalink TEXT,
  ADD COLUMN IF NOT EXISTS ig_container_id TEXT,
  ADD COLUMN IF NOT EXISTS scheduled_publish_time TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS publish_error TEXT;

-- Index for quick lookup of published/scheduled posts
CREATE INDEX IF NOT EXISTS idx_editorial_calendar_ig_post_id
  ON editorial_calendar (ig_post_id) WHERE ig_post_id IS NOT NULL;
