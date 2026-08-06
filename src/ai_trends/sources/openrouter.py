"""A price index for LLM inference, from OpenRouter's model catalogue.

OpenRouter only exposes *current* pricing, so this series is append-mode: it has
no history before the day we started recording, and grows one point per build.

Rather than track named models -- which churn, get deprecated, and would need
constant curation -- this tracks percentiles across the whole catalogue. That is
robust to model turnover and still shows the thing worth seeing: what a token
costs across the market, and how far apart the cheap and expensive ends are.
"""

from __future__ import annotations

from datetime import date

from ..http import get_json
from ..model import Line

API = "https://openrouter.ai/api/v1/models"

PERCENTILES = {
    "Cheapest decile": 10,
    "Median model": 50,
    "Most expensive decile": 90,
}


def _percentile(values: list[float], pct: int) -> float:
    """Nearest-rank percentile; `values` must be sorted."""
    index = max(0, min(len(values) - 1, round(pct / 100 * len(values) + 0.5) - 1))
    return values[index]


def token_price_index() -> list[Line]:
    models = get_json(API, use_cache=False).get("data", [])

    prices = []
    for model in models:
        pricing = model.get("pricing") or {}
        architecture = model.get("architecture") or {}
        if "text" not in (architecture.get("output_modalities") or ["text"]):
            continue
        try:
            per_token = float(pricing.get("prompt"))
        except (TypeError, ValueError):
            continue
        # Free and hidden-price entries would drag the low percentiles to zero.
        if per_token <= 0:
            continue
        prices.append(per_token * 1_000_000)

    if not prices:
        raise RuntimeError("OpenRouter returned no priced text models")
    prices.sort()

    today = date.today().isoformat()
    return [
        Line(label, [(today, round(_percentile(prices, pct), 4))])
        for label, pct in PERCENTILES.items()
    ]
