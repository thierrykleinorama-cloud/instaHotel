-- Migration: Add drive_file_id to creative_jobs and generated_music tables
-- Purpose: Link generated media (videos, music, composites) to permanent Google Drive files

ALTER TABLE creative_jobs ADD COLUMN IF NOT EXISTS drive_file_id TEXT;
ALTER TABLE generated_music ADD COLUMN IF NOT EXISTS drive_file_id TEXT;
