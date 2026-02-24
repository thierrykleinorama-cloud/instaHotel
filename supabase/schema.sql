-- InstaHotel Phase 1: Media Library Schema
-- Run this in the Supabase SQL Editor (same project as hotelPandL)

CREATE TABLE IF NOT EXISTS media_library (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Google Drive metadata
    drive_file_id TEXT UNIQUE NOT NULL,
    file_name TEXT NOT NULL,
    file_path TEXT,
    mime_type TEXT,
    file_size_bytes BIGINT,
    media_type TEXT NOT NULL CHECK (media_type IN ('image', 'video')),

    -- Claude Vision analysis
    category TEXT,
    subcategory TEXT,
    ambiance TEXT[] DEFAULT '{}',
    season TEXT[] DEFAULT '{}',
    elements TEXT[] DEFAULT '{}',
    ig_quality INTEGER CHECK (ig_quality BETWEEN 1 AND 10),
    aspect_ratio TEXT,
    description_fr TEXT,
    description_en TEXT,

    -- Video-specific fields
    duration_seconds FLOAT,
    scenes JSONB,

    -- Raw AI response for debugging
    analysis_raw JSONB,
    analysis_model TEXT,
    analyzed_at TIMESTAMPTZ,

    -- Status tracking
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'analyzed', 'error', 'skipped')),
    error_message TEXT,

    -- Usage tracking (for later phases)
    used_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Auto-update updated_at on row change
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_media_library_updated_at ON media_library;
CREATE TRIGGER update_media_library_updated_at
    BEFORE UPDATE ON media_library
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_media_library_category ON media_library(category);
CREATE INDEX IF NOT EXISTS idx_media_library_media_type ON media_library(media_type);
CREATE INDEX IF NOT EXISTS idx_media_library_status ON media_library(status);
CREATE INDEX IF NOT EXISTS idx_media_library_ig_quality ON media_library(ig_quality);
CREATE INDEX IF NOT EXISTS idx_media_library_drive_file_id ON media_library(drive_file_id);
