"""PutnamBench: problems from the Putnam competition, stated as Lean theorems.

The leaderboard is a JSON file in the benchmark's repository with one entry per
system, each giving how many problems it proved. The benchmark gains a
competition's worth of problems each year, so the size a count is measured
against is read from the README rather than fixed here.
"""

from __future__ import annotations

import re

from ..http import get_json, get_text
from ..model import Line, record_line

REPO_URL = "https://github.com/trishullab/PutnamBench"
LEADERBOARD_URL = "https://trishullab.github.io/PutnamBench/leaderboard.html"
_RAW = "https://raw.githubusercontent.com/trishullab/PutnamBench/main"
RESULTS_JSON = f"{_RAW}/docs/results.json"
README = f"{_RAW}/README.md"

# The standard Lean task, in which any numerical answer a problem asks for is
# written into the theorem. The leaderboard's other Lean variant makes the
# system find the answer too, and few entries attempt it.
_TASK = "lean-wsolution"


def _lean_problem_count() -> int:
    """The README's table of formalisations per language."""
    match = re.search(r"\|\s*Lean 4\s*\|\s*(\d+)\s*\|", get_text(README))
    if not match:
        raise ValueError("PutnamBench README no longer gives a Lean problem count")
    return int(match.group(1))


def best_share_solved() -> list[Line]:
    """Most problems any system has proved to date, as a share of today's set."""
    total = _lean_problem_count()
    entries = []
    for name, result in get_json(RESULTS_JSON).items():
        solved = (result.get("num-solved") or {}).get(_TASK)
        added = str(result.get("date-added") or "")
        if solved is not None and len(added) == 10:
            # Repeat submissions are told apart by trailing spaces in the key.
            entries.append((added, round(solved / total, 4), name.strip()))
    if not entries:
        return []
    # Hold the record out to the newest entry, not to today.
    latest = max(when for when, _, _ in entries)
    return [record_line("PutnamBench", entries, latest)]
