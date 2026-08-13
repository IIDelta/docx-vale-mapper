from __future__ import annotations

import unittest

from validators.abbreviationvalidator import (
    ParagraphRecord,
)
from validators.typographyvalidator import (
    validate_typography_paragraph,
)


def record(
    index: int,
    text: str,
) -> ParagraphRecord:
    """Create a compact paragraph fixture."""

    return ParagraphRecord(
        index=index,
        line=index,
        text=text,
    )


def format_state(
    italic: bool = False,
    superscript: bool = False,
):
    """Return a formatting callback with fixed formatting state."""

    def lookup(
        _start: int,
        _end: int,
    ) -> dict[str, bool]:
        return {
            "italic": italic,
            "superscript": superscript,
        }

    return lookup


class TypographyValidatorTests(unittest.TestCase):
    """Tests for A8.1 typography rules."""

    def test_species_requires_italics(self) -> None:
        findings = validate_typography_paragraph(
            paragraph=record(
                1,
                "Staphylococcus aureus was cultured.",
            ),
            offset_preserving_text=(
                "Staphylococcus aureus was cultured."
            ),
            get_format=format_state(
                italic=False,
            ),
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.ItalicRequired",
            checks,
        )

    def test_latin_expression_requires_roman_format(self) -> None:
        findings = validate_typography_paragraph(
            paragraph=record(
                1,
                "The assay was conducted in vitro.",
            ),
            offset_preserving_text=(
                "The assay was conducted in vitro."
            ),
            get_format=format_state(
                italic=True,
            ),
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.RomanRequired",
            checks,
        )

    def test_radiolabel_requires_superscript_isotope(self) -> None:
        findings = validate_typography_paragraph(
            paragraph=record(
                1,
                "[14C]metformin was administered.",
            ),
            offset_preserving_text=(
                "[14C]metformin was administered."
            ),
            get_format=format_state(
                superscript=False,
            ),
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.RadiolabelSuperscript",
            checks,
        )

    def test_radiolabel_spacing_is_flagged(self) -> None:
        findings = validate_typography_paragraph(
            paragraph=record(
                1,
                "[14 C] metformin was administered.",
            ),
            offset_preserving_text=(
                "[14 C] metformin was administered."
            ),
            get_format=format_state(),
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.RadiolabelSpacing",
            checks,
        )

    def test_compliant_radiolabel_passes(self) -> None:
        findings = validate_typography_paragraph(
            paragraph=record(
                1,
                "[14C]metformin was administered.",
            ),
            offset_preserving_text=(
                "[14C]metformin was administered."
            ),
            get_format=format_state(
                superscript=True,
            ),
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertNotIn(
            "Clinical.RadiolabelSuperscript",
            checks,
        )

        self.assertNotIn(
            "Clinical.RadiolabelSpacing",
            checks,
        )


if __name__ == "__main__":
    unittest.main()
