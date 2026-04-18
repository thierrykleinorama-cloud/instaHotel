-- InstaHotel: characters table
-- Stores recurring characters (cats, owner) for reference-based video generation.
-- Each character has one canonical reference photo.

CREATE TABLE IF NOT EXISTS characters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identity
    name TEXT NOT NULL UNIQUE,
    species TEXT NOT NULL CHECK (species IN ('cat', 'human', 'other')),
    description TEXT,  -- Physical description for the scenario generator prompt

    -- Canonical reference photo (used for video reference input)
    reference_media_id UUID REFERENCES media_library(id) ON DELETE SET NULL,

    -- Meta
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,  -- Personality, behavior, creative angle notes

    -- Additional reference photos stored directly in Drive (not in media_library)
    extra_reference_drive_ids TEXT[] DEFAULT '{}',

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_characters_name ON characters(name);
CREATE INDEX IF NOT EXISTS idx_characters_species ON characters(species);
CREATE INDEX IF NOT EXISTS idx_characters_active ON characters(is_active);

-- Auto-update timestamp
CREATE OR REPLACE FUNCTION update_characters_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_characters_updated ON characters;
CREATE TRIGGER trg_characters_updated
    BEFORE UPDATE ON characters
    FOR EACH ROW EXECUTE FUNCTION update_characters_timestamp();

-- Optional: tag media with which characters appear in it (for filtering)
ALTER TABLE media_library ADD COLUMN IF NOT EXISTS character_ids UUID[] DEFAULT '{}';
CREATE INDEX IF NOT EXISTS idx_media_character_ids ON media_library USING GIN (character_ids);
