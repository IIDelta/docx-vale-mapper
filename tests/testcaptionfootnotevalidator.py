from __future__ import annotations

import unittest

from validators.abbreviationvalidator import (
    ParagraphRecord,
)
from validators.captionfootnotevalidator import (
    CaptionRecord,
    FootnoteRecord,
    validate_captions,
    validate_footnotes,
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


class CaptionFootnoteValidatorTests(unittest.TestCase):
    """Tests for A9 caption and footnote mechanics."""

    def test_external_table_caption_is_flagged(self) -> None:
        caption = CaptionRecord(
            kind="Table",
            text="Table 5 Participant Summary",
            inside_table=False,
            paragraph=paragraph(
                1,
                "Table 5 Participant Summary",
            ),
            range_start=10,
            range_end=37,
        )

        findings = validate_captions([caption])

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.TableCaptionOutsideCell",
            checks,
        )

        self.assertIn(
            "Clinical.TableLabelPeriod",
            checks,
        )

    def test_duplicate_table_labels_are_flagged(self) -> None:
        captions = [
            CaptionRecord(
                kind="Table",
                text="Table 5.",
                inside_table=True,
                paragraph=paragraph(1, "Table 5."),
            ),
            CaptionRecord(
                kind="Table",
                text="Table 5.",
                inside_table=True,
                paragraph=paragraph(2, "Table 5."),
            ),
        ]

        findings = validate_captions(captions)

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.TableDuplicateLabel",
            checks,
        )

    def test_footnote_mechanics_are_flagged(self) -> None:
        footnotes = [
            FootnoteRecord(
                text="Source Table 15.1.1.1",
                paragraph=paragraph(
                    1,
                    "Source Table 15.1.1.1",
                ),
            ),
            FootnoteRecord(
                text="a, b Safety population",
                paragraph=paragraph(
                    2,
                    "a, b Safety population",
                ),
            ),
            FootnoteRecord(
                text="* Safety population note",
                paragraph=paragraph(
                    3,
                    "* Safety population note",
                ),
            ),
        ]

        findings = validate_footnotes(footnotes)

        checks = [
            finding["Check"]
            for finding in findings
        ]

        self.assertIn(
            "Clinical.FootnoteSourceColon",
            checks,
        )

        self.assertIn(
            "Clinical.FootnoteDesignatorSpacing",
            checks,
        )

        self.assertIn(
            "Clinical.FootnoteSymbolDesignator",
            checks,
        )

        self.assertEqual(
            checks.count(
                "Clinical.FootnoteEndPunctuation"
            ),
            3,
        )
