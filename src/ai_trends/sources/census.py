"""AI use by US businesses, from the Census Bureau's Business Trends and Outlook Survey.

BTOS asks a rotating panel of firms every two weeks whether they used AI in the
last fortnight and whether they expect to in the next six months. Census
reworded both questions in November 2025 -- from AI used "in producing goods or
services" to AI used "in any of its business functions" -- and publishes the
two wordings in separate workbooks. The broader wording draws markedly more
yeses, so they are kept as separate lines rather than spliced.
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
# promises the numbers survive a questionnaire revision.
_QUESTIONS = {
    "In the last two weeks, did this business use Artificial Intelligence": "Uses AI now",
    "During the next six months, do you think this business will be using Artificial "
    "Intelligence": "Expects to within six months",
}


def _collection_start(period: str) -> str:
    """A period is an ISO year plus a fortnight number, e.g. 202319.

    Fortnight n opens on the Monday of ISO week 2n-1, which reproduces the
    collection start dates Census lists in both workbooks.
    """
    return date.fromisocalendar(int(period[:4]), 2 * int(period[4:]) - 1, 1).isoformat()


def _yes_shares(url: str, sheet: str) -> dict[str, list[tuple[str, float | None]]]:
    """The 'Yes' row of each AI question, as dated points."""
    workbook = openpyxl.load_workbook(io.BytesIO(get_bytes(url)), read_only=True, data_only=True)
    rows = workbook[sheet].iter_rows(values_only=True)
    header = [str(cell or "").strip() for cell in next(rows)]
    question_col, answer_col = header.index("Question"), header.index("Answer")
    periods = [(i, name) for i, name in enumerate(header) if len(name) == 6 and name.isdigit()]

    found: dict[str, list[tuple[str, float | None]]] = {}
    for row in rows:
        question = str(row[question_col] or "")
        label = next((v for k, v in _QUESTIONS.items() if question.startswith(k)), None)
        if label is None or str(row[answer_col] or "").strip() != "Yes":
            continue
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
        found[label] = points
    return found


def business_ai_use() -> list[Line]:
    lines = []
    for url, sheet, wording in _WORKBOOKS:
        for label, points in _yes_shares(url, sheet).items():
            if points:
                lines.append(Line(f"{label} ({wording})", points))
    return lines
