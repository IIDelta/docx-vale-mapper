from __future__ import annotations

import unittest

from validators.abbreviationvalidator import (
    ParagraphRecord,
)
from validators.appendixvalidator import (
    AppendixElementRecord,
    find_appendix_context,
    validate_appendix_elements,
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


class AppendixValidatorTests(unittest.TestCase):
    """Tests for A9 appendix table and figure numbering."""

    def test_appendix_context_is_detected(self) -> None:
        paragraphs = [
            paragraph(1, "Appendix A Trial Information"),
            paragraph(2, "Table A-1."),
            paragraph(3, "Appendix B Additional Data"),
            paragraph(4, "Figure B-1."),
        ]

        context = find_appendix_context(
            paragraphs
        )

        self.assertEqual(context[2], "A")
        self.assertEqual(context[4], "B")

    def test_body_style_label_in_appendix_is_flagged(
        self,
    ) -> None:
        element = AppendixElementRecord(
            kind="Table",
            label="1",
            text="Table 1.",
            appendix_letter="A",
            paragraph=paragraph(2, "Table 1."),
        )

        findings = validate_appendix_elements(
            [element]
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.AppendixElementPrefix",
            checks,
        )

    def test_wrong_appendix_prefix_is_flagged(
        self,
    ) -> None:
        element = AppendixElementRecord(
            kind="Figure",
            label="A-1",
            text="Figure A-1.",
            appendix_letter="B",
            paragraph=paragraph(2, "Figure A-1."),
        )

        findings = validate_appendix_elements(
            [element]
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.AppendixElementPrefix",
            checks,
        )

    def test_sequence_gap_is_flagged(self) -> None:
        elements = [
            AppendixElementRecord(
                kind="Table",
                label="A-1",
                text="Table A-1.",
                appendix_letter="A",
                paragraph=paragraph(2, "Table A-1."),
            ),
            AppendixElementRecord(
                kind="Table",
                label="A-3",
                text="Table A-3.",
                appendix_letter="A",
                paragraph=paragraph(3, "Table A-3."),
            ),
        ]

        findings = validate_appendix_elements(
            elements
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.AppendixElementSequence",
            checks,
        )

    def test_valid_appendix_elements_pass(self) -> None:
        elements = [
            AppendixElementRecord(
                kind="Table",
                label="A-1",
                text="Table A-1.",
                appendix_letter="A",
                paragraph=paragraph(2, "Table A-1."),
            ),
            AppendixElementRecord(
                kind="Table",
                label="A-2",
                text="Table A-2.",
                appendix_letter="A",
                paragraph=paragraph(3, "Table A-2."),
            ),
            AppendixElementRecord(
                kind="Figure",
                label="A-1",
                text="Figure A-1.",
                appendix_letter="A",
                paragraph=paragraph(4, "Figure A-1."),
            ),
        ]

        findings = validate_appendix_elements(
            elements
        )

        self.assertEqual(findings, [])
