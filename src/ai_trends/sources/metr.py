"""METR's task-completion time horizons.

For each frontier model METR estimates the length of task -- measured by how
long it takes a skilled human -- that the model completes at a given success
rate. The per-model results are published as YAML alongside the write-up.
"""

from __future__ import annotations

import yaml

from ..http import get_text
from ..model import Line, running_max

PAGE_URL = "https://metr.org/time-horizons/"
# The file name carries the methodology version, and PAGE_URL links whichever
# is current. A new version gets a new name, after which this one keeps
# answering with numbers that have stopped moving.
RESULTS_YAML = "https://metr.org/assets/benchmark_results_1_1.yaml"

_METRICS = {
    "50% success rate": "p50_horizon_length",
    "80% success rate": "p80_horizon_length",
}


def frontier_time_horizon() -> list[Line]:
    """Longest time horizon measured for any model to date -- a running maximum."""
    results = yaml.safe_load(get_text(RESULTS_YAML))["results"]

    entries: dict[str, list[tuple[str, float]]] = {label: [] for label in _METRICS}
    for result in results.values():
        # YAML parses a bare 2024-06-20 into a date.
        released = str(result.get("release_date") or "")
        for label, metric in _METRICS.items():
            minutes = (result.get("metrics", {}).get(metric) or {}).get("estimate")
            if len(released) == 10 and minutes and minutes > 0:
                entries[label].append((released, float(minutes)))

    dated = [when for points in entries.values() for when, _ in points]
    if not dated:
        return []
    # Hold both records out to the newest model measured, not to today: a flat
    # stretch past that would claim measurements nobody has made.
    latest = max(dated)
    return [Line(label, running_max(points, latest)) for label, points in entries.items()]
