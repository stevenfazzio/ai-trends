"""AI use by US businesses, from the Census Bureau's Business Trends and Outlook Survey.

BTOS asks a rotating panel of firms every two weeks whether they used AI in the
last fortnight and whether they expect to in the next six months. Census
reworded both questions in November 2025 -- from AI used "in producing goods or
services" to AI used "in any of its business functions" -- and publishes the
two wordings in separate workbooks. The broader wording draws markedly more
yeses, so they are kept as separate lines rather than spliced.

In October 2026 Census started calling AI "Super Intelligence or SI (formerly
referred to as Artificial Intelligence or AI)" and rewrote the question text in
the live workbook for every past fortnight too.
"""

from __future__ import annotations

import io
from datetime import date

import openpyxl

from ..http import get_bytes, parse_float
from ..model import Line

DOWNLOADS_URL = "https://www.census.gov/hfp/btos/data_downloads"
_BASE = "https://www.census.gov/hfp/btos/downloads"

# (workbook, sheet, wording label). The first is a closed archive.
_WORKBOOKS = [
    (f"{_BASE}/AI%20Core%20Questions.xlsx", "National Estimates", "producing goods or services"),
    (f"{_BASE}/National.xlsx", "Response Estimates", "any business function"),
]

# Matched on the question text: the workbooks number questions, but nothing
# promises the numbers survive a questionnaire revision. The stem picks the
# question and the name check confirms it is still about AI; the name itself
# is left out of the stem because Census has renamed AI once already.
_QUESTIONS = {
    "In the last two weeks, did this business use ": "Uses AI now",
    "During the next six months, do you think this business will be using ": (
        "Expects to within six months"
    ),
}
_AI_NAMES = ("Artificial Intelligence", "Super Intelligence")


def _collection_start(period: str) -> str:
    """A period is an ISO year plus a fortnight number, e.g. 202319.

    Fortnight n opens on the Monday of ISO week 2n-1, which reproduces the
    collection start dates Census lists in both workbooks.
    """
    return date.fromisocalendar(int(period[:4]), 2 * int(period[4:]) - 1, 1).isoformat()


def _label(question: str) -> str | None:
    if not any(name in question for name in _AI_NAMES):
        return None
    return next((v for k, v in _QUESTIONS.items() if question.startswith(k)), None)


def _yes_shares(url: str, sheet: str) -> dict[str, list[tuple[str, float | None]]]:
    """The 'Yes' row of each AI question, as dated points.

    Raises if either question is missing, matched twice or has no data, so a
    reworded workbook fails the refresh instead of quietly dropping lines.
    """
    workbook = openpyxl.load_workbook(io.BytesIO(get_bytes(url)), read_only=True, data_only=True)
    rows = workbook[sheet].iter_rows(values_only=True)
    header = [str(cell or "").strip() for cell in next(rows)]
    question_col, answer_col = header.index("Question"), header.index("Answer")
    periods = [(i, name) for i, name in enumerate(header) if len(name) == 6 and name.isdigit()]

    found: dict[str, list[tuple[str, float | None]]] = {}
    for row in rows:
        question = str(row[question_col] or "")
        label = _label(question)
        if label is None or str(row[answer_col] or "").strip() != "Yes":
            continue
        if label in found:
            raise ValueError(f"{url} [{sheet}]: more than one question reads as {label!r}")
        # Cells read "23.8%", or "." / "S" where nothing was collected or the
        # estimate was suppressed.
        points = sorted(
            (_collection_start(name), parse_float(str(row[i] or "").rstrip("%")))
            for i, name in periods
        )
        # Keep gaps inside the series -- the autumn 2025 shutdown is one -- so
        # the line breaks there, but drop the empty run-in and run-out.
        while points and points[0][1] is None:
            points.pop(0)
        while points and points[-1][1] is None:
            points.pop()
        if not points:
            raise ValueError(f"{url} [{sheet}]: {label!r} has no estimates")
        found[label] = points

    missing = [label for label in _QUESTIONS.values() if label not in found]
    if missing:
        raise ValueError(f"{url} [{sheet}]: no AI question matches {', '.join(missing)}")
    return found


def business_ai_use() -> list[Line]:
    return [
        Line(f"{label} ({wording})", points)
        for url, sheet, wording in _WORKBOOKS
        for label, points in _yes_shares(url, sheet).items()
    ]
