-- Phase 3c + 2.5C: Creative transforms + tone variants
-- Adds parent_media_id lineage, creative_jobs async tracking

-- media_library: creative transform lineage
ALTER TABLE media_library ADD COLUMN IF NOT EXISTS parent_media_id UUID REFERENCES media_library(id);
ALTER TABLE media_library ADD COLUMN IF NOT EXISTS generation_method TEXT;
ALTER TABLE media_library ADD COLUMN IF NOT EXISTS generation_cost_usd NUMERIC(8,6);
CREATE INDEX IF NOT EXISTS idx_media_parent ON media_library(parent_media_id) WHERE parent_media_id IS NOT NULL;

-- creative_jobs: async job tracking for video/music generation
CREATE TABLE IF NOT EXISTS creative_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source_media_id UUID NOT NULL REFERENCES media_library(id),
  result_media_id UUID REFERENCES media_library(id),
  job_type TEXT NOT NULL CHECK (job_type IN ('photo_to_video','seasonal_variant','music_gen','video_composite')),
  provider TEXT NOT NULL,
  provider_job_id TEXT,
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending','running','completed','failed')),
  params JSONB DEFAULT '{}',
  cost_usd NUMERIC(8,6),
  error_message TEXT,
  created_at TIMESTAMPTZ DEFAULT now(),
  completed_at TIMESTAMPTZ
);
