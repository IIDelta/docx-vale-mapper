from __future__ import annotations

import unittest

from validators.abbreviationvalidator import (
    ParagraphRecord,
)
from validators.tablevalidator import (
    TableCellRecord,
    validate_table_cells,
)


def paragraph(
    index: int,
    text: str,
) -> ParagraphRecord:
    """Create a compact paragraph fixture."""

    return ParagraphRecord(
        index=index,
        line=index,
        text=text,
    )


def cell(
    table_index: int,
    row_index: int,
    column_index: int,
    text: str,
) -> TableCellRecord:
    """Create a compact table-cell fixture."""

    return TableCellRecord(
        table_index=table_index,
        row_index=row_index,
        column_index=column_index,
        text=text,
        paragraph=paragraph(
            index=(row_index * 10) + column_index,
            text=text,
        ),
    )


class TableValidatorTests(unittest.TestCase):
    """Tests for A9.1 table validation."""

    def test_sentence_case_headings_pass(self) -> None:
        cells = [
            cell(1, 1, 1, "Population"),
            cell(1, 1, 2, "Treatment group"),
            cell(1, 2, 1, "Safety population"),
            cell(1, 2, 2, "12"),
        ]

        findings = validate_table_cells(cells)

        self.assertEqual(findings, [])

    def test_title_case_headings_are_flagged(self) -> None:
        cells = [
            cell(1, 1, 1, "Population"),
            cell(1, 1, 2, "Treatment Group"),
            cell(1, 2, 1, "Safety Population"),
            cell(1, 2, 2, "12"),
        ]

        findings = validate_table_cells(cells)

        checks = [
            finding["Check"]
            for finding in findings
        ]

        self.assertEqual(
            checks.count(
                "Clinical.TableHeadingSentenceCase"
            ),
            2,
        )

    def test_body_zero_formats_are_flagged(self) -> None:
        cells = [
            cell(1, 1, 1, "Population"),
            cell(1, 1, 2, "Total"),
            cell(1, 2, 1, "Safety population"),
            cell(1, 2, 2, "0.0"),
            cell(1, 3, 1, "Response population"),
            cell(1, 3, 2, "0.0%"),
        ]

        findings = validate_table_cells(cells)

        checks = [
            finding["Check"]
            for finding in findings
        ]

        self.assertEqual(
            checks.count(
                "Clinical.TableZeroFormat"
            ),
            2,
        )
