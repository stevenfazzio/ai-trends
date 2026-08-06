"""The chart registry: the one file you edit to add a chart.

Each SeriesSpec pairs a fetch function with the metadata the site needs to
render it. Order within a group is the order on the page.
"""

from __future__ import annotations

from .model import Axis, Group, SeriesSpec, Source
from .sources import arxiv, epoch, indeed, openalex, openrouter, sec

GROUPS = [
    Group(
        "compute",
        "Compute",
        "How much computation is going into training, and who is buying the hardware.",
    ),
    Group(
        "economics",
        "Economics",
        "What AI costs to build and what it costs to use.",
    ),
    Group(
        "research",
        "Research",
        "Volume and geography of published AI work.",
    ),
    Group(
        "adoption",
        "Adoption",
        "Where AI is showing up outside the labs.",
    ),
]

# A "capability" group belongs here too -- benchmark scores and Arena Elo -- but
# LMArena stopped publishing to its HuggingFace mirror in August 2025 and the
# live source needs more work. See README.

SERIES = [
    SeriesSpec(
        id="frontier-training-compute",
        title="Largest known training run, by country",
        description=(
            "Training compute of the largest model published to date, in floating-point "
            "operations. A running maximum, so the line steps up only when a bigger "
            "training run appears."
        ),
        group="compute",
        source=Source(
            "Epoch AI — Notable AI Models",
            "https://epoch.ai/data/ai-models",
            "CC BY 4.0",
        ),
        fetch=epoch.frontier_training_compute,
        y=Axis(title="Training compute (FLOP)", log=True, tickformat=".0e"),
        line_shape="hv",
        notes=(
            "Models are attributed to the country of the first-listed organisation. "
            "Compute figures are Epoch's estimates and are frequently revised; only a "
            "few hundred of the 8,000+ catalogued models have a compute estimate at all."
        ),
    ),
    SeriesSpec(
        id="hyperscaler-capex",
        title="Quarterly capital expenditure at the big four cloud buyers",
        description=(
            "Cash spent on property, plant and equipment each quarter by Microsoft, "
            "Alphabet, Amazon and Meta — the closest public proxy for AI datacentre "
            "buildout."
        ),
        group="compute",
        source=Source(
            "SEC EDGAR XBRL company facts", "https://www.sec.gov/edgar/sec-api-documentation"
        ),
        fetch=sec.hyperscaler_capex,
        y=Axis(title="Capex per quarter (USD)", tickformat="$.2s", rangemode="tozero"),
        notes=(
            "Capex covers all property and equipment, not only AI hardware. Companies "
            "that file year-to-date cumulatives have their quarters recovered by "
            "differencing, and fiscal quarters do not align across companies."
        ),
    ),
    SeriesSpec(
        id="nvidia-revenue",
        title="NVIDIA quarterly revenue",
        description="Total revenue per fiscal quarter, as filed.",
        group="economics",
        source=Source(
            "SEC EDGAR XBRL company facts", "https://www.sec.gov/edgar/sec-api-documentation"
        ),
        fetch=sec.nvidia_revenue,
        y=Axis(title="Revenue per quarter (USD)", tickformat="$.2s", rangemode="tozero"),
        notes="Total company revenue; NVIDIA's datacentre segment is not broken out in XBRL.",
    ),
    SeriesSpec(
        id="token-price-index",
        title="Price of a million input tokens",
        description=(
            "Percentiles of prompt pricing across every text model listed on OpenRouter, "
            "tracking the market rather than any single model."
        ),
        group="economics",
        source=Source(
            "OpenRouter model catalogue",
            "https://openrouter.ai/docs/api-reference/list-available-models",
        ),
        fetch=openrouter.token_price_index,
        y=Axis(title="USD per million input tokens", log=True, tickformat="$.2f"),
        mode="append",
        notes=(
            "OpenRouter publishes current prices only, so this series starts the day "
            "collection began and gains one observation per day. It has no history "
            "before then."
        ),
    ),
    SeriesSpec(
        id="ai-publications-by-country",
        title="AI papers published per year, by country",
        description=(
            "Works whose primary topic falls in the Artificial Intelligence subfield, "
            "counted by the countries of their authors' institutions."
        ),
        group="research",
        source=Source("OpenAlex", "https://openalex.org", "CC0"),
        fetch=openalex.ai_publications_by_country,
        y=Axis(title="Papers per year", tickformat=".2s", rangemode="tozero"),
        notes=(
            "A paper with authors in several countries counts once for each, so the "
            "lines are not a partition. 'Rest of world' excludes any paper with a US or "
            "Chinese author. Recent years keep growing as indexing catches up."
        ),
    ),
    SeriesSpec(
        id="arxiv-submissions",
        title="arXiv submissions per month, by category",
        description="New submissions to the main AI-adjacent arXiv categories each month.",
        group="research",
        source=Source("arXiv API", "https://info.arxiv.org/help/api/index.html"),
        fetch=arxiv.monthly_submissions,
        y=Axis(title="Submissions per month", tickformat=".2s", rangemode="tozero"),
        notes=(
            "Counted by submission date and primary-or-cross-listed category, so a paper "
            "in both cs.LG and cs.CL appears in both lines. The most recent months keep "
            "rising for a few weeks as cross-lists land."
        ),
    ),
    SeriesSpec(
        id="ai-job-postings",
        title="Share of job postings mentioning AI",
        description=(
            "Percentage of postings on Indeed containing AI or generative-AI terms, "
            "averaged by month."
        ),
        group="adoption",
        source=Source("Indeed Hiring Lab — AI tracker", indeed.REPO_URL, "Indeed Hiring Lab terms"),
        fetch=indeed.ai_share_of_job_postings,
        y=Axis(title="Share of postings (%)", tickformat=".2f", rangemode="tozero"),
        notes=(
            "Indeed's country coverage does not include China. The measure is keyword "
            "based, so it tracks how often employers mention AI, not how many jobs "
            "actually involve it."
        ),
    ),
]
