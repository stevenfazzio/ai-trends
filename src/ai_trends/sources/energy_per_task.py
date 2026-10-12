"""Energy per task for open-weight models, from llm-energy-per-task.

The one source here that is not somebody else's work: the measurements were
made for this site. They live in their own repository, which publishes the
method, every raw answer and the lines themselves, and this module treats it as
it would any other upstream. It plots the lines as published and does not
recompute them, so the rule for what counts as a step is the repository's.
"""

from __future__ import annotations

from collections import defaultdict

from ..http import get_csv, parse_float
from ..model import Line

REPO_URL = "https://github.com/stevenfazzio/llm-energy-per-task"
_RESULTS = "https://raw.githubusercontent.com/stevenfazzio/llm-energy-per-task/main/results"
# One row per step of every line, for every score bar from 0.05 to 0.95.
FRONTIER_CSV = f"{_RESULTS}/frontier.csv"
# One row per model and task. Read only for the date of the newest model.
SUMMARY_CSV = f"{_RESULTS}/summary.csv"

_TASKS = {
    "extraction": "Answer from a passage",
    "intent": "Route a customer message",
    "toolcall": "Write a function call",
}


def least_energy_at_fixed_score() -> list[Line]:
    """One line per task: least energy among models at or above a score bar.

    The repository publishes every bar from 5% to 95% and marks two per task
    for charting. This takes the one it calls "2023", the highest bar that some
    model released in 2023 clears, because that line runs the length of the
    dataset. A step whose score is within sampling error of the bar is drawn
    hollow. Near misses, which the file also records, are left out.
    """
    steps: dict[tuple[str, float], list[dict]] = defaultdict(list)
    for row in get_csv(FRONTIER_CSV):
        bar = parse_float(row.get("bar"))
        joules = parse_float(row.get("joules_per_item"))
        charted = "2023" in (row.get("chart") or "").split("+")
        if row.get("task") not in _TASKS or not charted or bar is None or not joules:
            continue
        if row.get("kind") != "near_miss":
            steps[row["task"], bar].append(row)
    if not steps:
        return []

    # Hold each line out to the newest model measured, not to today: a flat
    # stretch past that would claim measurements nobody has made.
    latest = max(row["released"] for row in get_csv(SUMMARY_CSV) if row.get("released"))

    lines = []
    for task, bar in sorted(steps, key=lambda key: list(_TASKS).index(key[0])):
        rows = sorted(steps[task, bar], key=lambda row: row["released"])
        points = [(row["released"], round(float(row["joules_per_item"]), 3)) for row in rows]
        # The model without its publisher, and what it scored.
        labels = [f"{row['model'].split('/')[-1]}, {float(row['score']):.1%}" for row in rows]
        hollow = [row["kind"] == "step_straddling" for row in rows]
        if points[-1][0] != latest:
            points.append((latest, points[-1][1]))
            labels.append("")
            hollow.append(False)
        name = f"{_TASKS[task]} (at least {bar:.0%} right)"
        lines.append(Line(name, points, labels=labels, hollow=hollow))
    return lines
