"""The chart registry: the one file you edit to add a chart.

Each SeriesSpec pairs a fetch function with the metadata the site needs to
render it. Order within a group is the order on the page.
"""

from __future__ import annotations

from .model import Axis, Group, SeriesSpec, Source
from .sources import arxiv, census, epoch, indeed, manual, metr, openalex, openrouter, sec

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
EPOCH_BENCHMARKS = Source(
    "Epoch AI — Capabilities & benchmarking", "https://epoch.ai/benchmarks", "CC BY 4.0"
)
SEC_EDGAR = Source(
    "SEC EDGAR XBRL company facts", "https://www.sec.gov/edgar/sec-api-documentation"
)

GROUPS = [
    Group(
        "capability",
        "Capability",
        "What the models can do, as measured by people other than their makers.",
    ),
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

SERIES = [
    SeriesSpec(
        id="task-time-horizon",
        title="Longest task a frontier model can complete",
        description=(
            "Length of software task, measured by how long it takes a skilled human, that "
            "the best model to date completes at a given success rate. A running maximum "
            "over the models METR has evaluated."
        ),
        group="capability",
        sources=[Source("METR — Task-Completion Time Horizons", metr.PAGE_URL)],
        fetch=metr.frontier_time_horizon,
        y=Axis(title="Time horizon (minutes of human work)", log=True, tickformat=",.3~r"),
        line_shape="hv",
        notes=(
            "A thousand minutes is about seventeen hours. The tasks are mostly software "
            "engineering, machine-learning and cybersecurity problems, so this says little "
            "about other kinds of work. Each estimate is fitted from a model's pass rate "
            "across tasks of different lengths and is loose: the top of METR's confidence "
            "interval is typically three or four times the bottom, and more for the "
            "latest record-holders. METR measures a selection of models, so the lines end "
            "at the last one measured rather than today."
        ),
    ),
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
        y=Axis(title="Capex per quarter (USD)", tickprefix="$", rangemode="tozero"),
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
            "Peak throughput divided by rated power, for the most efficient accelerator "
            "released to date: once counting only tensor FP16/BF16 arithmetic, and once "
            "at whichever precision each chip is fastest."
        ),
        group="environment",
        sources=[EPOCH_HARDWARE],
        fetch=epoch.chip_energy_efficiency,
        y=Axis(title="Operations per second per watt", log=True, tickformat=".0e"),
        line_shape="hv",
        notes=(
            "Vendor-quoted peak throughput over rated TDP, so both lines are spec-sheet "
            "ceilings rather than efficiency on a real workload. The FP16 line holds "
            "precision fixed to keep the comparison like for like, which leaves out "
            "whatever newer chips gain by computing at 8 or 4 bits. The any-precision "
            "line is Epoch's own efficiency figure: each chip's highest quoted throughput "
            "in any number format, counting a 4-bit operation the same as a 16-bit one. "
            "Several of its records were set by small, low-power inference chips rather "
            "than training hardware. The gap between the lines is what lower precision "
            "buys, and only a workload that tolerates it gets that gain."
        ),
    ),
    SeriesSpec(
        id="nvidia-revenue",
        title="NVIDIA quarterly revenue",
        description="Total revenue per fiscal quarter, as filed.",
        group="economics",
        sources=[SEC_EDGAR],
        fetch=sec.nvidia_revenue,
        y=Axis(title="Revenue per quarter (USD)", tickprefix="$", rangemode="tozero"),
        notes="Total company revenue; NVIDIA's datacentre segment is not broken out in XBRL.",
    ),
    SeriesSpec(
        id="ai-funding",
        title="Cumulative equity raised by the largest AI companies",
        description="Running total of disclosed equity funding, by company.",
        group="economics",
        sources=[EPOCH_COMPANIES],
        fetch=epoch.cumulative_ai_funding,
        y=Axis(title="Equity raised to date (USD)", tickprefix="$", rangemode="tozero"),
        line_shape="hv",
        notes=(
            "Equity only — debt financing, which has become a large part of how datacentre "
            "buildout is paid for, is excluded. Epoch tracks disclosed rounds at major "
            "companies rather than the whole market, and rounds are dated to close."
        ),
    ),
    SeriesSpec(
        id="ai-company-revenue",
        title="Annualised revenue of AI companies",
        description=(
            "Reported revenue run rate, by company: a recent month or quarter scaled up "
            "to a full year."
        ),
        group="economics",
        sources=[EPOCH_COMPANIES],
        fetch=epoch.annualized_revenue,
        y=Axis(title="Annualised revenue (USD)", log=True, tickprefix="$"),
        notes=(
            "Run rates, not booked revenue: a company growing fast will have earned far "
            "less over the past year than its run rate suggests. Most figures come from "
            "press reports rather than company disclosures, and companies do not define "
            "run rate or ARR the same way. Each marker is one report and the lines "
            "between them are interpolation. Companies with fewer than three reports are "
            "left out, as are figures covering a single product."
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
        id="arc-agi-cost-at-score",
        title="Cheapest model to reach a fixed ARC-AGI score",
        description=(
            "Lowest cost per task among models released to date that solve at least a "
            "given share of ARC-AGI-1. A running minimum, so each line steps down only "
            "when something cheaper clears the bar."
        ),
        group="economics",
        sources=[
            EPOCH_BENCHMARKS,
            Source("ARC Prize leaderboard", "https://arcprize.org/leaderboard"),
        ],
        fetch=epoch.arc_agi_cost_at_score,
        y=Axis(title="Cost per task (USD)", log=True, tickformat="$,.3~r"),
        line_shape="hv",
        notes=(
            "The costs are those ARC Prize reports for each model and reasoning setting "
            "it tests, republished by Epoch with release dates; entries with no reported "
            "cost are left out. A price is not a cost of production: it carries margins "
            "and pricing decisions as well as hardware and electricity, so this is what "
            "the work costs to buy. Models sit at their release date rather than the date "
            "they were tested, and the lines end at the newest model with a reported cost "
            "rather than today. ARC-AGI-1 is a set of abstract visual puzzles, so this "
            "says little about other kinds of work."
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
            "Chinese author. Papers with no country recorded for any author appear in "
            "none of the lines; they are a fifth to two-fifths of the subfield, "
            "depending on the year. Recent years keep growing as indexing catches up. "
            "OpenAlex's Artificial Intelligence subfield is broader than its name: it "
            "takes in cryptography, quantum information, and logic and type systems "
            "alongside machine learning."
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
        id="business-ai-use",
        title="Share of US businesses using AI",
        description=(
            "Percentage of firms telling the Census Bureau they used AI in the last two "
            "weeks, and the percentage expecting to within six months."
        ),
        group="adoption",
        sources=[
            Source("US Census Bureau — Business Trends and Outlook Survey", census.DOWNLOADS_URL)
        ],
        fetch=census.business_ai_use,
        y=Axis(title="Share of businesses (%)", tickformat=".1f", rangemode="tozero"),
        notes=(
            "The jump in late 2025 is a change of question, not of behaviour. Until "
            "October 2025 the survey asked about AI used in producing goods or services; "
            "from November it asks about AI used in any business function, and the "
            "broader wording draws many more yeses. Read each pair of lines on its own. "
            "The gap between them is the federal shutdown, when nothing was collected."
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
