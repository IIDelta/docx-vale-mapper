from __future__ import annotations

import unittest

from validators.abbreviationvalidator import ParagraphRecord
from validators.typographyvalidator import validate_unit_nonbreaking_spaces


class UnitSpacingTests(unittest.TestCase):
    def paragraph(
        self,
        zone: str = "body_narrative",
    ) -> ParagraphRecord:
        return ParagraphRecord(
            index=1,
            line=1,
            text="fixture",
            content_zone=zone,
        )

    def test_ordinary_space_between_number_and_unit_is_flagged(self) -> None:
        findings = validate_unit_nonbreaking_spaces(
            self.paragraph(),
            "Participants received 5 mg for 3 days.",
        )

        self.assertEqual(len(findings), 2)
        self.assertEqual(
            {finding["Check"] for finding in findings},
            {"Clinical.UnitNonbreakingSpace"},
        )

    def test_nonbreaking_space_between_number_and_unit_passes(self) -> None:
        findings = validate_unit_nonbreaking_spaces(
            self.paragraph(),
            "Participants received 5\u00a0mg for 3\u00a0days.",
        )

        self.assertEqual(findings, [])

    def test_table_cells_are_exempt(self) -> None:
        findings = validate_unit_nonbreaking_spaces(
            self.paragraph("table_cell"),
            "5 mg",
        )

        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
