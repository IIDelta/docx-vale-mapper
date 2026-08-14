from __future__ import annotations

import unittest

from validators.abbreviationvalidator import ParagraphRecord
from validators.tablevalidator import TableCellRecord, validate_table_cells


def cell(row: int, column: int, text: str) -> TableCellRecord:
    paragraph = ParagraphRecord(index=(row * 10) + column, line=row, text=text)
    return TableCellRecord(
        table_index=1,
        row_index=row,
        column_index=column,
        text=text,
        paragraph=paragraph,
    )


class MissingDataDefinitionTests(unittest.TestCase):
    def test_undefined_missing_data_code_is_flagged(self) -> None:
        findings = validate_table_cells(
            [
                cell(1, 1, "Population"),
                cell(1, 2, "Total"),
                cell(2, 1, "Safety population"),
                cell(2, 2, "NA"),
            ]
        )
        checks = {finding["Check"] for finding in findings}
        self.assertIn("Clinical.TableMissingDataDefinition", checks)

    def test_defined_missing_data_code_passes(self) -> None:
        findings = validate_table_cells(
            [
                cell(1, 1, "Population"),
                cell(1, 2, "Total"),
                cell(2, 1, "Safety population"),
                cell(2, 2, "ND"),
                cell(3, 1, "ND: not determined."),
            ]
        )
        checks = {finding["Check"] for finding in findings}
        self.assertNotIn("Clinical.TableMissingDataDefinition", checks)


if __name__ == "__main__":
    unittest.main()
