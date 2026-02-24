-- =============================================================
-- InstaHotel — Phase 2: Editorial Strategy Engine
-- =============================================================
-- Run this migration in the Supabase SQL Editor.
-- Depends on: schema.sql (media_library)

-- -----------------------------------------------------------
-- 1. editorial_rules — Weekly posting schedule
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS editorial_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    day_of_week INTEGER NOT NULL CHECK (day_of_week BETWEEN 1 AND 7),  -- 1=Mon..7=Sun
    slot_index INTEGER NOT NULL DEFAULT 1,  -- 1=main, 2=bonus
    default_category TEXT,  -- chambre, commun, exterieur, gastronomie, experience
    preferred_time TIME,
    preferred_format TEXT CHECK (preferred_format IN ('feed', 'story', 'reel')),
    preferred_aspect_ratio TEXT,  -- '1:1', '4:5', '9:16', etc.
    min_quality INTEGER DEFAULT 6 CHECK (min_quality BETWEEN 1 AND 10),
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (day_of_week, slot_index)
);

-- Auto-update updated_at
CREATE OR REPLACE FUNCTION update_editorial_rules_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_editorial_rules_updated ON editorial_rules;
CREATE TRIGGER trg_editorial_rules_updated
    BEFORE UPDATE ON editorial_rules
    FOR EACH ROW EXECUTE FUNCTION update_editorial_rules_timestamp();

-- -----------------------------------------------------------
-- 2. seasonal_themes — Date ranges with editorial context
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS seasonal_themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    theme_name TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    season TEXT,  -- printemps, ete, automne, hiver
    preferred_ambiances TEXT[] DEFAULT '{}',
    preferred_elements TEXT[] DEFAULT '{}',
    editorial_tone TEXT,
    cta_focus TEXT,
    hashtags TEXT[] DEFAULT '{}',
    priority INTEGER DEFAULT 1,  -- higher wins on overlap
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE OR REPLACE FUNCTION update_seasonal_themes_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_seasonal_themes_updated ON seasonal_themes;
CREATE TRIGGER trg_seasonal_themes_updated
    BEFORE UPDATE ON seasonal_themes
    FOR EACH ROW EXECUTE FUNCTION update_seasonal_themes_timestamp();

-- Index for date-range lookups
CREATE INDEX IF NOT EXISTS idx_seasonal_themes_dates
    ON seasonal_themes (start_date, end_date)
    WHERE is_active = TRUE;

-- -----------------------------------------------------------
-- 3. editorial_calendar — Generated posting calendar
-- -----------------------------------------------------------
CREATE TABLE IF NOT EXISTS editorial_calendar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    post_date DATE NOT NULL,
    time_slot TIME,
    slot_index INTEGER NOT NULL DEFAULT 1,

    -- Link to rule
    rule_id UUID REFERENCES editorial_rules(id) ON DELETE SET NULL,
    target_category TEXT,
    target_format TEXT,

    -- Link to seasonal theme
    theme_id UUID REFERENCES seasonal_themes(id) ON DELETE SET NULL,
    season_context TEXT,
    theme_name TEXT,

    -- Scored media assignment
    media_id UUID REFERENCES media_library(id) ON DELETE SET NULL,
    media_score NUMERIC(5, 2),
    score_breakdown JSONB,

    -- Workflow status
    status TEXT DEFAULT 'planned' CHECK (status IN ('planned', 'generated', 'validated', 'published', 'skipped')),

    -- Manual overrides
    manual_media_id UUID REFERENCES media_library(id) ON DELETE SET NULL,
    manual_notes TEXT,

    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (post_date, slot_index)
);

CREATE OR REPLACE FUNCTION update_editorial_calendar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_editorial_calendar_updated ON editorial_calendar;
CREATE TRIGGER trg_editorial_calendar_updated
    BEFORE UPDATE ON editorial_calendar
    FOR EACH ROW EXECUTE FUNCTION update_editorial_calendar_timestamp();

-- Indexes for calendar queries
CREATE INDEX IF NOT EXISTS idx_editorial_calendar_date
    ON editorial_calendar (post_date);
CREATE INDEX IF NOT EXISTS idx_editorial_calendar_status
    ON editorial_calendar (status);
CREATE INDEX IF NOT EXISTS idx_editorial_calendar_media
    ON editorial_calendar (media_id);

-- =============================================================
-- DEFAULT DATA
-- =============================================================

