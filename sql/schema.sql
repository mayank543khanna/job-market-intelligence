-- ============================================================
-- schema.sql
-- Normalized schema for the Data Analyst Job Market Intelligence project.
-- Design goal: raw postings are messy/flat; this schema splits them into
-- companies, postings, skills, and a posting_skills junction table so we
-- can run real relational analysis (co-occurrence, demand trends, salary
-- bands by skill combo) instead of just filtering a flat CSV.
-- ============================================================

DROP TABLE IF EXISTS posting_skills CASCADE;
DROP TABLE IF EXISTS postings CASCADE;
DROP TABLE IF EXISTS companies CASCADE;
DROP TABLE IF EXISTS skills CASCADE;
DROP TABLE IF EXISTS load_log CASCADE;

CREATE TABLE companies (
    company_id      SERIAL PRIMARY KEY,
    company_name    TEXT NOT NULL UNIQUE
);

CREATE TABLE skills (
    skill_id        SERIAL PRIMARY KEY,
    skill_name      TEXT NOT NULL UNIQUE,
    skill_category  TEXT  -- e.g. 'Programming', 'BI Tool', 'Database', 'Soft Skill'
);

CREATE TABLE postings (
    posting_id      TEXT PRIMARY KEY,        -- natural key from source (e.g. JOB00123)
    title           TEXT NOT NULL,
    company_id      INTEGER REFERENCES companies(company_id),
    location_raw    TEXT,
    location_clean  TEXT,                    -- normalized city name
    posted_date     DATE,
    salary_min_lpa  NUMERIC(5,2),             -- lakhs per annum
    salary_max_lpa  NUMERIC(5,2),
    source          TEXT,
    description     TEXT,
    loaded_at       TIMESTAMP DEFAULT NOW()
);

CREATE TABLE posting_skills (
    posting_id      TEXT REFERENCES postings(posting_id) ON DELETE CASCADE,
    skill_id        INTEGER REFERENCES skills(skill_id) ON DELETE CASCADE,
    PRIMARY KEY (posting_id, skill_id)
);

-- Tracks every ETL run so data-quality trends over time can be shown
-- (same "audit trail" thinking used in the escalation/QA project idea).
CREATE TABLE load_log (
    load_id             SERIAL PRIMARY KEY,
    run_timestamp        TIMESTAMP DEFAULT NOW(),
    rows_in_raw          INTEGER,
    rows_after_dedup      INTEGER,
    duplicates_removed    INTEGER,
    rows_missing_salary   INTEGER,
    rows_missing_description INTEGER,
    notes                 TEXT
);

-- Helpful indexes for the analysis queries
CREATE INDEX idx_postings_date ON postings(posted_date);
CREATE INDEX idx_postings_location ON postings(location_clean);
CREATE INDEX idx_posting_skills_skill ON posting_skills(skill_id);
