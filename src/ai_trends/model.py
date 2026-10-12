"""Core data model shared by every source adapter and the build pipeline."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field, replace

# A point is (ISO date, value). Values may be None to represent a genuine gap in
# the series -- Plotly renders those as a break in the line rather than
# interpolating across them.
Point = tuple[str, float | None]


@dataclass
class Line:
    """One plotted line. A series with a geographic or categorical dimension
    contributes several of these; a plain series contributes exactly one.

    The optional fields say more about individual points, for a line whose
    points are things with names rather than readings on a calendar. Left
    unset, nothing about them reaches the JSON.
    """

    name: str
    points: list[Point]
    # One per point: what the hover shows beside the value, such as the model
    # that set a record. An empty label marks a point that is the line being
    # carried forward, not an observation; it is drawn without a marker.
    labels: list[str] | None = None
    # One per point: True draws the marker hollow, for a point less certain
    # than its neighbours.
    hollow: list[bool] | None = None

    def sorted(self) -> Line:
        order = sorted(range(len(self.points)), key=lambda i: self.points[i][0])

        def reorder(values: list | None) -> list | None:
            return [values[i] for i in order] if values else values

        return replace(
            self,
            points=reorder(self.points),
            labels=reorder(self.labels),
            hollow=reorder(self.hollow),
        )

    def to_dict(self) -> dict:
        out: dict = {"name": self.name, "points": [list(p) for p in self.points]}
        if self.labels:
            out["labels"] = self.labels
        if self.hollow:
            out["hollow"] = self.hollow
        return out


def running_max(
    entries: list[tuple[str, float]], carry_to: str | None = None
) -> list[tuple[str, float]]:
    """Step the line up only when a new record appears."""
    points: list[tuple[str, float]] = []
    best = 0.0
    for when, value in sorted(entries):
        if value > best:
            best = value
            points.append((when, best))
    if points and carry_to and points[-1][0] != carry_to:
        points.append((carry_to, points[-1][1]))
    return points


def running_min(
    entries: list[tuple[str, float]], carry_to: str | None = None
) -> list[tuple[str, float]]:
    """Step the line down only when a new record low appears."""
    points: list[tuple[str, float]] = []
    best = float("inf")
    for when, value in sorted(entries):
        if value < best:
            best = value
            points.append((when, best))
    if points and carry_to and points[-1][0] != carry_to:
        points.append((carry_to, points[-1][1]))
    return points


@dataclass
class Axis:
    title: str = ""
    log: bool = False
    # Plotly d3-format string, e.g. ".2s" for SI prefixes, "$,.0f", ".1%"
    tickformat: str | None = None
    # Text put in front of every tick and hover value. For large dollar amounts
    # use tickprefix="$" and no tickformat: d3's SI format writes a billion as
    # "G", whereas Plotly's own abbreviation, used when tickformat is unset,
    # writes "B".
    tickprefix: str | None = None
    # Text put after every tick and hover value: a unit, with its leading space.
    ticksuffix: str | None = None
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
    # Usually one, but a hand-assembled series can cite several pollsters or
    # publications, each of which deserves its own link.
    sources: list[Source]
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
            "sources": [source.to_dict() for source in self.sources],
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
