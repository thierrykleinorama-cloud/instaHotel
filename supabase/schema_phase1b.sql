-- InstaHotel Phase 1b: Media Explorer Schema Changes
-- Run via Supabase SQL Editor

-- Add manual_notes to media_library for human annotations
ALTER TABLE media_library ADD COLUMN IF NOT EXISTS manual_notes TEXT;

-- Track manual corrections to AI tags
CREATE TABLE IF NOT EXISTS tag_corrections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    media_id UUID REFERENCES media_library(id) ON DELETE CASCADE,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    corrected_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tag_corrections_media_id ON tag_corrections(media_id);
