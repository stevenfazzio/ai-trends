"""Core data model shared by every source adapter and the build pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

# A point is (ISO date, value). Values may be None to represent a genuine gap in
# the series -- Plotly renders those as a break in the line rather than
# interpolating across them.
Point = tuple[str, float | None]


@dataclass
class Line:
    """One plotted line. A series with a geographic or categorical dimension
    contributes several of these; a plain series contributes exactly one."""

    name: str
    points: list[Point]

    def sorted(self) -> Line:
        return Line(self.name, sorted(self.points, key=lambda p: p[0]))

    def to_dict(self) -> dict:
        return {"name": self.name, "points": [list(p) for p in self.points]}


@dataclass
class Axis:
    title: str = ""
    log: bool = False
    # Plotly d3-format string, e.g. ".2s" for SI prefixes, "$,.0f", ".1%"
    tickformat: str | None = None
    # "tozero" pins a linear axis at 0 so growth isn't visually exaggerated.
    rangemode: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v not in (None, "", False)}


@dataclass
class Source:
    name: str
    url: str
    license: str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class SeriesSpec:
    """Everything needed to fetch, store and render one chart.

    Adding a chart to the site means adding one of these to the registry.
    """

    id: str
    title: str
    description: str
    group: str
    source: Source
    fetch: Callable[[], list[Line]]
    y: Axis = field(default_factory=Axis)

    # "recompute": the upstream source holds full history, so every run rebuilds
    #   the series from scratch and picks up any upstream revisions.
    # "append":    the upstream source only exposes a current value, so each run
    #   appends today's observation to whatever we have already recorded. These
    #   series start empty and fill in over time.
    mode: str = "recompute"

    # Whether to draw the shared model-release markers from events.toml.
    annotations: bool = True

    # Plotly line shape. "hv" draws a staircase, which is the honest rendering
    # for a running maximum: the value holds until something beats it.
    line_shape: str = "linear"

    # Caveats worth showing the reader directly under the chart.
    notes: str = ""

    def meta(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "group": self.group,
            "source": self.source.to_dict(),
            "y": self.y.to_dict(),
            "mode": self.mode,
            "annotations": self.annotations,
            "line_shape": self.line_shape,
            "notes": self.notes,
        }


@dataclass
class Group:
    id: str
    title: str
    blurb: str = ""
