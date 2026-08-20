-- ============================================================
-- analysis_queries.sql
-- The core analytical layer of the project. Run these after etl.py has
-- populated the database. Each query answers one specific market
-- question a job-seeker (or a company's talent-analytics team) would
-- actually care about.
-- ============================================================

-- 1) TOP IN-DEMAND SKILLS -------------------------------------------------
-- What skills show up most often across all postings?
SELECT
    s.skill_name,
    s.skill_category,
    COUNT(*) AS postings_mentioning
FROM posting_skills ps
JOIN skills s ON s.skill_id = ps.skill_id
GROUP BY s.skill_name, s.skill_category
ORDER BY postings_mentioning DESC
LIMIT 20;


-- 2) SKILL CO-OCCURRENCE -----------------------------------------------
-- Which skill PAIRS most commonly appear together in the same posting?
-- This is the "what should I learn together" insight.
SELECT
    s1.skill_name AS skill_a,
    s2.skill_name AS skill_b,
    COUNT(*) AS postings_with_both
FROM posting_skills ps1
JOIN posting_skills ps2
    ON ps1.posting_id = ps2.posting_id
    AND ps1.skill_id < ps2.skill_id          -- avoid duplicate/reverse pairs
JOIN skills s1 ON s1.skill_id = ps1.skill_id
JOIN skills s2 ON s2.skill_id = ps2.skill_id
GROUP BY s1.skill_name, s2.skill_name
HAVING COUNT(*) >= 5
ORDER BY postings_with_both DESC
LIMIT 20;


-- 3) MONTHLY DEMAND TREND ------------------------------------------------
-- Is demand for Data Analyst roles growing, flat, or shrinking month over month?
SELECT
    DATE_TRUNC('month', posted_date)::DATE AS month,
    COUNT(*) AS postings_count
FROM postings
WHERE posted_date IS NOT NULL
GROUP BY 1
ORDER BY 1;


-- 4) SALARY BANDS BY SKILL -----------------------------------------------
-- Which individual skills are associated with the highest median salary?
-- (Only postings where salary was actually disclosed.)
SELECT
    s.skill_name,
    COUNT(*) AS postings_with_salary,
    ROUND(AVG(p.salary_min_lpa)::numeric, 1) AS avg_min_lpa,
    ROUND(AVG(p.salary_max_lpa)::numeric, 1) AS avg_max_lpa
FROM postings p
JOIN posting_skills ps ON ps.posting_id = p.posting_id
JOIN skills s ON s.skill_id = ps.skill_id
WHERE p.salary_min_lpa IS NOT NULL
GROUP BY s.skill_name
HAVING COUNT(*) >= 10
ORDER BY avg_max_lpa DESC;


-- 5) SALARY BY SKILL COMBINATION (window-function style ranking) --------
-- Does knowing Python + SQL together command a premium over SQL alone?
WITH posting_skill_sets AS (
    SELECT
        p.posting_id,
        p.salary_max_lpa,
        BOOL_OR(s.skill_name = 'Python') AS has_python,
        BOOL_OR(s.skill_name = 'SQL') AS has_sql,
        BOOL_OR(s.skill_name = 'Power BI') AS has_powerbi
    FROM postings p
    JOIN posting_skills ps ON ps.posting_id = p.posting_id
    JOIN skills s ON s.skill_id = ps.skill_id
    WHERE p.salary_max_lpa IS NOT NULL
    GROUP BY p.posting_id, p.salary_max_lpa
)
SELECT
    CASE
        WHEN has_python AND has_sql THEN 'Python + SQL'
        WHEN has_sql AND has_powerbi THEN 'SQL + Power BI'
        WHEN has_sql THEN 'SQL only'
        ELSE 'Other combo'
    END AS skill_combo,
    COUNT(*) AS postings,
    ROUND(AVG(salary_max_lpa)::numeric, 1) AS avg_max_salary_lpa,
    RANK() OVER (ORDER BY AVG(salary_max_lpa) DESC) AS salary_rank
FROM posting_skill_sets
GROUP BY 1
ORDER BY avg_max_salary_lpa DESC;


-- 6) DEMAND BY LOCATION ---------------------------------------------------
SELECT
    location_clean,
    COUNT(*) AS postings_count,
    ROUND(AVG(salary_max_lpa)::numeric, 1) AS avg_max_salary_lpa
FROM postings
GROUP BY location_clean
ORDER BY postings_count DESC;


-- 7) MY SKILL GAP -----------------------------------------------------
-- Compare Mayank's current skill stack (edit the list below) against
-- overall market demand to find the highest-value skill NOT yet held.
WITH my_skills AS (
    SELECT unnest(ARRAY[
        'Excel', 'Power BI', 'SQL', 'Python', 'Communication Skills',
        'Stakeholder Management', 'PowerPoint'
    ]) AS skill_name
)
SELECT
    s.skill_name,
    COUNT(*) AS demand_count,
    CASE WHEN my.skill_name IS NULL THEN 'GAP - not yet on resume'
         ELSE 'Already have' END AS status
FROM posting_skills ps
JOIN skills s ON s.skill_id = ps.skill_id
LEFT JOIN my_skills my ON my.skill_name = s.skill_name
GROUP BY s.skill_name, my.skill_name
ORDER BY demand_count DESC
LIMIT 15;


-- 8) DATA QUALITY / AUDIT TRAIL -----------------------------------------
-- Trend of data quality across ETL runs (mirrors the "audit-ready record
-- keeping" language already on the resume, but engineered instead of manual).
SELECT
    run_timestamp,
    rows_in_raw,
    duplicates_removed,
    ROUND(100.0 * duplicates_removed / NULLIF(rows_in_raw, 0), 2) AS dupe_pct,
    rows_missing_salary,
    rows_missing_description
FROM load_log
ORDER BY run_timestamp DESC;
