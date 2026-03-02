-- Destination content: add focus columns to editorial_rules and editorial_calendar
-- Run: 2026-03-02

ALTER TABLE editorial_rules ADD COLUMN IF NOT EXISTS focus TEXT DEFAULT 'hotel'
    CHECK (focus IN ('hotel', 'destination'));

ALTER TABLE editorial_calendar ADD COLUMN IF NOT EXISTS focus TEXT DEFAULT 'hotel';
ALTER TABLE editorial_calendar ADD COLUMN IF NOT EXISTS destination_topic TEXT;
