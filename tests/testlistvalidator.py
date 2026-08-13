from __future__ import annotations

import unittest

from validators.abbreviationvalidator import (
    ParagraphRecord,
)
from validators.listvalidator import (
    validate_list_structure,
)


def record(
    index: int,
    text: str,
    list_marker: str = "",
) -> ParagraphRecord:
    """Create a compact paragraph fixture."""

    return ParagraphRecord(
        index=index,
        line=index,
        text=text,
        list_marker=list_marker,
    )


class ListValidatorTests(unittest.TestCase):
    """Tests for Word list-structure validation."""

    def test_valid_list_passes(self) -> None:
        paragraphs = [
            record(
                1,
                "The following components were included:",
            ),
            record(
                2,
                "First component.",
                "•",
            ),
            record(
                3,
                "Second component.",
                "•",
            ),
        ]

        findings = validate_list_structure(
            paragraphs
        )

        self.assertEqual(findings, [])

    def test_single_item_list_is_flagged(self) -> None:
        paragraphs = [
            record(
                1,
                "The following component was included:",
            ),
            record(
                2,
                "First component.",
                "•",
            ),
        ]

        findings = validate_list_structure(
            paragraphs
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.SingleItemList",
            checks,
        )

    def test_missing_introductory_colon_is_flagged(self) -> None:
        paragraphs = [
            record(
                1,
                "The following components were included.",
            ),
            record(
                2,
                "First component.",
                "•",
            ),
            record(
                3,
                "Second component.",
                "•",
            ),
        ]

        findings = validate_list_structure(
            paragraphs
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.ListIntroductionColon",
            checks,
        )

    def test_lowercase_and_missing_period_are_flagged(
        self,
    ) -> None:
        paragraphs = [
            record(
                1,
                "The following components were included:",
            ),
            record(
                2,
                "first component",
                "•",
            ),
            record(
                3,
                "Second component.",
                "•",
            ),
        ]

        findings = validate_list_structure(
            paragraphs
        )

        checks = [
            finding["Check"]
            for finding in findings
        ]

        self.assertIn(
            "Clinical.ListItemCapitalization",
            checks,
        )

        self.assertIn(
            "Clinical.ListItemEndPunctuation",
            checks,
        )


    def test_manual_bullet_list_is_validated(
        self,
    ) -> None:
        paragraphs = [
            record(
                1,
                "The following components were included.",
            ),
            record(
                2,
                "• first component",
            ),
            record(
                3,
                "• Second component.",
            ),
        ]

        findings = validate_list_structure(
            paragraphs
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.ListIntroductionColon",
            checks,
        )

        self.assertIn(
            "Clinical.ListItemCapitalization",
            checks,
        )

        self.assertIn(
            "Clinical.ListItemEndPunctuation",
            checks,
        )



if __name__ == "__main__":
    unittest.main()
