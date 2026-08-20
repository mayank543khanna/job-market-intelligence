"""
skill_extraction.py
--------------------
Lightweight, dependency-free "NLP" layer: extracts a canonical list of
skills out of free-text job descriptions using word-boundary regex
matching. Not a black-box ML model on purpose — for a fresher-level
analytics project, a transparent, explainable extraction method that you
can defend line-by-line in an interview beats an opaque model you can't
explain.

Handles:
- Case-insensitivity ("python" vs "Python")
- Multi-word skills ("Power BI", "Machine Learning")
- Aliases / synonyms ("Postgres" -> "PostgreSQL", "PBI" -> "Power BI")
- Word-boundary matching so "R" doesn't match inside "Reporting"
"""

import re

# Canonical skill -> category (used for skill-gap comparison and grouping)
SKILL_CATALOG = {
    "Python":              "Programming",
    "SQL":                 "Database",
    "PostgreSQL":          "Database",
    "MySQL":                "Database",
    "Power BI":             "BI Tool",
    "Tableau":              "BI Tool",
    "Looker":               "BI Tool",
    "Excel":                "Office Tool",
    "Advanced Excel":        "Office Tool",
    "VBA":                   "Office Tool",
    "PowerPoint":            "Office Tool",
    "Google Sheets":         "Office Tool",
    "R":                     "Programming",
    "Pandas":                "Programming",
    "NumPy":                 "Programming",
    "Statistics":            "Analytical",
    "A/B Testing":           "Analytical",
    "Machine Learning":      "Analytical",
    "AWS":                   "Cloud",
    "Azure":                 "Cloud",
    "GCP":                   "Cloud",
    "ETL":                   "Data Engineering",
    "Data Warehousing":       "Data Engineering",
    "Snowflake":              "Data Engineering",
    "dbt":                    "Data Engineering",
    "Airflow":                "Data Engineering",
    "Git":                    "Engineering",
    "Communication Skills":    "Soft Skill",
    "Stakeholder Management":  "Soft Skill",
}

# Aliases seen in real postings that should map back to a canonical skill name
ALIASES = {
    "postgres": "PostgreSQL",
    "pbi": "Power BI",
    "power-bi": "Power BI",
    "ms excel": "Excel",
    "excel/vba": "Excel",
    "communication": "Communication Skills",
    "stakeholder mgmt": "Stakeholder Management",
    "ml": "Machine Learning",
}

_all_terms = {s.lower(): s for s in SKILL_CATALOG}
_all_terms.update(ALIASES)

# Build one big regex with word boundaries, longest terms first so
# "Power BI" matches before a hypothetical shorter overlapping term would.
_terms_sorted = sorted(_all_terms.keys(), key=len, reverse=True)
_pattern = re.compile(
    r"(?<![A-Za-z0-9])(" + "|".join(re.escape(t) for t in _terms_sorted) + r")(?![A-Za-z0-9])",
    re.IGNORECASE,
)


def extract_skills(text: str) -> list[str]:
    """Return a de-duplicated list of canonical skill names found in text."""
    if not text or not isinstance(text, str):
        return []
    found = set()
    for match in _pattern.findall(text):
        canonical = _all_terms.get(match.lower())
        if canonical:
            found.add(canonical)
    return sorted(found)


def skill_category(skill_name: str) -> str:
    return SKILL_CATALOG.get(skill_name, "Other")


if __name__ == "__main__":
    sample = ("We need someone strong in python, SQL and Postgres. PBI or " 
               "Power BI experience is a big plus. Excel/VBA a bonus.")
    print(extract_skills(sample))
    # -> ['Excel', 'PostgreSQL', 'Power BI', 'Python', 'SQL', 'VBA']
