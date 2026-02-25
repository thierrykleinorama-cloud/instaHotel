-- =============================================================
-- InstaHotel — Phase 3: Content Assembly (Caption Generation)
-- =============================================================
-- Run this migration in the Supabase SQL Editor.
-- Depends on: schema_phase2.sql (editorial_calendar, media_library)

-- -----------------------------------------------------------
-- 1. generated_content — AI-generated captions per calendar slot
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS generated_content (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Link to calendar slot (multiple candidates per slot allowed)
    calendar_id UUID NOT NULL REFERENCES editorial_calendar(id) ON DELETE CASCADE,
    media_id UUID REFERENCES media_library(id) ON DELETE SET NULL,

    -- Captions: short variant x 3 languages
    caption_short_es TEXT,
    caption_short_en TEXT,
    caption_short_fr TEXT,

    -- Captions: storytelling variant x 3 languages
    caption_story_es TEXT,
    caption_story_en TEXT,
    caption_story_fr TEXT,

    -- Hashtags
    hashtags TEXT[] DEFAULT '{}',

    -- User selection
    selected_variant TEXT CHECK (selected_variant IN ('short', 'storytelling')),
    selected_language TEXT CHECK (selected_language IN ('es', 'en', 'fr')),

    -- AI usage tracking
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd NUMERIC(8, 6),

    -- Generation method & params (extensible for future methods)
    generation_params JSONB DEFAULT '{}',

    -- Workflow
    content_status TEXT DEFAULT 'draft' CHECK (content_status IN ('draft', 'edited', 'approved')),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_generated_content_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_generated_content_updated ON generated_content;
CREATE TRIGGER trg_generated_content_updated
    BEFORE UPDATE ON generated_content
    FOR EACH ROW EXECUTE FUNCTION update_generated_content_timestamp();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_generated_content_calendar
    ON generated_content (calendar_id);
CREATE INDEX IF NOT EXISTS idx_generated_content_status
    ON generated_content (content_status);

-- -----------------------------------------------------------
-- 2. Alter editorial_calendar — add content_id FK + new status
-- -----------------------------------------------------------

-- Add content_id column pointing to the selected generated_content
ALTER TABLE editorial_calendar
    ADD COLUMN IF NOT EXISTS content_id UUID REFERENCES generated_content(id) ON DELETE SET NULL;

-- Expand status CHECK to include 'content_ready'
-- Drop old constraint and recreate with new value
ALTER TABLE editorial_calendar
    DROP CONSTRAINT IF EXISTS editorial_calendar_status_check;

ALTER TABLE editorial_calendar
    ADD CONSTRAINT editorial_calendar_status_check
    CHECK (status IN ('planned', 'generated', 'content_ready', 'validated', 'published', 'skipped'));

CREATE INDEX IF NOT EXISTS idx_editorial_calendar_content
    ON editorial_calendar (content_id);
