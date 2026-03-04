-- Batch Creative Pipeline — link creative artifacts to calendar slots
-- Run via Supabase Management API

-- Add calendar_id FK to creative tables (NULL for manual/AI Lab generation)
ALTER TABLE generated_scenarios ADD COLUMN IF NOT EXISTS calendar_id UUID REFERENCES editorial_calendar(id) ON DELETE SET NULL;
ALTER TABLE creative_jobs ADD COLUMN IF NOT EXISTS calendar_id UUID REFERENCES editorial_calendar(id) ON DELETE SET NULL;
ALTER TABLE generated_music ADD COLUMN IF NOT EXISTS calendar_id UUID REFERENCES editorial_calendar(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_scenarios_calendar ON generated_scenarios(calendar_id) WHERE calendar_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_jobs_calendar ON creative_jobs(calendar_id) WHERE calendar_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_music_calendar ON generated_music(calendar_id) WHERE calendar_id IS NOT NULL;

-- Creative pipeline status tracking on calendar slots
ALTER TABLE editorial_calendar ADD COLUMN IF NOT EXISTS creative_status TEXT DEFAULT NULL;
-- Values: NULL (no creative), scenarios_generated, video_generated, music_generated, complete
