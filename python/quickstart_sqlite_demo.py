"""
quickstart_sqlite_demo.py
--------------------------
Zero-setup demo version of the pipeline. Runs the SAME clean/transform
logic as etl.py but loads into a local SQLite file instead of PostgreSQL,
and immediately prints the key analysis results.

Why this exists: if you're demoing this project live (interview, viva,
walking a recruiter through your screen) you don't want to depend on a
Postgres server being up. This script proves the pipeline logic end-to-end
in about 5 seconds with zero setup. The "real" version for the portfolio
is etl.py + PostgreSQL + Power BI (see README.md) — this is the fast path.

Run:  python quickstart_sqlite_demo.py
"""

import os
import sqlite3
import sys

import pandas as pd

sys.path.append(os.path.dirname(__file__))
from etl import run_etl
from skill_extraction import skill_category

DB_PATH = os.path.join(os.path.dirname(__file__), "job_market_demo.sqlite")


def build_sqlite_db(df: pd.DataFrame):
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("CREATE TABLE postings (posting_id TEXT PRIMARY KEY, title TEXT, company TEXT, location_clean TEXT, posted_date TEXT, salary_min_lpa REAL, salary_max_lpa REAL, source TEXT)")
    cur.execute("CREATE TABLE posting_skills (posting_id TEXT, skill_name TEXT, skill_category TEXT)")

    for _, row in df.iterrows():
        cur.execute(
            "INSERT OR IGNORE INTO postings VALUES (?,?,?,?,?,?,?,?)",
            (row["posting_id"], row["title"], row["company"], row["location_clean"],
             str(row["posted_date_parsed"]) if row["posted_date_parsed"] else None,
             row["salary_min_lpa"], row["salary_max_lpa"], row["source"]),
        )
        for skill in row["skills_found"]:
            cur.execute(
                "INSERT INTO posting_skills VALUES (?,?,?)",
                (row["posting_id"], skill, skill_category(skill)),
            )
    conn.commit()
    return conn


def print_top_skills(conn):
    print("\n=== TOP 10 IN-DEMAND SKILLS ===")
    q = """
        SELECT skill_name, COUNT(*) AS n
        FROM posting_skills
        GROUP BY skill_name
        ORDER BY n DESC
        LIMIT 10
    """
    print(pd.read_sql(q, conn).to_string(index=False))


def print_salary_by_skill(conn):
    print("\n=== AVG MAX SALARY (LPA) BY SKILL (min 10 postings) ===")
    q = """
        SELECT ps.skill_name,
               COUNT(*) AS postings_with_salary,
               ROUND(AVG(p.salary_max_lpa), 1) AS avg_max_lpa
        FROM postings p
        JOIN posting_skills ps ON ps.posting_id = p.posting_id
        WHERE p.salary_max_lpa IS NOT NULL
        GROUP BY ps.skill_name
        HAVING COUNT(*) >= 10
        ORDER BY avg_max_lpa DESC
        LIMIT 10
    """
    print(pd.read_sql(q, conn).to_string(index=False))


def print_demand_by_location(conn):
    print("\n=== DEMAND BY LOCATION ===")
    q = """
        SELECT location_clean, COUNT(*) AS postings_count
        FROM postings
        GROUP BY location_clean
        ORDER BY postings_count DESC
    """
    print(pd.read_sql(q, conn).to_string(index=False))


def print_skill_gap(conn, my_skills):
    print(f"\n=== SKILL GAP vs MY CURRENT STACK {my_skills} ===")
    q = """
        SELECT skill_name, COUNT(*) AS demand_count
        FROM posting_skills
        GROUP BY skill_name
        ORDER BY demand_count DESC
        LIMIT 15
    """
    top = pd.read_sql(q, conn)
    top["status"] = top["skill_name"].apply(lambda s: "Already have" if s in my_skills else "GAP")
    print(top.to_string(index=False))


if __name__ == "__main__":
    df, stats = run_etl()
    print("\nETL stats:", stats)

    conn = build_sqlite_db(df)
    print(f"\nSQLite demo DB built at: {DB_PATH}")

    print_top_skills(conn)
    print_salary_by_skill(conn)
    print_demand_by_location(conn)
    print_skill_gap(conn, my_skills=[
        "Excel", "Power BI", "SQL", "Python",
        "Communication Skills", "Stakeholder Management", "PowerPoint",
    ])

    print("\nDone. Open job_market_demo.sqlite in any SQLite viewer, or point")
    print("Power BI's 'SQLite ODBC' connector at it for a dashboard preview.")
