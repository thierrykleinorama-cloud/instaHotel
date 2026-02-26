-- Phase 3 extension: Reel caption variant columns
-- Run in Supabase SQL Editor after schema_phase3.sql

ALTER TABLE generated_content ADD COLUMN IF NOT EXISTS caption_reel_es TEXT;
ALTER TABLE generated_content ADD COLUMN IF NOT EXISTS caption_reel_en TEXT;
ALTER TABLE generated_content ADD COLUMN IF NOT EXISTS caption_reel_fr TEXT;

-- Update variant check to include 'reel'
ALTER TABLE generated_content DROP CONSTRAINT IF EXISTS generated_content_selected_variant_check;
ALTER TABLE generated_content ADD CONSTRAINT generated_content_selected_variant_check
  CHECK (selected_variant IN ('short', 'storytelling', 'reel'));
