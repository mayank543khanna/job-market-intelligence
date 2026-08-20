# Power BI Setup — Job Market Intelligence Dashboard

## 1. Connect Power BI to PostgreSQL

1. Make sure `python/etl.py` has run successfully and your Postgres DB is populated.
2. In Power BI Desktop: **Get Data → PostgreSQL database**
3. Server: `localhost` (or your host), Database: `job_market_intel`
4. Import these tables (or write a native SQL query using `sql/analysis_queries.sql`):
   - `postings`
   - `posting_skills`
   - `skills`
   - `companies`
   - `load_log`
5. In Power Query, create relationships: `postings.posting_id` ↔ `posting_skills.posting_id`,
   `posting_skills.skill_id` ↔ `skills.skill_id`, `postings.company_id` ↔ `companies.company_id`.

**No Postgres server handy?** Use `python/quickstart_sqlite_demo.py` to generate
`job_market_demo.sqlite`, then connect via Power BI's SQLite ODBC connector, or
just import the CSVs Power Query can pull straight out of SQLite Browser.

## 2. Recommended pages / visuals

| Page | Visuals |
|---|---|
| **Overview** | KPI cards (total postings, avg max salary, % with salary disclosed), monthly demand trend line, postings-by-location map/bar |
| **Skill Demand** | Top-20 skills bar chart, skill category treemap, skill co-occurrence matrix (use the SQL query output as a table visual or matrix) |
| **Salary Intelligence** | Avg salary by skill (bar), salary band by skill-combo (from query 5), salary by location |
| **My Skill Gap** | Table from query 7 — colored by "Already have" vs "GAP" using conditional formatting, so it visually tells the story: *here's exactly what I should learn next* |
| **Data Quality Log** | `load_log` trend — dupes removed, missing-salary %, missing-description % per run. This page is the one that shows engineering maturity, not just charting. |

## 3. Useful DAX measures

```dax
Total Postings = COUNTROWS(postings)

Avg Max Salary (LPA) =
AVERAGE(postings[salary_max_lpa])

% Postings With Salary Disclosed =
DIVIDE(
    CALCULATE(COUNTROWS(postings), NOT(ISBLANK(postings[salary_max_lpa]))),
    COUNTROWS(postings)
)

Skill Demand Rank =
RANKX(
    ALL(skills[skill_name]),
    CALCULATE(COUNTROWS(posting_skills))
)

MoM Posting Growth % =
VAR CurrentMonth = [Total Postings]
VAR PrevMonth =
    CALCULATE(
        [Total Postings],
        DATEADD('Calendar'[Date], -1, MONTH)
    )
RETURN DIVIDE(CurrentMonth - PrevMonth, PrevMonth)
```

## 4. The "skill gap" visual — the slide that gets remembered

Build a simple table: `skill_name | demand_count | status`, with a background
color rule (green = "Already have", red = "GAP"). Put your own resume skills
into the `my_skills` list in `sql/analysis_queries.sql` (query 7) or
`quickstart_sqlite_demo.py` before running, so this page is genuinely about
*your* stack vs the market — not a generic chart.

This is the visual worth screenshotting for LinkedIn / your resume project
description, and the one to open first in an interview.
