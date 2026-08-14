from __future__ import annotations

import unittest

from validators.abbreviationvalidator import ParagraphRecord
from validators.captionfootnotevalidator import CaptionRecord, validate_captions
from validators.figurevalidator import validate_figures


def paragraph(index: int, text: str) -> ParagraphRecord:
    return ParagraphRecord(index=index, line=index, text=text)


class CaptionSequenceTests(unittest.TestCase):
    def test_table_label_gap_is_flagged(self) -> None:
        captions = [
            CaptionRecord("Table", "Table 5.", True, paragraph(1, "Table 5.")),
            CaptionRecord("Table", "Table 7.", True, paragraph(2, "Table 7.")),
        ]
        checks = {item["Check"] for item in validate_captions(captions)}
        self.assertIn("Clinical.TableLabelSequence", checks)

    def test_figure_label_gap_is_flagged(self) -> None:
        captions = [
            CaptionRecord("Figure", "Figure 2.", False, paragraph(1, "Figure 2.")),
            CaptionRecord("Figure", "Figure 4.", False, paragraph(2, "Figure 4.")),
        ]
        checks = {
            item["Check"]
            for item in validate_figures(captions=captions, figures=[])
        }
        self.assertIn("Clinical.FigureLabelSequence", checks)

    def test_consecutive_labels_pass(self) -> None:
        captions = [
            CaptionRecord("Table", "Table 5.", True, paragraph(1, "Table 5.")),
            CaptionRecord("Table", "Table 6.", True, paragraph(2, "Table 6.")),
        ]
        checks = {item["Check"] for item in validate_captions(captions)}
        self.assertNotIn("Clinical.TableLabelSequence", checks)


if __name__ == "__main__":
    unittest.main()
