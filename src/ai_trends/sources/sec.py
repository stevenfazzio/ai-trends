"""Quarterly financials straight from SEC XBRL company facts.

No key, full history, and the numbers are the filed ones. The awkward part is
that companies report flow concepts (revenue, capex) inconsistently: some file a
discrete figure each quarter, others file a year-to-date cumulative that has to
be differenced back into quarters. `_quarterly` handles both.
"""

from __future__ import annotations

from datetime import date

from ..http import CONTACT, get_json
from ..model import Line

COMPANY_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"

# EDGAR wants a plain "name contact-email" user agent and returns 403 for the
# project's default one, which embeds a URL.
SEC_HEADERS = {"User-Agent": f"ai-trends {CONTACT}", "Accept-Encoding": "gzip, deflate"}

# Tag preference order. The first tag a company actually reports wins.
REVENUE_TAGS = (
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "SalesRevenueNet",
)
CAPEX_TAGS = (
    "PaymentsToAcquirePropertyPlantAndEquipment",
    "PaymentsToAcquireProductiveAssets",
)

HYPERSCALERS = {
    "Microsoft": 789019,
    "Alphabet": 1652044,
    "Amazon": 1018724,
    "Meta": 1326801,
}
NVIDIA_CIK = 1045810

# A "quarter" in filings runs anywhere from 84 to 98 days depending on the
# fiscal calendar; anything outside this window is a half-year or annual figure.
_QUARTER_MIN, _QUARTER_MAX = 80, 100


def _facts(cik: int) -> dict:
    return get_json(COMPANY_FACTS.format(cik=cik), headers=SEC_HEADERS)


def _quarterly(
    cik: int, tags: tuple[str, ...], since: str = "2014-01-01"
) -> list[tuple[str, float]]:
    """Discrete quarterly values, merged across every equivalent tag.

    Companies re-tag the same line item over time -- Amazon's capex moves from
    PaymentsToAcquirePropertyPlantAndEquipment to PaymentsToAcquireProductiveAssets
    in 2017 -- so taking a single tag silently truncates the series. The tags in
    each group above are synonyms for one concept, and where they overlap the
    most recently filed value wins.
    """
    facts = _facts(cik).get("facts", {}).get("us-gaap", {})
    entries = [
        entry for tag in tags for entry in facts.get(tag, {}).get("units", {}).get("USD", [])
    ]
    if not entries:
        raise RuntimeError(f"CIK {cik}: none of {tags} reported in USD")

    # The same period is refiled repeatedly (10-Q, then 10-K, then comparatives
    # in later years). Keep the most recently filed value for each period.
    periods: dict[tuple[str, str], tuple[str, float]] = {}
    for entry in entries:
        start, end, filed = entry.get("start"), entry.get("end"), entry.get("filed", "")
        if not start or not end:
            continue
        key = (start, end)
        if key not in periods or filed > periods[key][0]:
            periods[key] = (filed, float(entry["val"]))

    def span(start: str, end: str) -> int:
        return (date.fromisoformat(end) - date.fromisoformat(start)).days

    # Values already filed as a single quarter.
    quarters: dict[str, float] = {
        end: val
        for (start, end), (_, val) in periods.items()
        if _QUARTER_MIN <= span(start, end) <= _QUARTER_MAX
    }

    # Year-to-date cumulatives: everything sharing a start date forms a chain
    # (Q1, H1, 9M, FY), so consecutive differences recover the later quarters.
    chains: dict[str, list[tuple[str, float]]] = {}
    for (start, end), (_, val) in periods.items():
        chains.setdefault(start, []).append((end, val))
    for chain in chains.values():
        chain.sort()
        for (prev_end, prev_val), (end, val) in zip(chain, chain[1:], strict=False):
            if end in quarters:
                continue
            if _QUARTER_MIN <= span(prev_end, end) <= _QUARTER_MAX:
                quarters[end] = val - prev_val

    return sorted((end, val) for end, val in quarters.items() if end >= since)


def hyperscaler_capex() -> list[Line]:
    return [Line(name, _quarterly(cik, CAPEX_TAGS)) for name, cik in HYPERSCALERS.items()]


def nvidia_revenue() -> list[Line]:
    return [Line("NVIDIA total revenue", _quarterly(NVIDIA_CIK, REVENUE_TAGS, since="2010-01-01"))]
