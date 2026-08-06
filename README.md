# AI Trends

Time-series charts on AI compute, economics, research and adoption, rebuilt
daily from public sources and published to GitHub Pages.

**→ https://stevenfazzio.com/ai-trends/**

Nothing here is an original estimate. Every chart plots someone else's published
numbers and links back to them.

## How it works

A GitHub Actions job runs each morning, fetches every series in the registry,
commits the result to `data/`, and deploys the static site.

```
src/ai_trends/
  registry.py     the list of charts -- the only file you edit to add one
  model.py        SeriesSpec / Line / Axis
  build.py        fetch -> data/*.json -> _site/
  http.py         shared session, retries, local response cache
  sources/        one module per upstream provider
data/             committed output, one JSON per series
cache/            committed intermediate counts (arXiv), so CI stays cheap
site/             index.html, app.js, style.css -- rendered with Plotly
events.toml       model-release markers drawn across the charts
```

### Two kinds of series

Sources differ in whether they hand you history, and the pipeline treats them
differently:

- **`recompute`** — the upstream holds the full history (Epoch, SEC, OpenAlex,
  arXiv, Indeed). Every run rebuilds the series from scratch, so upstream
  revisions flow through.
- **`append`** — the upstream only exposes a current value (OpenRouter pricing).
  Each run records one observation. These series have no history before
  collection started and can never be backfilled, which is why the job runs
  daily rather than on demand.

## Running it locally

```sh
uv sync
uv run python -m ai_trends.build          # everything
uv run python -m ai_trends.build --only nvidia-revenue
uv run python -m ai_trends.build --fail-fast   # stop on the first fetch error

python3 -m http.server 8000 --directory _site
```

A failing upstream does not blank a chart: the previously committed JSON stays
in place and the page shows a "last refresh failed" badge.

The first build populates `cache/arxiv_monthly_counts.json` by asking arXiv for
one count per category per month, at their requested one-request-per-three-
seconds. That takes roughly half an hour once; afterwards only the trailing two
months are refetched.

## Adding a chart

1. Write a function in `src/ai_trends/sources/` returning `list[Line]`.
2. Add a `SeriesSpec` to `SERIES` in `registry.py`.
3. `uv run python -m ai_trends.build --only your-new-id --fail-fast`

The page is driven entirely by `data/manifest.json`; no front-end changes are
needed.

## Sources

| Series | Source | Licence |
|---|---|---|
| Largest known training run | [Epoch AI](https://epoch.ai/data/ai-models) | CC BY 4.0 |
| Hyperscaler capex, NVIDIA revenue | [SEC EDGAR XBRL](https://www.sec.gov/edgar/sec-api-documentation) | public domain |
| Token price index | [OpenRouter](https://openrouter.ai/docs/api-reference/list-available-models) | — |
| AI papers by country | [OpenAlex](https://openalex.org) | CC0 |
| arXiv submissions | [arXiv API](https://info.arxiv.org/help/api/index.html) | — |
| AI share of job postings | [Indeed Hiring Lab](https://github.com/hiring-lab/ai-tracker) | Hiring Lab terms |

## Not here yet

**Capability benchmarks.** The obvious missing group. LMArena's HuggingFace
mirror carries dated leaderboard CSVs from May 2023 but stopped updating in
August 2025, so Elo history is available but stale, and the live source needs
work. SWE-bench Verified is reconstructable from per-submission metadata in
[SWE-bench/experiments](https://github.com/SWE-bench/experiments). ARC-AGI has
no JSON endpoint — the leaderboard is embedded in the page payload.

**Geographic splits** exist only where the upstream carries a country field:
Epoch (organisation country), OpenAlex (author institutions), Indeed (per
country, no China). Benchmarks, prices and arXiv have no usable country
dimension, so those charts are single-region by necessity rather than choice.
