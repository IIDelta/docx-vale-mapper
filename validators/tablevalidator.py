from __future__ import annotations

import re
from dataclasses import dataclass

from validators.abbreviationvalidator import (
    ParagraphRecord,
    make_finding,
)


@dataclass(frozen=True)
class TableCellRecord:
    """One extracted Word table cell."""

    table_index: int
    row_index: int
    column_index: int
    text: str
    paragraph: ParagraphRecord
    range_start: int = 0
    range_end: int = 0


def is_title_case_like(
    text: str,
) -> bool:
    """
    Return True when multiword text resembles title case.

    This is intentionally conservative. It ignores:
      - single-word headings;
      - all-uppercase abbreviations;
      - headings with fewer than two ordinary words.
    """

    words = re.findall(
        r"[A-Za-z]+",
        text,
    )

    ordinary_words = [
        word
        for word in words
        if not word.isupper()
    ]

    if len(ordinary_words) < 2:
        return False

    capitalized_count = sum(
        word[0].isupper()
        for word in ordinary_words
        if word
    )

    return capitalized_count == len(ordinary_words)


def make_cell_finding(
    check: str,
    severity: str,
    message: str,
    match: str,
    cell: TableCellRecord,
) -> dict:
    """
    Create a structural finding with the exact Word table-cell range.

    Paragraph data remains available for CSV/export compatibility,
    while RangeStart and RangeEnd allow Word comments to attach to
    the actual table cell rather than a nearby paragraph.
    """

    finding = make_finding(
        check=check,
        severity=severity,
        message=message,
        match=match,
        paragraph=cell.paragraph,
    )

    if cell.range_end > cell.range_start:
        finding["RangeStart"] = cell.range_start
        finding["RangeEnd"] = cell.range_end

    return finding


def validate_table_cells(
    cells: list[TableCellRecord],
) -> list[dict]:
    """
    Validate table heading case and basic zero presentation.

    Heading checks:
      - first table row;
      - first table column.

    Zero checks:
      - body cells only;
      - exact 0.0 and 0.0% values.
    """

    findings: list[dict] = []

    processed_heading_cells: set[
        tuple[int, int, int]
    ] = set()

    for cell in cells:
        if cell.paragraph.content_zone in {
            "title_page",
            "summary_of_changes",
            "protocol_summary",
        }:
            continue

        is_column_heading = cell.row_index == 1

        is_row_heading = (
            cell.column_index == 1
            and cell.row_index > 1
        )

        if is_column_heading or is_row_heading:
            cell_key = (
                cell.table_index,
                cell.row_index,
                cell.column_index,
            )

            if cell_key in processed_heading_cells:
                continue

            processed_heading_cells.add(cell_key)

            if is_title_case_like(cell.text):
                findings.append(
                    make_cell_finding(
                        check="Clinical.TableHeadingSentenceCase",
                        severity="warning",
                        message=(
                            "Style guide table format: Use "
                            "sentence-case capitalization for table "
                            "column and row headings."
                        ),
                        match=cell.text,
                        cell=cell,
                    )
                )


        is_body_cell = (
            cell.row_index > 1
            and cell.column_index > 1
        )

        if not is_body_cell:
            continue

        normalized_text = cell.text.strip()

        if normalized_text == "0.0":
            findings.append(
                make_cell_finding(
                    check="Clinical.TableZeroFormat",
                    severity="warning",
                    message=(
                        "Style guide table format: Use 0 instead "
                        "of 0.0 for a null table value."
                    ),
                    match=cell.text,
                    cell=cell,
                )
            )


        if normalized_text == "0.0%":
            findings.append(
                make_cell_finding(
                    check="Clinical.TableZeroFormat",
                    severity="warning",
                    message=(
                        "Style guide table format: Use 0 instead "
                        "of 0.0% for a null table value."
                    ),
                    match=cell.text,
                    cell=cell,
                )
            )


    return findings
