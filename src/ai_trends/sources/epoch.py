"""Epoch AI's curated datasets.

Epoch publishes plain CSVs with no key required. Several of the charts here come
from different files in that collection: notable models, ML hardware, datacentre
build timelines, and company funding rounds.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from ..http import get_csv, parse_float
from ..model import Line

NOTABLE_MODELS_CSV = "https://epoch.ai/data/notable_ai_models.csv"
ML_HARDWARE_CSV = "https://epoch.ai/data/ml_hardware.csv"
DATA_CENTER_TIMELINES_CSV = "https://epoch.ai/data/data_centers/data_center_timelines.csv"
FUNDING_ROUNDS_CSV = "https://epoch.ai/data/ai_companies_funding_rounds.csv"

# Epoch uses ISO long-form country names.
_REGIONS = {
    "United States of America": "United States",
    "China": "China",
}


def _iso_date(raw: str) -> str | None:
    """Epoch dates arrive as a year, a year-month, or a full date."""
    raw = (raw or "").strip()
    if len(raw) == 4:
        return f"{raw}-01-01"
    if len(raw) == 7:
        return f"{raw}-01"
    return raw if len(raw) == 10 else None


def _running_max(
    entries: list[tuple[str, float]], carry_to: str | None = None
) -> list[tuple[str, float]]:
    """Step the line up only when a new record appears."""
    points: list[tuple[str, float]] = []
    best = 0.0
    for when, value in sorted(entries):
        if value > best:
            best = value
            points.append((when, best))
    if points and carry_to and points[-1][0] != carry_to:
        points.append((carry_to, points[-1][1]))
    return points


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
        published = _iso_date(row.get("Publication date"))
        compute = parse_float(row.get("Training compute (FLOP)"))
        region = _region(row.get("Country (of organization)") or "")
        if not published or compute is None or compute <= 0 or region is None:
            continue
        by_region.setdefault(region, []).append((published, compute))

    latest = max(when for entries in by_region.values() for when, _ in entries)

    lines = []
    for region in ("United States", "China", "Rest of world"):
        entries = by_region.get(region, [])
        if not entries:
            continue
        records = _running_max(entries)

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


def frontier_training_power() -> list[Line]:
    """Peak power drawn by the hardware of the largest training runs."""
    entries = []
    for row in get_csv(NOTABLE_MODELS_CSV):
        published = _iso_date(row.get("Publication date"))
        watts = parse_float(row.get("Training power draw (W)"))
        if published and watts and watts > 0 and published >= DISPLAY_FROM:
            entries.append((published, watts))
    if not entries:
        return []
    return [Line("Largest known training run", _running_max(entries, date.today().isoformat()))]


def chip_energy_efficiency() -> list[Line]:
    """Compute per watt of the best AI accelerator available, over time.

    Restricted to tensor FP16/BF16 throughput so the comparison is like for
    like; mixing in FP32 or FP8 figures would make the curve an artefact of
    which precision each vendor chose to quote.
    """
    entries = []
    for row in get_csv(ML_HARDWARE_CSV):
        released = _iso_date(row.get("Release date"))
        tdp = parse_float(row.get("TDP (W)"))
        flops = parse_float(row.get("Tensor-FP16/BF16 performance (FLOP/s)"))
        if released and tdp and flops and tdp > 0:
            entries.append((released, flops / tdp))
    if not entries:
        return []
    return [Line("Best accelerator at release", _running_max(entries, date.today().isoformat()))]


def datacenter_power_capacity() -> list[Line]:
    """Total power capacity of the AI datacentres Epoch tracks.

    The timeline file records each site's capacity at successive observation
    dates, so the total at any moment is the sum of the most recent reading for
    every site -- an as-of join, not a sum of the rows.
    """
    observations = []
    for row in get_csv(DATA_CENTER_TIMELINES_CSV):
        when = _iso_date(row.get("Date"))
        megawatts = parse_float(row.get("Power (MW)"))
        name = (row.get("Data center") or "").strip()
        if when and name and megawatts is not None:
            observations.append((when, name, megawatts))

    # Epoch's timelines run out to 2030 because they include announced build
    # schedules. Anything past today is a projection, not a measurement.
    today = date.today().isoformat()
    observations = sorted(o for o in observations if o[0] <= today)
    if not observations:
        return []

    current: dict[str, float] = {}
    totals: dict[str, float] = {}
    for when, name, megawatts in observations:
        current[name] = megawatts
        totals[when] = sum(current.values())  # last write per date wins

    points = sorted(totals.items())
    if points[-1][0] != today:
        points.append((today, points[-1][1]))
    return [Line("Tracked AI datacentres", points)]


# Enough companies to show the shape of the race without crowding the legend.
_FUNDING_COMPANIES = 5


def cumulative_ai_funding() -> list[Line]:
    """Equity raised to date by the largest AI companies."""
    by_company: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in get_csv(FUNDING_ROUNDS_CSV):
        closed = _iso_date(row.get("Close date"))
        equity = parse_float(row.get("Funding (equity)"))
        company = (row.get("Company") or "").strip()
        if closed and company and equity and equity > 0:
            by_company[company].append((closed, equity))

    if not by_company:
        return []

    ranked = sorted(by_company, key=lambda c: -sum(v for _, v in by_company[c]))
    today = date.today().isoformat()

    lines = []
    for company in ranked[:_FUNDING_COMPANIES]:
        running = 0.0
        points = []
        for when, amount in sorted(by_company[company]):
            running += amount
            points.append((when, running))
        if points[-1][0] != today:
            points.append((today, running))
        lines.append(Line(company, points))
    return lines
