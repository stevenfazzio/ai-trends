"""New GitHub repositories written in proof assistants' languages, by month.

GitHub's repository search reports a total count for any query, so we ask one
per language per month -- public repositories created that month whose main
language, as GitHub detects it, is the one asked for -- and one more for every
public repository created that month, to divide by. Search leaves forks out of
both unless asked.

That is several hundred requests for the full history, so counts land in a
committed JSON cache, as arXiv's do, and only the trailing months are refetched:
a repository is given a language only once code is pushed to it, so a month's
counts keep climbing for a while after it ends.
"""

from __future__ import annotations

import calendar
import json
import os
import time
from datetime import date
from pathlib import Path

from ..http import session
from ..model import Line

API = "https://api.github.com/search/repositories"
DOCS_URL = "https://docs.github.com/en/rest/search/search#search-repositories"
CACHE_FILE = Path(__file__).resolve().parents[3] / "cache" / "github_monthly_repo_counts.json"

# GitHub's language names, and how the chart labels them. GitHub still calls
# Rocq by its old name and accepts either in a query.
LANGUAGES = {
    "Lean": "Lean",
    "Coq": "Rocq (formerly Coq)",
    "Isabelle": "Isabelle",
    "Agda": "Agda",
}
# Cache key for the count of every public repository, the denominator.
_ALL = "all"

START = date(2016, 1, 1)

# Search allows 30 requests a minute with a token and 10 without.
_DELAY_WITH_TOKEN = 2.5
_DELAY_WITHOUT = 6.5

# Trailing months are always refetched, since languages are detected late.
VOLATILE_MONTHS = 3


def _months(start: date, end: date) -> list[tuple[int, int]]:
    out, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        out.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _headers() -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _query_count(language: str, year: int, month: int) -> int:
    last = calendar.monthrange(year, month)[1]
    created = f"created:{year}-{month:02d}-01..{year}-{month:02d}-{last:02d}"
    query = f"is:public {created}" if language == _ALL else f"language:{language} {created}"

    for _ in range(6):
        resp = session().get(
            API, params={"q": query, "per_page": 1}, headers=_headers(), timeout=60
        )
        # GitHub signals both of its rate limits with a 403 or 429. The
        # secondary one may give no reset time, in which case it asks for a
        # minute's wait.
        if resp.status_code in (403, 429):
            retry_after = resp.headers.get("Retry-After")
            reset = resp.headers.get("X-RateLimit-Reset")
            if retry_after:
                wait = float(retry_after)
            elif resp.headers.get("X-RateLimit-Remaining") == "0" and reset:
                wait = max(float(reset) - time.time(), 0) + 1
            else:
                wait = 60.0
            time.sleep(min(wait, 300))
            continue
        resp.raise_for_status()
        body = resp.json()
        # A search that runs out of time returns whatever it counted so far.
        if body.get("incomplete_results"):
            time.sleep(10)
            continue
        return int(body["total_count"])
    raise RuntimeError(f"GitHub search gave no complete count for {query!r}")


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
        (language, y, m)
        for language in [_ALL, *LANGUAGES]
        for (y, m) in months
        if f"{language}:{y}-{m:02d}" not in cache or (y, m) in volatile
    ]

    delay = _DELAY_WITH_TOKEN if os.environ.get("GITHUB_TOKEN") else _DELAY_WITHOUT
    for i, (language, y, m) in enumerate(pending):
        cache[f"{language}:{y}-{m:02d}"] = _query_count(language, y, m)
        if i % 20 == 0 or i == len(pending) - 1:
            _save_cache(cache)
            print(f"  github: {i + 1}/{len(pending)} counts fetched", flush=True)
        if i < len(pending) - 1:
            time.sleep(delay)

    _save_cache(cache)
    return cache


# Each point pools this many months. The smaller languages see a handful of
# new repositories a month, and a class that gives every student a repository
# can multiply a month's count tenfold.
WINDOW_MONTHS = 3


def proof_assistant_repo_share() -> list[Line]:
    """New repositories in each proof assistant's language, per million new ones.

    Dividing by every new repository takes out GitHub's own growth, which is
    fast enough to make any language's raw count climb. Each point is the share
    over the months up to and including its own.
    """
    cache = refresh_cache()
    months = sorted(key.split(":", 1)[1] for key in cache if key.startswith(f"{_ALL}:"))
    lines = []
    for language, label in LANGUAGES.items():
        points = []
        for end in range(WINDOW_MONTHS - 1, len(months)):
            window = months[end - WINDOW_MONTHS + 1 : end + 1]
            counts = [cache.get(f"{language}:{month}") for month in window]
            total = sum(cache[f"{_ALL}:{month}"] for month in window)
            if None not in counts and total:
                points.append((f"{months[end]}-01", round(sum(counts) / total * 1e6, 2)))
        if points:
            lines.append(Line(label, points))
    return lines
