"""The chart registry: the one file you edit to add a chart.

Each SeriesSpec pairs a fetch function with the metadata the site needs to
render it. Order within a group is the order on the page.
"""

from __future__ import annotations

from .model import Axis, Group, SeriesSpec, Source
from .sources import arxiv, epoch, indeed, manual, openalex, openrouter, sec

EPOCH_MODELS = Source(
    "Epoch AI — Notable AI Models", "https://epoch.ai/data/ai-models", "CC BY 4.0"
)
EPOCH_HARDWARE = Source(
    "Epoch AI — Machine Learning Hardware",
    "https://epoch.ai/data/machine-learning-hardware",
    "CC BY 4.0",
)
EPOCH_DATACENTERS = Source(
    "Epoch AI — AI Data Centers", "https://epoch.ai/data/ai-data-centers", "CC BY 4.0"
)
EPOCH_COMPANIES = Source(
    "Epoch AI — AI Companies", "https://epoch.ai/data/ai-companies", "CC BY 4.0"
)
SEC_EDGAR = Source(
    "SEC EDGAR XBRL company facts", "https://www.sec.gov/edgar/sec-api-documentation"
)

GROUPS = [
    Group(
        "compute",
        "Compute",
        "How much computation is going into training, and who is buying the hardware.",
    ),
    Group(
        "environment",
        "Environment",
        "The physical footprint: power drawn, capacity built, and efficiency gained.",
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
    Group(
        "opinion",
        "Opinion",
        "What the public makes of it.",
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
        sources=[EPOCH_MODELS],
        fetch=epoch.frontier_training_compute,
        y=Axis(title="Training compute (FLOP)", log=True, tickformat=".0e"),
        line_shape="hv",
        notes=(
            "Models are attributed to the country of the first-listed organisation. "
            "Compute figures are Epoch's estimates and are frequently revised; only about "
            "half of the catalogued models carry a compute estimate at all."
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
        sources=[SEC_EDGAR],
        fetch=sec.hyperscaler_capex,
        y=Axis(title="Capex per quarter (USD)", tickformat="$.2s", rangemode="tozero"),
        notes=(
            "Capex covers all property and equipment, not only AI hardware. Companies "
            "that file year-to-date cumulatives have their quarters recovered by "
            "differencing, and fiscal quarters do not align across companies."
        ),
    ),
    SeriesSpec(
        id="datacenter-power",
        title="Power capacity of tracked AI datacentres",
        description=(
            "Combined nameplate power of the AI datacentres Epoch tracks, taking each "
            "site's most recent recorded capacity."
        ),
        group="environment",
        sources=[EPOCH_DATACENTERS],
        fetch=epoch.datacenter_power_capacity,
        y=Axis(title="Power capacity (MW)", tickformat=".2s", rangemode="tozero"),
        notes=(
            "Capacity the sites can draw, not the electricity they actually consume. "
            "Epoch tracks roughly eighty sites and the coverage is overwhelmingly American, "
            "so this is a floor on the global total rather than a measurement of it. Their "
            "timelines extend to 2030 because they include announced build schedules; "
            "everything after today is excluded here. As Epoch adds sites, earlier totals "
            "rise too."
        ),
    ),
    SeriesSpec(
        id="training-power-draw",
        title="Power drawn by the largest training runs",
        description=(
            "Estimated power pulled by the hardware running the largest training run "
            "published to date."
        ),
        group="environment",
        sources=[EPOCH_MODELS],
        fetch=epoch.frontier_training_power,
        y=Axis(title="Training power draw (W)", log=True, tickformat=".0e"),
        line_shape="hv",
        notes=(
            "A running maximum over the models Epoch has power estimates for, which is "
            "roughly a fifth of the catalogue. This is instantaneous draw during training, "
            "not total energy consumed, and says nothing about inference — which is now the "
            "larger share of the industry's electricity use."
        ),
    ),
    SeriesSpec(
        id="chip-energy-efficiency",
        title="Compute per watt of the best AI accelerator",
        description=(
            "Peak tensor FP16/BF16 throughput divided by rated power, for the most "
            "efficient accelerator released to date."
        ),
        group="environment",
        sources=[EPOCH_HARDWARE],
        fetch=epoch.chip_energy_efficiency,
        y=Axis(title="FLOP/s per watt", log=True, tickformat=".0e"),
        line_shape="hv",
        notes=(
            "Vendor-quoted peak throughput over rated TDP, so it is a spec-sheet ceiling "
            "rather than efficiency on a real workload. Restricted to tensor FP16/BF16 "
            "figures to keep the comparison like for like — quoting FP8 or FP4 numbers "
            "instead would make the curve an artefact of precision choices."
        ),
    ),
    SeriesSpec(
        id="nvidia-revenue",
        title="NVIDIA quarterly revenue",
        description="Total revenue per fiscal quarter, as filed.",
        group="economics",
        sources=[SEC_EDGAR],
        fetch=sec.nvidia_revenue,
        y=Axis(title="Revenue per quarter (USD)", tickformat="$.2s", rangemode="tozero"),
        notes="Total company revenue; NVIDIA's datacentre segment is not broken out in XBRL.",
    ),
    SeriesSpec(
        id="ai-funding",
        title="Cumulative equity raised by the largest AI companies",
        description="Running total of disclosed equity funding, by company.",
        group="economics",
        sources=[EPOCH_COMPANIES],
        fetch=epoch.cumulative_ai_funding,
        y=Axis(title="Equity raised to date (USD)", tickformat="$.2s", rangemode="tozero"),
        line_shape="hv",
        notes=(
            "Equity only — debt financing, which has become a large part of how datacentre "
            "buildout is paid for, is excluded. Epoch tracks disclosed rounds at major "
            "companies rather than the whole market, and rounds are dated to close."
        ),
    ),
    SeriesSpec(
        id="token-price-index",
        title="Price of a million input tokens",
        description=(
            "Percentiles of prompt pricing across every text model listed on OpenRouter, "
            "tracking the market rather than any single model."
        ),
        group="economics",
        sources=[
            Source(
                "OpenRouter model catalogue",
                "https://openrouter.ai/docs/api-reference/list-available-models",
            )
        ],
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
        sources=[Source("OpenAlex", "https://openalex.org", "CC0")],
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
        sources=[Source("arXiv API", "https://info.arxiv.org/help/api/index.html")],
        fetch=arxiv.monthly_submissions,
        y=Axis(title="Submissions per month", tickformat=".2s", rangemode="tozero"),
        notes=(
            "Counted by submission date and primary-or-cross-listed category, so a paper "
            "in both cs.LG and cs.CL appears in both lines. The newest month is dropped "
            "because cross-lists keep landing for weeks after a month closes."
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
        sources=[
            Source("Indeed Hiring Lab — AI tracker", indeed.REPO_URL, "Indeed Hiring Lab terms")
        ],
        fetch=indeed.ai_share_of_job_postings,
        y=Axis(title="Share of postings (%)", tickformat=".2f", rangemode="tozero"),
        notes=(
            "Indeed's country coverage does not include China. The measure is keyword "
            "based, so it tracks how often employers mention AI, not how many jobs "
            "actually involve it."
        ),
    ),
    SeriesSpec(
        id="us-ai-opinion",
        title="American public opinion on AI",
        description=(
            "Long-running poll questions on how the US public feels about AI, from the "
            "two organisations that have asked the same thing repeatedly."
        ),
        group="opinion",
        sources=[
            Source(
                "Pew Research Center",
                "https://www.pewresearch.org/topic/internet-technology/emerging-technology/artificial-intelligence/",
            ),
            Source("Gallup", "https://www.gallup.com/topic/artificial-intelligence.aspx"),
        ],
        fetch=manual.us_ai_opinion,
        y=Axis(title="% of US adults", tickformat=".0f", rangemode="tozero"),
        notes=(
            "Hand-entered from published releases — no pollster offers a machine-readable "
            "feed — with every figure's citation recorded alongside it in "
            "manual/us-ai-opinion.csv. The lines come from different surveys with different "
            "question wording and sampling, so read the movement within a line and not the "
            "gaps between them. Each question is asked about once a year."
        ),
    ),
]
