"""AI research output by country, via OpenAlex.

OpenAlex tags every work with a topic hierarchy and with the countries of its
authors' institutions, and it will group counts by year server-side -- so the
whole series is three cheap requests.
"""

from __future__ import annotations

from datetime import date

from ..http import get_json
from ..model import Line

API = "https://api.openalex.org/works"
AI_SUBFIELD = "subfields/1702"  # Artificial Intelligence
CONTACT = "fazzios@gmail.com"

FIRST_YEAR = 2010

# "Rest of world" is defined by exclusion rather than subtraction: a paper with
# both US and Chinese authors counts once for each of those, so US + China +
# (world - US - China) would not reconcile.
_QUERIES = {
    "United States": "authorships.countries:US",
    "China": "authorships.countries:CN",
    "Rest of world": "authorships.countries:!US,authorships.countries:!CN",
}


def ai_publications_by_country() -> list[Line]:
    # The current year is always partial; end at the last complete one.
    last_year = date.today().year - 1

    lines = []
    for label, country_filter in _QUERIES.items():
        payload = get_json(
            API,
            {
                "filter": (
                    f"primary_topic.subfield.id:{AI_SUBFIELD},"
                    f"{country_filter},"
                    f"publication_year:{FIRST_YEAR}-{last_year}"
                ),
                "group_by": "publication_year",
                "per_page": 200,
                "mailto": CONTACT,
            },
        )
        points = sorted(
            (f"{group['key']}-01-01", float(group["count"]))
            for group in payload.get("group_by", [])
            if group.get("key", "").isdigit()
        )
        lines.append(Line(label, list(points)))
    return lines
