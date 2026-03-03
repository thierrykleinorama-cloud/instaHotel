-- Carousel drafts table for multi-image Instagram posts
CREATE TABLE IF NOT EXISTS carousel_drafts (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    title TEXT,
    media_ids TEXT[] NOT NULL,           -- ordered list of media_library UUIDs
    caption_es TEXT,
    caption_en TEXT,
    caption_fr TEXT,
    hashtags TEXT[],
    status TEXT DEFAULT 'draft',         -- draft / validated / published
    ig_post_id TEXT,
    ig_permalink TEXT,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

-- Index for status filtering
CREATE INDEX IF NOT EXISTS idx_carousel_drafts_status ON carousel_drafts(status);
