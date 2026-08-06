"""Epoch AI's curated database of notable AI models.

Epoch publishes plain CSVs with no key required. `notable_ai_models.csv` is the
one used here: it carries a publication date, a training-compute estimate, and
the country of the organisation behind each model.
"""

from __future__ import annotations

from ..http import get_csv, parse_float
from ..model import Line

NOTABLE_MODELS_CSV = "https://epoch.ai/data/notable_ai_models.csv"

# Epoch uses ISO long-form country names.
_REGIONS = {
    "United States of America": "United States",
    "China": "China",
}


def _region(raw: str) -> str | None:
    """Map a model's country field to a plotting region.

    The column holds one entry per contributing organisation, comma separated
    and often repeated ("United States of America,United States of America").
    We attribute the model to the first-listed organisation, which is Epoch's
    lead organisation for the model.
    """
    first = raw.split(",")[0].strip()
    if not first:
        return None
    return _REGIONS.get(first, "Rest of world")


# Epoch's catalogue reaches back to the 1950s. Plotting all of it compresses
# the last fifteen years into a sliver, so the chart starts here -- the running
# maximum still carries the earlier record forward as its opening value.
DISPLAY_FROM = "2010-01-01"


def frontier_training_compute() -> list[Line]:
    """Largest training run to date, by region -- a running maximum.

    A running max, rather than a scatter of every model, is what makes this a
    line: it answers "how big was the biggest known training run at time T".
    """
    rows = get_csv(NOTABLE_MODELS_CSV)

    by_region: dict[str, list[tuple[str, float]]] = {}
    for row in rows:
        published = (row.get("Publication date") or "").strip()
        compute = parse_float(row.get("Training compute (FLOP)"))
        region = _region(row.get("Country (of organization)") or "")
        if not published or compute is None or compute <= 0 or region is None:
            continue
        # A handful of rows carry a year or year-month only.
        if len(published) == 4:
            published = f"{published}-01-01"
        elif len(published) == 7:
            published = f"{published}-01"
        by_region.setdefault(region, []).append((published, compute))

    latest = max(when for entries in by_region.values() for when, _ in entries)

    lines = []
    for region in ("United States", "China", "Rest of world"):
        entries = sorted(by_region.get(region, []))
        if not entries:
            continue

        records: list[tuple[str, float]] = []
        best = 0.0
        for when, compute in entries:
            if compute > best:
                best = compute
                records.append((when, best))

        # Clip to the display window, opening at whatever the record already
        # was when the window starts.
        visible = [point for point in records if point[0] >= DISPLAY_FROM]
        earlier = [point for point in records if point[0] < DISPLAY_FROM]
        if earlier:
            visible.insert(0, (DISPLAY_FROM, earlier[-1][1]))
        if not visible:
            continue

        # Hold the frontier out to the end of the dataset so the regions' lines
        # finish together rather than stopping at each one's last record.
        if visible[-1][0] != latest:
            visible.append((latest, visible[-1][1]))
        lines.append(Line(region, visible))
    return lines
