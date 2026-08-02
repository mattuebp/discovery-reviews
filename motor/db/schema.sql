-- Canonical review storage.
--
-- One row per review, matching the "Data contract" table in CLAUDE.md
-- field-for-field. `dedup_id` is the primary key so the `store` pipeline
-- stage can re-run safely: inserting a review that's already there is an
-- upsert, not a duplicate.
--
-- There is deliberately no separate `apps`/`projects` table yet. A
-- "project" (primary app + competitors) is a config concept that drives and
-- labels the pipeline (see motor/models), not something that needs its own
-- persisted table at this stage.
CREATE TABLE IF NOT EXISTS reviews (
    dedup_id        TEXT PRIMARY KEY,   -- hash of platform+app+author+date+text
    platform        TEXT NOT NULL CHECK (platform IN ('google_play', 'app_store')),
    app_id          TEXT NOT NULL,      -- store package/id, e.g. com.hevy.app
    country         TEXT NOT NULL,      -- storefront, e.g. 'br'
    rating          INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    title           TEXT,               -- can be empty on Google Play
    body            TEXT NOT NULL,
    author_hash     TEXT NOT NULL,      -- pseudonymized PII, never the raw author
    app_version     TEXT,
    review_date     TEXT NOT NULL,      -- ISO 8601
    helpful_votes   INTEGER NOT NULL DEFAULT 0,
    dev_reply       TEXT,               -- developer's reply text, or NULL if none
    lang            TEXT,               -- detected language, e.g. 'pt'
    collected_at    TEXT NOT NULL,      -- ISO 8601 timestamp of when we collected it

    -- Enrichment fields: added by the `enrich` pipeline stage, so they're
    -- NULL/empty on a freshly-normalized, not-yet-enriched review.
    themes              TEXT,     -- JSON array of theme strings, e.g. '["sync","pricing"]'
    sentiment           TEXT,     -- e.g. 'positive' | 'negative' | 'neutral'
    is_feature_request  INTEGER,  -- 0/1/NULL - SQLite has no boolean type
    opportunity_tag     TEXT
);

-- Reviews are almost always looked up per app, so index that access pattern.
CREATE INDEX IF NOT EXISTS idx_reviews_app ON reviews (platform, app_id, country);
