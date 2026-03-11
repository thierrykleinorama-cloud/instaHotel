-- Migration: Add is_excluded column to media_library
-- Purpose: Allow blacklisting media from gallery, calendar, and all selectors
-- Executed: 2026-03-11

ALTER TABLE media_library ADD COLUMN IF NOT EXISTS is_excluded boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN media_library.is_excluded IS 'If true, media is hidden from gallery, calendar, and all selectors';

-- Exclude IMG_6738.PNG (Instagram screenshot with comments, not hotel content)
UPDATE media_library SET is_excluded = true WHERE file_name ILIKE '%IMG_6738%';
