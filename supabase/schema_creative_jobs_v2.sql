-- Creative jobs v2: expand job types + add result_url for crash recovery
-- Allows persisting scenario generation results and video/audio output URLs

-- Expand job_type enum to include scenario_generation
ALTER TABLE creative_jobs DROP CONSTRAINT IF EXISTS creative_jobs_job_type_check;
ALTER TABLE creative_jobs ADD CONSTRAINT creative_jobs_job_type_check
  CHECK (job_type IN ('photo_to_video','seasonal_variant','music_gen','video_composite','scenario_generation'));

-- Add result_url for storing Supabase Storage URLs (video/audio output)
ALTER TABLE creative_jobs ADD COLUMN IF NOT EXISTS result_url TEXT;
