-- Feedback tables: generated_scenarios, generated_music + feedback columns on creative_jobs & generated_content
-- Run: 2026-03-03

-- 1. Generated scenarios table
CREATE TABLE IF NOT EXISTS generated_scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_media_id UUID REFERENCES media_library(id),
    title TEXT NOT NULL,
    description TEXT,
    motion_prompt TEXT,
    mood TEXT,
    caption_hook TEXT,
    generation_params JSONB DEFAULT '{}',
    model TEXT,
    cost_usd NUMERIC,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'accepted', 'rejected')),
    feedback TEXT,
    rating INTEGER CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. Generated music table
CREATE TABLE IF NOT EXISTS generated_music (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_media_id UUID REFERENCES media_library(id),
    prompt TEXT,
    preset TEXT,
    duration_seconds NUMERIC,
    audio_url TEXT,
    generation_params JSONB DEFAULT '{}',
    model TEXT,
    cost_usd NUMERIC,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'accepted', 'rejected')),
    feedback TEXT,
    rating INTEGER CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- 3. Add feedback columns to creative_jobs (generated videos)
ALTER TABLE creative_jobs ADD COLUMN IF NOT EXISTS feedback TEXT;
ALTER TABLE creative_jobs ADD COLUMN IF NOT EXISTS rating INTEGER CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5));

-- 4. Add feedback columns to generated_content (captions)
ALTER TABLE generated_content ADD COLUMN IF NOT EXISTS feedback TEXT;
ALTER TABLE generated_content ADD COLUMN IF NOT EXISTS rating INTEGER CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5));
