"""
etl.py
------
End-to-end ETL pipeline for the Data Analyst Job Market Intelligence project.

Steps:
1. Extract  -> read raw_job_postings.csv (messy, flat, duplicate-prone)
2. Transform -> dedupe, parse inconsistent dates, parse inconsistent salary
                strings into numeric min/max LPA, normalize location names,
                extract skills from free-text descriptions
3. Load      -> write into the normalized PostgreSQL schema (companies,
                postings, skills, posting_skills) and log the run to
                load_log so data-quality can be tracked over time

Run:
    python etl.py
Requires a running PostgreSQL instance and a .env file (see .env.example).
"""

import os
import re
import sys
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

sys.path.append(os.path.dirname(__file__))
from skill_extraction import extract_skills, skill_category

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "job_market_intel")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

RAW_CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "raw_job_postings.csv")

LOCATION_MAP = {
    "bangalore": "Bangalore", "bengaluru": "Bangalore", "bengaluru, karnataka": "Bangalore",
    "mumbai": "Mumbai", "mumbai, mh": "Mumbai",
    "delhi": "Delhi", "new delhi": "Delhi", "delhi ncr": "Delhi",
    "gurugram": "Gurugram", "gurgaon": "Gurugram",
    "pune": "Pune",
    "hyderabad": "Hyderabad", "hyderabad, tg": "Hyderabad",
    "chennai": "Chennai",
    "remote": "Remote", "remote - india": "Remote",
    "noida": "Noida",
}

DATE_PATTERNS = [
    "%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y", "%b %Y", "%d %B, %Y",
]


def parse_messy_date(raw: str):
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip()
    for fmt in DATE_PATTERNS:
        try:
            dt = datetime.strptime(raw, fmt)
            # "%b %Y" has no day -> default to the 1st, still usable for monthly trend
            return dt.date()
        except ValueError:
            continue
    return None


def parse_salary(raw: str):
    """Extract (min_lpa, max_lpa) from wildly inconsistent salary strings.
    Returns (None, None) if unparseable or blank."""
    if not raw or not isinstance(raw, str) or raw.strip() == "":
        return None, None

    # Normalize: remove currency symbols/words, commas
    cleaned = raw.replace("₹", "").replace("INR", "").replace("Rs", "")
    cleaned = cleaned.replace(",00,000", "").replace(",", "")

    numbers = re.findall(r"\d+(?:\.\d+)?", cleaned)
    numbers = [float(n) for n in numbers]

    if len(numbers) >= 2:
        return min(numbers[0], numbers[1]), max(numbers[0], numbers[1])
    elif len(numbers) == 1:
        return numbers[0], numbers[0]
    return None, None


def normalize_location(raw: str) -> str:
    if not raw or not isinstance(raw, str):
        return "Unknown"
    key = raw.strip().lower()
    return LOCATION_MAP.get(key, raw.strip().title())


def run_etl():
    print(f"Reading raw data from {RAW_CSV_PATH} ...")
    df = pd.read_csv(RAW_CSV_PATH, dtype=str)
    rows_in_raw = len(df)
    print(f"  {rows_in_raw} raw rows loaded")

    # --- Deduplicate (same posting_id scraped more than once) ---
    before = len(df)
    df = df.drop_duplicates(subset=["posting_id"], keep="first")
    duplicates_removed = before - len(df)
    print(f"  Removed {duplicates_removed} duplicate posting_ids")

    # --- Missing-data audit (before we fill/drop anything) ---
    rows_missing_salary = int((df["salary_range"].fillna("").str.strip() == "").sum())
    rows_missing_description = int((df["description"].fillna("").str.strip() == "").sum())

    # --- Transform ---
    df["posted_date_parsed"] = df["posted_date"].apply(parse_messy_date)
    df[["salary_min_lpa", "salary_max_lpa"]] = df["salary_range"].apply(
        lambda x: pd.Series(parse_salary(x))
    )
    df["location_clean"] = df["location"].apply(normalize_location)
    df["skills_found"] = df["description"].apply(extract_skills)

    rows_after_dedup = len(df)

    print("Sample transformed row:")
    print(df[["posting_id", "location_clean", "salary_min_lpa", "salary_max_lpa", "skills_found"]].head(3).to_string())

    return df, {
        "rows_in_raw": rows_in_raw,
        "rows_after_dedup": rows_after_dedup,
        "duplicates_removed": duplicates_removed,
        "rows_missing_salary": rows_missing_salary,
        "rows_missing_description": rows_missing_description,
    }


