-- InstaHotel V2: posts table
-- Central entity for Generate -> Review -> Publish flow
-- Run via Supabase Management API (not PostgREST)

CREATE TABLE IF NOT EXISTS posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Content type / route
    post_type TEXT NOT NULL CHECK (post_type IN ('feed','carousel','reel-kling','reel-veo','reel-slideshow')),

    -- Source media (base photo from media_library)
    media_id UUID REFERENCES media_library(id) ON DELETE SET NULL,

    -- Editorial context
    category TEXT,
    season TEXT,
    theme_name TEXT,
    tone TEXT DEFAULT 'default',

    -- Captions (denormalized — no FK to generated_content)
    caption_es TEXT,
    caption_en TEXT,
    caption_fr TEXT,
    hashtags TEXT[] DEFAULT '{}',

    -- Creative artifact links (nullable — populated as generation progresses)
    scenario_id UUID,
    video_job_id UUID,
    music_id UUID,
    carousel_draft_id UUID,

    -- Workflow status
    status TEXT DEFAULT 'draft' CHECK (status IN (
        'draft',       -- generation in progress or not started
        'review',      -- all artifacts generated, awaiting human review
        'approved',    -- human approved, ready to publish
        'discarded',   -- human rejected (with feedback)
        'published',   -- published to IG
        'failed'       -- publish attempt failed
    )),
    discard_feedback TEXT,

    -- Publishing metadata
    ig_post_id TEXT,
    ig_permalink TEXT,
    published_at TIMESTAMPTZ,
    publish_error TEXT,

    -- Batch tracking
    batch_id UUID,
    total_cost_usd NUMERIC(10,4) DEFAULT 0,
    generation_source TEXT DEFAULT 'individual' CHECK (generation_source IN ('batch','individual')),

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_batch ON posts(batch_id);
CREATE INDEX IF NOT EXISTS idx_posts_type ON posts(post_type);
CREATE INDEX IF NOT EXISTS idx_posts_media ON posts(media_id);
CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC);

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_posts_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_posts_updated ON posts;
CREATE TRIGGER trg_posts_updated
    BEFORE UPDATE ON posts
    FOR EACH ROW EXECUTE FUNCTION update_posts_timestamp();
