"""Share of job postings mentioning AI, from Indeed's Hiring Lab.

Hiring Lab publishes the tracker as a CSV in a public GitHub repo, daily, per
country, back to 2019. Daily is noisier and larger than this chart needs, so we
average to months.
"""

from __future__ import annotations

from collections import defaultdict

from ..http import get_csv, parse_float
from ..model import Line

CSV_URL = "https://raw.githubusercontent.com/hiring-lab/ai-tracker/main/AI_posting.csv"
REPO_URL = "https://github.com/hiring-lab/ai-tracker"

# Hiring Lab covers AU, CA, DE, FR, GB, IE, IT, NL, US. Six keeps the chart
# readable; the rest track the same shape.
COUNTRIES = {
    "US": "United States",
    "GB": "United Kingdom",
    "CA": "Canada",
    "DE": "Germany",
    "FR": "France",
    "AU": "Australia",
}


def ai_share_of_job_postings() -> list[Line]:
    rows = get_csv(CSV_URL)

    monthly: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        code = (row.get("jobcountry") or "").strip()
        day = (row.get("date") or "").strip()
        share = parse_float(row.get("AI_share_postings"))
        if code not in COUNTRIES or len(day) < 7 or share is None:
            continue
        monthly[code][f"{day[:7]}-01"].append(share)

    lines = []
    for code, label in COUNTRIES.items():
        months = monthly.get(code, {})
        points = sorted(
            (month, round(sum(values) / len(values), 4)) for month, values in months.items()
        )
        if points:
            # The final month is usually partial; keeping it makes the last
            # point jump around between daily rebuilds.
            lines.append(Line(label, list(points[:-1])))
    return lines
