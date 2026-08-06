"""arXiv submission volume, by category, by month.

The arXiv API returns a total-results count for any query, so we ask one query
per (category, month) and read the count. That is a lot of requests to do on
every build, so counts land in a committed JSON cache and only the trailing
months are refetched -- arXiv keeps accepting cross-lists into a month for a
while after it ends, so those numbers stay soft for a few weeks.
"""

from __future__ import annotations

import calendar
import json
import re
import time
from datetime import date
from pathlib import Path

from ..http import get_text
from ..model import Line

API = "https://export.arxiv.org/api/query"
CACHE_FILE = Path(__file__).resolve().parents[3] / "cache" / "arxiv_monthly_counts.json"

CATEGORIES = {
    "cs.AI": "cs.AI (Artificial Intelligence)",
    "cs.LG": "cs.LG (Machine Learning)",
    "cs.CL": "cs.CL (Computation and Language)",
    "cs.CV": "cs.CV (Computer Vision)",
}

START = date(2015, 1, 1)

# arXiv asks for no more than one request every three seconds.
REQUEST_DELAY_SECONDS = 3.0

# Trailing months are always refetched, since late cross-lists keep landing.
VOLATILE_MONTHS = 2

_TOTAL_RE = re.compile(r"<opensearch:totalResults[^>]*>(\d+)</opensearch:totalResults>")


def _months(start: date, end: date) -> list[tuple[int, int]]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _query_count(category: str, year: int, month: int) -> int:
    last = calendar.monthrange(year, month)[1]
    window = f"[{year}{month:02d}010000 TO {year}{month:02d}{last:02d}2359]"
    xml = get_text(
        API,
        # max_results=0 returns HTTP 500; 1 is the cheapest query that works.
        {"search_query": f"cat:{category} AND submittedDate:{window}", "max_results": 1},
        use_cache=False,
    )
    match = _TOTAL_RE.search(xml)
    if not match:
        raise RuntimeError(f"no totalResults in arXiv response for {category} {year}-{month:02d}")
    return int(match.group(1))


def _load_cache() -> dict[str, int]:
    if CACHE_FILE.exists():
        return json.loads(CACHE_FILE.read_text())
    return {}


def _save_cache(cache: dict[str, int]) -> None:
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=0, sort_keys=True) + "\n")


def refresh_cache(today: date | None = None) -> dict[str, int]:
    """Fill in any months missing from the cache, plus the volatile tail."""
    today = today or date.today()
    # The current month is always partial, so the last full month is the end.
    end = date(today.year, today.month, 1)
    end = date(end.year - 1, 12, 1) if end.month == 1 else date(end.year, end.month - 1, 1)

    months = _months(START, end)
    volatile = set(months[-VOLATILE_MONTHS:])
    cache = _load_cache()

    pending = [
        (cat, y, m)
        for cat in CATEGORIES
        for (y, m) in months
        if f"{cat}:{y}-{m:02d}" not in cache or (y, m) in volatile
    ]

    for i, (cat, y, m) in enumerate(pending):
        cache[f"{cat}:{y}-{m:02d}"] = _query_count(cat, y, m)
        if i % 20 == 0 or i == len(pending) - 1:
            _save_cache(cache)
            print(f"  arxiv: {i + 1}/{len(pending)} months fetched", flush=True)
        if i < len(pending) - 1:
            time.sleep(REQUEST_DELAY_SECONDS)

    _save_cache(cache)
    return cache


def monthly_submissions() -> list[Line]:
    cache = refresh_cache()
    lines = []
    for cat, label in CATEGORIES.items():
        prefix = f"{cat}:"
        points = sorted(
            (f"{key[len(prefix) :]}-01", float(count))
            for key, count in cache.items()
            if key.startswith(prefix)
        )
        if points:
            lines.append(Line(label, list(points)))
    return lines
