"""Epoch AI's polling on AI usage, fielded with Ipsos.

Epoch publishes one page per wave at https://epoch.ai/data/polling/<wave>. Each
links an aggregate CSV named polling_on_ai_usage_<mon>_<year>.csv and states
who fielded it and when. The landing page is the latest wave and carries a
dropdown listing every wave, so waves are discovered from there rather than by
guessing month slugs. The CSV itself carries no date; each point sits at the
middle of the fieldwork the page reports, or mid-month if the page stops saying.

Only waves that asked the attitude question, and that Ipsos fielded, contribute
a point. The first was October 2026, when Epoch began a monthly tracker meant to
repeat the same core questions. Earlier waves asked about usage, not attitude,
and one of them was fielded by a different pollster, so they are skipped.
"""

from __future__ import annotations

import calendar
import html
import re
from datetime import date

from ..http import get_csv, get_text, parse_float
from ..model import Line

INDEX_URL = "https://epoch.ai/data/polling"
_BASE_URL = "https://epoch.ai"

# Epoch's wording is Pew's, word for word. The CSV is keyed on the question id;
# the verbatim is checked too, so a reworded question cannot quietly extend a
# line that only means something while the wording holds.
ATTITUDE_QUESTION = "q1_attitude"
ATTITUDE_VERBATIM = (
    "Overall, would you say the increased use of artificial intelligence (AI) in "
    "daily life makes you feel..."
)
MORE_CONCERNED = "More concerned than excited"

# A wave page's path, as the landing page's dropdown lists it: a slug with no
# file extension, such as /data/polling/2026-10.
_WAVE_PATH = re.compile(r"/data/polling/([A-Za-z0-9-]+)(?![\w.-])")
# The aggregate CSV, as distinct from the microdata and codebook files beside it.
_AGGREGATE_CSV = re.compile(r"/data/polling/polling_on_ai_usage_([a-z]{3})_(\d{4})\.csv")
_MONTH_BY_SLUG = {name.lower(): number for number, name in enumerate(calendar.month_abbr) if name}
_MONTH_BY_NAME = {name: number for number, name in enumerate(calendar.month_name) if name}

# "October 9–11, 2026", "November 25 – December 3, 2025", "October 9, 2026", or
# a range that crosses a year, "December 30, 2026 – January 2, 2027".
_FIELDWORK = re.compile(
    r"([A-Z][a-z]+)\s+(\d{1,2})(?:,\s*(\d{4}))?"
    r"(?:\s*[-–—]\s*(?:([A-Z][a-z]+)\s+)?(\d{1,2}))?"
    r",\s*(\d{4})"
)


def _metadata(page: str, label: str) -> str | None:
    """The entry called `label` in a wave page's description list, as plain text."""
    match = re.search(rf"<dt[^>]*>\s*{label}\s*</dt>\s*<dd[^>]*>(.*?)</dd>", page, re.S)
    if not match:
        return None
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", match.group(1))).split())


def fieldwork_midpoint(text: str | None) -> date | None:
    """The middle day of a fieldwork range written as Epoch writes it.

    Anything else, including a garbled range, gives None rather than whatever
    fragment happens to look like a date.
    """
    match = _FIELDWORK.fullmatch(" ".join((text or "").split()))
    if not match:
        return None
    start_month, start_day, start_year, end_month, end_day, end_year = match.groups()
    try:
        end_month = _MONTH_BY_NAME[end_month or start_month]
        end = date(int(end_year), end_month, int(end_day or start_day))
        start = date(int(start_year or end_year), _MONTH_BY_NAME[start_month], int(start_day))
    except (KeyError, ValueError):
        return None
    if start > end:
        return None
    return start + (end - start) // 2


def _wave_pages() -> list[str]:
    """Every wave's page, newest first, as the landing page lists them."""
    found: list[str] = []
    for match in _WAVE_PATH.finditer(get_text(INDEX_URL)):
        url = _BASE_URL + match.group(0)
        if url not in found:
            found.append(url)
    return found


def _normalised(wording: str) -> str:
    return " ".join(wording.replace("…", "...").split()).lower()


def _full_sample_share(rows: list[dict[str, str]], response: str) -> float | None:
    """The weighted share of all respondents giving `response` to the attitude question."""
    for row in rows:
        if row.get("question") != ATTITUDE_QUESTION or row.get("demographic") != "full_sample":
            continue
        wording = row.get("question_verbatim") or ""
        if _normalised(wording) != _normalised(ATTITUDE_VERBATIM):
            raise ValueError(f"Epoch reworded {ATTITUDE_QUESTION}: {wording!r}")
        if row.get("response") == response:
            share = parse_float(row.get("pct"))
            return round(share, 1) if share is not None else None
    return None


def more_concerned_than_excited() -> list[Line]:
    """Share of US adults more concerned than excited about AI, one point per wave."""
    points: list[tuple[str, float]] = []
    for page_url in _wave_pages():
        page = get_text(page_url)
        csv_link = _AGGREGATE_CSV.search(page)
        if not csv_link:
            continue
        pollster = _metadata(page, "Pollster")
        if pollster and "Ipsos" not in pollster:
            continue
        rows = get_csv(_BASE_URL + csv_link.group(0))
        share = _full_sample_share(rows, MORE_CONCERNED)
        if share is None:
            continue
        month_slug, year = csv_link.groups()
        when = fieldwork_midpoint(_metadata(page, "Fielded")) or date(
            int(year), _MONTH_BY_SLUG[month_slug], 15
        )
        points.append((when.isoformat(), share))

    if not points:
        # The tracker exists, so finding nothing means the page or CSV layout has
        # changed. Failing here keeps the last good data on the chart, with a badge.
        raise ValueError(f"no wave at {INDEX_URL} carried {ATTITUDE_QUESTION}")
    return [Line("More concerned than excited about AI (Epoch/Ipsos, monthly)", sorted(points))]
