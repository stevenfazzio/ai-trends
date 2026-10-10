"""Epoch AI's curated datasets.

Epoch publishes plain CSVs with no key required. Several of the charts here come
from different files in that collection: notable models, ML hardware, datacentre
build timelines, company funding rounds and revenue reports, and the benchmark
results they gather from other people's leaderboards.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from ..http import get_csv, get_zipped_csv, parse_float
from ..model import Line, running_max, running_min

NOTABLE_MODELS_CSV = "https://epoch.ai/data/notable_ai_models.csv"
ML_HARDWARE_CSV = "https://epoch.ai/data/ml_hardware.csv"
DATA_CENTER_TIMELINES_CSV = "https://epoch.ai/data/data_centers/data_center_timelines.csv"
FUNDING_ROUNDS_CSV = "https://epoch.ai/data/ai_companies_funding_rounds.csv"
REVENUE_REPORTS_CSV = "https://epoch.ai/data/ai_companies_revenue_reports.csv"
# One archive holding a CSV per benchmark.
BENCHMARK_DATA_ZIP = "https://epoch.ai/data/benchmark_data.zip"

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
        records = running_max(entries)

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
    return [Line("Largest known training run", running_max(entries, date.today().isoformat()))]


def chip_energy_efficiency() -> list[Line]:
    """Compute per watt of the best AI accelerator available, over time.

    Two lines. The first is restricted to tensor FP16/BF16 throughput so the
    comparison is like for like; mixing in FP32 or FP8 figures would make the
    curve an artefact of which precision each vendor chose to quote. The second
    is Epoch's own efficiency column, which does mix them -- each chip's highest
    quoted throughput at any precision, over TDP -- and so picks up the gains
    from lower-precision arithmetic that the first leaves out.
    """
    fp16 = []
    any_precision = []
    for row in get_csv(ML_HARDWARE_CSV):
        released = _iso_date(row.get("Release date"))
        if not released:
            continue
        tdp = parse_float(row.get("TDP (W)"))
        flops = parse_float(row.get("Tensor-FP16/BF16 performance (FLOP/s)"))
        if tdp and flops and tdp > 0:
            fp16.append((released, flops / tdp))
        efficiency = parse_float(row.get("Energy efficiency"))
        if efficiency and efficiency > 0:
            any_precision.append((released, efficiency))

    today = date.today().isoformat()
    like_for_like = running_max(fp16, today)
    overall = running_max(any_precision, today)

    # Epoch's column reaches back to 2008 and jumps fortyfold in 2015, when the
    # record passes from FP32 graphics cards to an INT8 inference chip. Open it
    # where the FP16 line opens, at the record then standing, so the gap between
    # the two shows the precision shift and nothing else.
    if like_for_like:
        start = like_for_like[0][0]
        standing = [point for point in overall if point[0] <= start]
        overall = [point for point in overall if point[0] > start]
        if standing:
            overall.insert(0, (start, standing[-1][1]))

    return [Line("FP16 only", like_for_like), Line("Any precision", overall)]


# Shares of ARC-AGI-1 solved. The lower bars were cleared first and so show the
# longest decline.
_ARC_SCORE_BARS = (0.25, 0.50, 0.75, 0.90)


def arc_agi_cost_at_score() -> list[Line]:
    """Cheapest model to date that clears a fixed ARC-AGI-1 score -- a running minimum.

    Fixing the score is what makes cost comparable over time. The cheapest entry
    on a leaderboard is always a weak model, so the question has to be what it
    costs to do at least this well.
    """
    entries = []
    for row in get_zipped_csv(BENCHMARK_DATA_ZIP, "arc_agi_external.csv"):
        released = _iso_date(row.get("Release date"))
        score = parse_float(row.get("Score"))
        cost = parse_float(row.get("Cost per task"))
        if released and score is not None and cost and cost > 0:
            entries.append((released, score, cost))
    if not entries:
        return []

    # Hold the records out to the newest model with a reported cost, not to
    # today: a flat stretch past that would claim measurements nobody has made.
    latest = max(when for when, _, _ in entries)
    lines = []
    for bar in _ARC_SCORE_BARS:
        cleared = [(when, cost) for when, score, cost in entries if score >= bar]
        lines.append(Line(f"At least {bar:.0%} solved", running_min(cleared, latest)))
    return lines


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


# A company needs a few reports before joining them up says anything.
_MIN_REVENUE_REPORTS = 3


def annualized_revenue() -> list[Line]:
    """Reported annualised revenue of AI companies, one line per company.

    Each row is one report of a run rate at a date. Product-level figures and
    rows that only give a period total are left out, so every point on a line
    is a whole-company annualised number.
    """
    by_company: dict[str, dict[str, float]] = defaultdict(dict)
    rows = get_csv(REVENUE_REPORTS_CSV)
    # Two reports can share a date; the later-published one wins.
    for row in sorted(rows, key=lambda r: r.get("Report date") or ""):
        when = _iso_date(row.get("Date"))
        revenue = parse_float(row.get("Annualized revenue (USD)"))
        company = (row.get("Company") or "").strip()
        if (row.get("Scope") or "").strip() != "Full company":
            continue
        if when and company and revenue and revenue > 0:
            by_company[company][when] = revenue

    lines = [
        Line(company, sorted(points.items()))
        for company, points in by_company.items()
        if len(points) >= _MIN_REVENUE_REPORTS
    ]
    return sorted(lines, key=lambda line: -line.points[-1][1])
