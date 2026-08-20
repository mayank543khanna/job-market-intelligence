"""
generate_sample_data.py
------------------------
Generates a realistic, deliberately MESSY raw job-postings dataset to simulate
what you'd actually pull from a public job-postings source (duplicate IDs,
inconsistent date formats, missing salaries, inconsistent location casing,
skills buried inside free-text descriptions rather than neat columns).

Why synthetic instead of scraped: live-scraping job boards violates most
sites' Terms of Service and real "Kaggle job postings" datasets go stale
fast. Generating a realistic messy dataset lets the ETL/cleaning layer
(the actual skill being demonstrated) work exactly like it would on real
data, without a ToS or staleness problem.

Run:  python generate_sample_data.py
Output: raw_job_postings.csv (in this folder)
"""

import csv
import random
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()
random.seed(42)
Faker.seed(42)

TITLES = [
    "Data Analyst", "Junior Data Analyst", "Business Analyst",
    "Data Analyst - Entry Level", "Reporting Analyst", "BI Analyst",
    "Data Analyst (Fresher)", "Associate Data Analyst", "Analytics Associate",
    "Product Analyst", "Marketing Data Analyst", "Operations Analyst",
]

LOCATIONS_MESSY = [
    "Bangalore", "bangalore", "Bengaluru", "Bengaluru, Karnataka",
    "Mumbai", "mumbai ", "Mumbai, MH", "Delhi", "New Delhi", "delhi ncr",
    "Gurugram", "Gurgaon", "Pune", "pune", "Hyderabad", "hyderabad, TG",
    "Chennai", "Remote", "remote", "Remote - India", "Noida", "noida ",
]

SKILLS_POOL = [
    "Python", "SQL", "PostgreSQL", "MySQL", "Power BI", "Tableau", "Excel",
    "Advanced Excel", "R", "Pandas", "NumPy", "Statistics", "A/B Testing",
    "Google Sheets", "Looker", "AWS", "Azure", "GCP", "Machine Learning",
    "ETL", "Data Warehousing", "Snowflake", "dbt", "Airflow", "VBA",
    "PowerPoint", "Communication Skills", "Stakeholder Management", "Git",
]

# Realistic skill "clusters" so co-occurrence analysis later actually finds patterns
CLUSTERS = [
    ["SQL", "Power BI", "Excel", "Stakeholder Management"],
    ["Python", "SQL", "PostgreSQL", "ETL", "Airflow"],
    ["Python", "Pandas", "Statistics", "Machine Learning", "A/B Testing"],
    ["Excel", "VBA", "PowerPoint", "Communication Skills"],
    ["SQL", "Tableau", "Data Warehousing", "Snowflake"],
    ["Python", "SQL", "AWS", "dbt", "Git"],
]

COMPANY_SUFFIXES = ["Technologies", "Analytics", "Solutions", "Labs",
                     "Systems", "Consulting", "Digital", "Softwares"]

DATE_FORMATS = [
    lambda d: d.strftime("%Y-%m-%d"),
    lambda d: d.strftime("%d/%m/%Y"),
    lambda d: d.strftime("%d-%b-%Y"),
    lambda d: d.strftime("%b %Y"),
    lambda d: d.strftime("%d %B, %Y"),
]

SALARY_FORMATS = [
    lambda lo, hi: f"₹{lo}L - ₹{hi}L PA",
    lambda lo, hi: f"{lo}-{hi} LPA",
    lambda lo, hi: f"INR {lo},00,000 - {hi},00,000",
    lambda lo, hi: f"Rs {lo}L to {hi}L per annum",
]

DESC_TEMPLATES = [
    "We are looking for a {title} to join our analytics team. Must have hands-on "
    "experience with {skills}. Prior internship experience preferred.",
    "The ideal candidate is proficient in {skills} and can translate business "
    "questions into data-driven answers. Experience with {skills2} is a plus.",
    "Responsibilities include building dashboards, writing queries, and reporting "
    "to leadership. Required: {skills}. Nice to have: {skills2}.",
    "Join our growing data team! Skills needed: {skills}. Freshers with strong "
    "{skills2} fundamentals encouraged to apply.",
    "{title} needed for a fast-paced fintech startup. Core stack: {skills}. "
    "Bonus points for {skills2} exposure.",
]


def random_date_within(days_back=365):
    return datetime.now() - timedelta(days=random.randint(0, days_back))


def messy_row(posting_id):
    title = random.choice(TITLES)
    company = fake.company().replace(",", "") + " " + random.choice(COMPANY_SUFFIXES)
    location = random.choice(LOCATIONS_MESSY)

    cluster = random.choice(CLUSTERS)
    extra_skills = random.sample(SKILLS_POOL, k=random.randint(1, 3))
    primary_skills = list(set(cluster))
    secondary_skills = list(set(extra_skills) - set(primary_skills))

    desc_template = random.choice(DESC_TEMPLATES)
    description = desc_template.format(
        title=title,
        skills=", ".join(primary_skills),
        skills2=", ".join(secondary_skills) if secondary_skills else "SQL",
    )

    posted = random_date_within()
    date_fmt = random.choice(DATE_FORMATS)
    posted_date_str = date_fmt(posted)

    # ~30% of postings have no salary listed at all (realistic)
    if random.random() < 0.30:
        salary_str = ""
    else:
        lo = random.choice([3, 4, 5, 6, 7, 8])
        hi = lo + random.choice([1, 2, 3])
        salary_str = random.choice(SALARY_FORMATS)(lo, hi)

    source = random.choice(["NaukriSim", "LinkedInSim", "IndeedSim", "InternshalaSim"])

    return {
        "posting_id": posting_id,
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "posted_date": posted_date_str,
        "salary_range": salary_str,
        "source": source,
    }


def generate(n=750, duplicate_rate=0.05, null_desc_rate=0.02):
    rows = []
    for i in range(1, n + 1):
        pid = f"JOB{i:05d}"
        rows.append(messy_row(pid))

    # Inject duplicate postings (same posting_id re-scraped from a different source)
    n_dupes = int(n * duplicate_rate)
    for _ in range(n_dupes):
        dupe = dict(random.choice(rows))
        dupe["source"] = random.choice(["NaukriSim", "LinkedInSim", "IndeedSim", "InternshalaSim"])
        rows.append(dupe)

    # Inject a few missing descriptions (real-world scrape failures)
    n_nulls = int(n * null_desc_rate)
    for _ in range(n_nulls):
        row = random.choice(rows)
        row["description"] = ""

    random.shuffle(rows)
    return rows


if __name__ == "__main__":
    data = generate()
    out_path = "raw_job_postings.csv"
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "posting_id", "title", "company", "location",
            "description", "posted_date", "salary_range", "source",
        ])
        writer.writeheader()
        writer.writerows(data)

    print(f"Generated {len(data)} raw (messy) job postings -> {out_path}")
    print("This is the RAW input the ETL pipeline (python/etl.py) will clean.")