-- 7 daily slots + 2 weekend bonus slots = 9 rows
INSERT INTO editorial_rules (day_of_week, slot_index, default_category, preferred_time, preferred_format, preferred_aspect_ratio, min_quality, notes)
VALUES
    (1, 1, 'chambre',       '10:00', 'feed',  '4:5', 7, 'Monday — Room showcase'),
    (2, 1, 'gastronomie',   '12:00', 'feed',  '4:5', 7, 'Tuesday — Food & dining'),
    (3, 1, 'commun',        '10:00', 'feed',  '4:5', 6, 'Wednesday — Common areas'),
    (4, 1, 'experience',    '11:00', 'reel',  '9:16', 7, 'Thursday — Experiences & activities'),
    (5, 1, 'exterieur',     '10:00', 'feed',  '4:5', 7, 'Friday — Exterior & surroundings'),
    (6, 1, 'chambre',       '10:00', 'feed',  '1:1', 6, 'Saturday — Lifestyle'),
    (7, 1, 'exterieur',     '10:00', 'feed',  '4:5', 7, 'Sunday — Destination highlight'),
    -- Weekend bonus stories
    (6, 2, 'gastronomie',   '18:00', 'story', '9:16', 5, 'Saturday PM — Behind the scenes'),
    (7, 2, 'experience',    '17:00', 'story', '9:16', 5, 'Sunday PM — Guest moment')
ON CONFLICT (day_of_week, slot_index) DO NOTHING;

-- 4 seasons + 2 events = 6 rows
INSERT INTO seasonal_themes (theme_name, start_date, end_date, season, preferred_ambiances, preferred_elements, editorial_tone, cta_focus, hashtags, priority)
VALUES
    (
        'Printemps Méditerranéen',
        '2026-03-21', '2026-06-20',
        'printemps',
        ARRAY['lumineux', 'naturel', 'colore'],
        ARRAY['terrasse', 'jardin', 'fleurs', 'vue_mer'],
        'Fresh, renewal, outdoor living',
        'book_now',
        ARRAY['#SpringInSitges', '#MediterraneanSpring', '#HotelNoucentista', '#SitgesSpring', '#CostaGarraf'],
        1
    ),
    (
        'Été & Plage',
        '2026-06-21', '2026-09-22',
        'ete',
        ARRAY['lumineux', 'festif', 'mediterraneen'],
        ARRAY['piscine', 'plage', 'terrasse', 'soleil', 'vue_mer'],
        'Vibrant, summer energy, fun',
        'link_bio',
        ARRAY['#SummerInSitges', '#BeachLife', '#HotelNoucentista', '#MediterraneanSummer', '#SitgesBeach'],
        1
    ),
    (
        'Automne Culturel',
        '2026-09-23', '2026-12-20',
        'automne',
        ARRAY['chaleureux', 'intime', 'elegant'],
        ARRAY['cheminee', 'bibliotheque', 'vin', 'art'],
        'Cozy, cultural, wine season',
        'dm',
        ARRAY['#AutumnInSitges', '#CulturalEscape', '#HotelNoucentista', '#WineSeason', '#CostaGarraf'],
        1
    ),
    (
        'Hiver Cosy',
        '2025-12-21', '2026-03-20',
        'hiver',
        ARRAY['chaleureux', 'intime', 'romantique', 'luxueux'],
        ARRAY['cheminee', 'spa', 'lit', 'couverture'],
        'Warm, intimate, slow living',
        'book_now',
        ARRAY['#WinterEscape', '#CosySitges', '#HotelNoucentista', '#SlowTravel', '#WinterSun'],
        1
    ),
    (
        'Festival du Film de Sitges',
        '2026-10-08', '2026-10-18',
        'automne',
        ARRAY['festif', 'colore', 'moderne'],
        ARRAY['cinema', 'terrasse', 'nuit', 'art'],
        'Exciting, cinematic, exclusive',
        'link_bio',
        ARRAY['#SitgesFilmFestival', '#SitgesFestival', '#HotelNoucentista', '#FilmFestival', '#SitgesCinema'],
        10
    ),
    (
        'Noël & Nouvel An',
        '2026-12-15', '2027-01-06',
        'hiver',
        ARRAY['festif', 'chaleureux', 'luxueux', 'romantique'],
        ARRAY['decoration_noel', 'cheminee', 'champagne', 'gastronomie'],
        'Festive, magical, celebration',
        'book_now',
        ARRAY['#ChristmasInSitges', '#NYESitges', '#HotelNoucentista', '#FestiveSeason', '#HolidayEscape'],
        10
    )
ON CONFLICT DO NOTHING;
