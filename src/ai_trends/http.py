"""Shared HTTP helpers.

Every upstream here is a free public API. We identify ourselves honestly, retry
transient failures, and keep a small on-disk cache so a rebuild during
development doesn't hammer anyone.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CONTACT = "fazzios@gmail.com"
USER_AGENT = f"ai-trends/0.1 (+https://github.com/stevenfazzio/ai-trends; {CONTACT})"

CACHE_DIR = Path(os.environ.get("AI_TRENDS_CACHE", Path(__file__).resolve().parents[2] / ".cache"))
# Responses older than this are refetched. CI runs with a cold cache anyway; this
# mainly protects local iteration.
CACHE_TTL_SECONDS = 6 * 60 * 60

_session: requests.Session | None = None


def session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers["User-Agent"] = USER_AGENT
        retry = Retry(
            total=4,
            backoff_factor=1.5,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            respect_retry_after_header=True,
        )
        s.mount("https://", HTTPAdapter(max_retries=retry))
        s.mount("http://", HTTPAdapter(max_retries=retry))
        _session = s
    return _session


def _cache_path(url: str, params: Any) -> Path:
    key = hashlib.sha256(f"{url}|{json.dumps(params, sort_keys=True)}".encode()).hexdigest()[:20]
    return CACHE_DIR / f"{key}.cache"


def get_text(
    url: str,
    params: dict | None = None,
    *,
    use_cache: bool = True,
    headers: dict | None = None,
) -> str:
    """GET a URL as text, with a short-lived on-disk cache."""
    path = _cache_path(url, params)
    if use_cache and path.exists() and time.time() - path.stat().st_mtime < CACHE_TTL_SECONDS:
        return path.read_text()

    resp = session().get(url, params=params, timeout=60, headers=headers)
    resp.raise_for_status()
    text = resp.text

    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return text


def get_json(
    url: str,
    params: dict | None = None,
    *,
    use_cache: bool = True,
    headers: dict | None = None,
) -> Any:
    return json.loads(get_text(url, params, use_cache=use_cache, headers=headers))


def get_csv(
    url: str, params: dict | None = None, *, use_cache: bool = True
) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(get_text(url, params, use_cache=use_cache))))


def parse_float(value: str | None) -> float | None:
    """CSV numeric fields from upstream are frequently blank or non-numeric."""
    if value is None:
        return None
    value = value.strip().replace(",", "")
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None
