# Data Analyst Job Market Intelligence Dashboard

**The story:** While job hunting, instead of just applying and waiting, I built
the analytics pipeline I wished existed — one that ingests messy, real-world-style
job posting data, cleans and structures it properly, and answers the exact
questions a job seeker (or a company's talent-analytics team) actually needs
answered: *what skills are in demand, what do they pay, and what's the gap
between what I have and what the market wants?*

This isn't a "load one clean CSV into Power BI" project. It's a full pipeline:
**messy raw data → Python ETL → normalized PostgreSQL database → SQL analysis
→ Power BI dashboard**, mirroring how analytics actually gets built in a real
company rather than a tutorial.

> **Note on data:** Live-scraping job boards violates most sites' Terms of
> Service, so `data/generate_sample_data.py` generates a realistic *synthetic*
> dataset with the same kinds of quality problems real scraped data has —
> duplicate postings, inconsistent date/salary formats, inconsistent location
> casing, missing fields. The cleaning logic in `python/etl.py` is real and
> would work identically against a genuine scraped/API-sourced dataset.

---

## Architecture

```
data/generate_sample_data.py     -> raw_job_postings.csv  (messy, simulated)
            |
            v
python/skill_extraction.py       -> regex-based skill extraction from free text
python/etl.py                    -> clean, dedupe, parse, load into PostgreSQL
            |
            v
sql/schema.sql                   -> normalized schema (companies, postings,
                                     skills, posting_skills, load_log)
sql/analysis_queries.sql         -> co-occurrence, salary bands, trends, skill gap
            |
            v
powerbi/README_PowerBI_Setup.md  -> dashboard build guide + DAX measures
```

## Tech stack

- **Python** (pandas, regex) — ETL, data cleaning, lightweight skill-extraction NLP
- **PostgreSQL** — normalized relational schema, not a flat spreadsheet
- **SQL** — window functions, CTEs, self-joins for co-occurrence analysis
- **Power BI** — live-connected dashboard
- **SQLite** (bonus) — zero-setup demo path for quick walkthroughs

## Quickstart (no Postgres install needed)

```bash
pip install -r requirements.txt
cd data && python generate_sample_data.py && cd ..
cd python && python quickstart_sqlite_demo.py
```

This prints top skills, salary-by-skill, demand-by-location, and your
personal skill-gap analysis straight to the terminal in a few seconds.

## Full setup (PostgreSQL + Power BI, for the real portfolio version)

```bash
pip install -r requirements.txt
cp .env.example .env                     # then fill in your local DB credentials
createdb job_market_intel                # or create it in pgAdmin
psql -d job_market_intel -f sql/schema.sql
cd data && python generate_sample_data.py && cd ..
cd python && python etl.py
```

Then open `sql/analysis_queries.sql` in pgAdmin/DBeaver to explore, and follow
`powerbi/README_PowerBI_Setup.md` to build the dashboard.

## What each layer actually demonstrates

| Layer | What it proves |
|---|---|
| Synthetic messy data generation | Understands what real-world data problems look like (not just working with pre-cleaned Kaggle CSVs) |
| `skill_extraction.py` | Can build a transparent, explainable text-parsing tool — not just call a library |
| `etl.py` | Can design and populate a normalized relational schema, not just dump into one flat table |
| `load_log` table | Thinks about auditability and data-quality tracking over time |
| `analysis_queries.sql` | Comfortable with window functions, CTEs, self-joins — beyond basic SELECT/JOIN |
| Power BI skill-gap page | Turns the whole project into a personal, memorable narrative |

## Resume bullets (ready to paste)

```
Job Market Intelligence Dashboard — Python, PostgreSQL, SQL, Power BI
• Built an end-to-end Python ETL pipeline to clean 750+ simulated job postings,
  resolving duplicate records and inconsistent date/salary formats, and loaded
  results into a normalized PostgreSQL schema (4 related tables).
• Engineered a regex-based skill-extraction module to parse structured skill
  data out of unstructured job description text, covering 28 canonical skills
  across 8 categories.
• Wrote SQL window-function and self-join queries to surface skill
  co-occurrence patterns and salary bands by skill combination, identifying
  the 3 highest-paying skill pairings in the dataset.
• Built a Power BI dashboard connected live to PostgreSQL, including a
  personal skill-gap analysis comparing my own skill set against market
  demand across 20+ tracked skills.
```
Trim to 3 bullets if space is tight — the first and fourth are the strongest pair.

## Extending it further (optional, if you want to go even further)

- Swap the synthetic generator for a real dataset (e.g. via a paid job-board
  API) once you have proper API access — the ETL logic doesn't need to change.
- Add a simple Python script that emails you (via `smtplib`) when a new
  "GAP" skill enters the top-10 demand list — ties back to the
  exception-escalation habit from your internships.
- Add `great_expectations` for formal data-quality validation instead of the
  hand-rolled checks in `etl.py`.
