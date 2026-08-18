from __future__ import annotations

import unittest

from validators.abbreviationvalidator import (
    ParagraphRecord,
)
from validators.captionfootnotevalidator import (
    CaptionRecord,
)
from validators.figurevalidator import (
    FigureRecord,
    validate_figures,
)


def paragraph(
    index: int,
    text: str,
    start: int,
    end: int,
) -> ParagraphRecord:
    """Create a compact paragraph fixture."""

    return ParagraphRecord(
        index=index,
        line=index,
        text=text,
        range_start=start,
        range_end=end,
    )


class FigureValidatorTests(unittest.TestCase):
    """Tests for A9 figure validation."""

    def test_below_title_and_label_period_are_flagged(
        self,
    ) -> None:
        caption = CaptionRecord(
            kind="Figure",
            text="Figure 1 Efficacy Results",
            inside_table=False,
            paragraph=paragraph(
                2,
                "Figure 1 Efficacy Results",
                200,
                226,
            ),
            range_start=200,
            range_end=226,
        )

        figure = FigureRecord(
            figure_index=1,
            position=150,
            paragraph=paragraph(
                1,
                "Figure anchor",
                150,
                151,
            ),
        )

        findings = validate_figures(
            captions=[caption],
            figures=[figure],
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.FigureTitleBelow",
            checks,
        )

        self.assertIn(
            "Clinical.FigureLabelPeriod",
            checks,
        )


    def test_duplicate_figure_labels_are_flagged(
        self,
    ) -> None:
        captions = [
            CaptionRecord(
                kind="Figure",
                text="Figure 1.",
                inside_table=False,
                paragraph=paragraph(
                    1,
                    "Figure 1.",
                    10,
                    19,
                ),
                range_start=10,
                range_end=19,
            ),
            CaptionRecord(
                kind="Figure",
                text="Figure 1.",
                inside_table=False,
                paragraph=paragraph(
                    2,
                    "Figure 1.",
                    100,
                    109,
                ),
                range_start=100,
                range_end=109,
            ),
        ]

        findings = validate_figures(
            captions=captions,
            figures=[],
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.FigureDuplicateLabel",
            checks,
        )

    def test_missing_caption_is_flagged(self) -> None:
        figure = FigureRecord(
            figure_index=1,
            position=150,
            paragraph=paragraph(
                1,
                "Figure anchor",
                150,
                151,
            ),
        )

        findings = validate_figures(
            captions=[],
            figures=[figure],
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertIn(
            "Clinical.FigureCaptionMissing",
            checks,
        )