def load_to_postgres(df: pd.DataFrame, stats: dict):
    conn_str = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    engine = create_engine(conn_str)

    with engine.begin() as conn:
        # --- companies ---
        companies = df["company"].dropna().unique()
        for c in companies:
            conn.execute(
                text("INSERT INTO companies (company_name) VALUES (:c) ON CONFLICT (company_name) DO NOTHING"),
                {"c": c},
            )
        company_ids = {
            row[0]: row[1]
            for row in conn.execute(text("SELECT company_name, company_id FROM companies")).fetchall()
        }

        # --- skills ---
        all_skills = sorted({s for row in df["skills_found"] for s in row})
        for s in all_skills:
            conn.execute(
                text("""INSERT INTO skills (skill_name, skill_category)
                        VALUES (:s, :cat) ON CONFLICT (skill_name) DO NOTHING"""),
                {"s": s, "cat": skill_category(s)},
            )
        skill_ids = {
            row[0]: row[1]
            for row in conn.execute(text("SELECT skill_name, skill_id FROM skills")).fetchall()
        }

        # --- postings ---
        for _, row in df.iterrows():
            conn.execute(
                text("""
                    INSERT INTO postings
                        (posting_id, title, company_id, location_raw, location_clean,
                         posted_date, salary_min_lpa, salary_max_lpa, source, description)
                    VALUES
                        (:pid, :title, :cid, :loc_raw, :loc_clean,
                         :pdate, :smin, :smax, :src, :desc)
                    ON CONFLICT (posting_id) DO NOTHING
                """),
                {
                    "pid": row["posting_id"],
                    "title": row["title"],
                    "cid": company_ids.get(row["company"]),
                    "loc_raw": row["location"],
                    "loc_clean": row["location_clean"],
                    "pdate": row["posted_date_parsed"],
                    "smin": row["salary_min_lpa"],
                    "smax": row["salary_max_lpa"],
                    "src": row["source"],
                    "desc": row["description"],
                },
            )
            for skill_name in row["skills_found"]:
                conn.execute(
                    text("""INSERT INTO posting_skills (posting_id, skill_id)
                            VALUES (:pid, :sid) ON CONFLICT DO NOTHING"""),
                    {"pid": row["posting_id"], "sid": skill_ids[skill_name]},
                )

        # --- audit log ---
        conn.execute(
            text("""
                INSERT INTO load_log
                    (rows_in_raw, rows_after_dedup, duplicates_removed,
                     rows_missing_salary, rows_missing_description, notes)
                VALUES
                    (:rin, :rout, :dupes, :nosal, :nodesc, :notes)
            """),
            {
                "rin": stats["rows_in_raw"],
                "rout": stats["rows_after_dedup"],
                "dupes": stats["duplicates_removed"],
                "nosal": stats["rows_missing_salary"],
                "nodesc": stats["rows_missing_description"],
                "notes": "Automated ETL run",
            },
        )

    print("Load complete: companies, skills, postings, posting_skills, load_log all populated.")


if __name__ == "__main__":
    df, stats = run_etl()
    print("\nStats:", stats)
    try:
        load_to_postgres(df, stats)
    except Exception as e:
        print(f"\n[!] Could not connect to PostgreSQL ({e})")
        print("    Make sure PostgreSQL is running and .env is configured (see .env.example),")
        print("    and that you've run: psql -f sql/schema.sql")
        print("    The cleaned DataFrame was still built successfully in memory above.")
