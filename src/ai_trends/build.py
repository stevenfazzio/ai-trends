"""Fetch every series in the registry, write JSON, assemble the static site.

Run with no arguments for a full build:

    uv run python -m ai_trends.build

A failing upstream never blanks a chart: the previously committed JSON for that
series is left in place and the manifest records the failure so the page can say
so. Only `--fail-fast` turns a fetch error into a non-zero exit.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tomllib
import traceback
from datetime import UTC, datetime
from pathlib import Path

from .model import Line, SeriesSpec
from .registry import GROUPS, SERIES

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
SITE_DIR = ROOT / "site"
OUT_DIR = ROOT / "_site"
EVENTS_FILE = ROOT / "events.toml"


def _read_existing(spec: SeriesSpec) -> dict | None:
    path = DATA_DIR / f"{spec.id}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def _merge_append(existing: dict | None, fresh: list[Line]) -> list[Line]:
    """Fold today's observation into the recorded history.

    Points are keyed by date, so re-running on the same day overwrites rather
    than duplicating.
    """
    recorded: dict[str, dict[str, float | None]] = {}
    order: list[str] = []
    for line in (existing or {}).get("lines", []):
        recorded[line["name"]] = {point[0]: point[1] for point in line["points"]}
        order.append(line["name"])

    for line in fresh:
        recorded.setdefault(line.name, {})
        if line.name not in order:
            order.append(line.name)
        recorded[line.name].update(dict(line.points))

    return [Line(name, sorted(recorded[name].items())) for name in order]


def build_series(spec: SeriesSpec, *, fail_fast: bool) -> dict:
    """Fetch one series and write its JSON. Returns the manifest entry."""
    meta = spec.meta()
    existing = _read_existing(spec)

    try:
        fetched = spec.fetch()
    except Exception as exc:  # noqa: BLE001 - one bad upstream must not stop the build
        if fail_fast:
            raise
        traceback.print_exc()
        print(f"  !! {spec.id}: {type(exc).__name__}: {exc}", file=sys.stderr)
        meta.update(
            {
                "ok": False,
                "error": f"{type(exc).__name__}: {exc}",
                "updated": (existing or {}).get("updated"),
                "stale": existing is not None,
            }
        )
        return meta

    lines = _merge_append(existing, fetched) if spec.mode == "append" else fetched
    lines = [line.sorted() for line in lines if line.points]

    updated = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {**meta, "updated": updated, "lines": [line.to_dict() for line in lines]}

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / f"{spec.id}.json").write_text(json.dumps(payload, indent=1) + "\n")

    total = sum(len(line.points) for line in lines)
    print(f"  ok {spec.id}: {len(lines)} line(s), {total} points")
    return {**meta, "ok": True, "updated": updated, "lines": len(lines), "points": total}


def load_events() -> list[dict]:
    if not EVENTS_FILE.exists():
        return []
    events = tomllib.loads(EVENTS_FILE.read_text()).get("event", [])
    return sorted(events, key=lambda e: e["date"])


def write_manifest(entries: dict[str, dict]) -> None:
    groups = []
    for group in GROUPS:
        members = [entries[spec.id] for spec in SERIES if spec.group == group.id]
        if members:
            groups.append(
                {"id": group.id, "title": group.title, "blurb": group.blurb, "series": members}
            )

    manifest = {
        "generated": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "groups": groups,
        "events": load_events(),
    }
    (DATA_DIR / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")


def assemble_site() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    shutil.copytree(SITE_DIR, OUT_DIR)
    shutil.copytree(DATA_DIR, OUT_DIR / "data")
    print(f"  assembled {OUT_DIR.relative_to(ROOT)}/")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", action="append", metavar="SERIES_ID", help="build just these")
    parser.add_argument("--fail-fast", action="store_true", help="stop on the first fetch error")
    parser.add_argument("--no-assemble", action="store_true", help="skip writing _site/")
    args = parser.parse_args(argv)

    selected = [s for s in SERIES if not args.only or s.id in args.only]
    if args.only and len(selected) != len(args.only):
        unknown = set(args.only) - {s.id for s in selected}
        parser.error(f"unknown series: {', '.join(sorted(unknown))}")

    print(f"building {len(selected)} series")
    entries = {spec.id: build_series(spec, fail_fast=args.fail_fast) for spec in selected}

    # A partial build still needs the untouched series in the manifest.
    for spec in SERIES:
        if spec.id not in entries:
            existing = _read_existing(spec) or {}
            entries[spec.id] = {
                **spec.meta(),
                "ok": bool(existing),
                "updated": existing.get("updated"),
                "lines": len(existing.get("lines", [])),
            }

    write_manifest(entries)
    if not args.no_assemble:
        assemble_site()

    failed = [sid for sid, entry in entries.items() if not entry.get("ok")]
    if failed:
        print(f"\n{len(failed)} series failed: {', '.join(failed)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
