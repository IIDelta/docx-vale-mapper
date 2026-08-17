from __future__ import annotations

import unittest

from validators.abbreviationvalidator import ParagraphRecord
from validators.captionfootnotevalidator import FootnoteRecord, validate_footnotes


def footnote(text: str, position: int, container: str = "table:1") -> FootnoteRecord:
    return FootnoteRecord(
        text=text,
        paragraph=ParagraphRecord(index=position, line=position, text=text),
        range_start=position,
        range_end=position + len(text),
        container_key=container,
    )


class FootnoteOrderTests(unittest.TestCase):
    def test_out_of_order_statistical_note_is_flagged(self) -> None:
        findings = validate_footnotes(
            [
                footnote("Source: Table 1.", 1),
                footnote("a Safety population.", 30),
                footnote("* p<0.05.", 60),
            ]
        )
        checks = {finding["Check"] for finding in findings}
        self.assertIn("Clinical.FootnoteOrder", checks)

    def test_letter_gap_is_flagged_within_one_table(self) -> None:
        findings = validate_footnotes(
            [
                footnote("a Safety population.", 1),
                footnote("c Response population.", 40),
            ]
        )
        checks = {finding["Check"] for finding in findings}
        self.assertIn("Clinical.FootnoteLetterSequence", checks)

    def test_letter_sequence_restarts_for_next_table(self) -> None:
        findings = validate_footnotes(
            [
                footnote("a Safety population.", 1, "table:1"),
                footnote("a Response population.", 40, "table:2"),
            ]
        )
        checks = {finding["Check"] for finding in findings}
        self.assertNotIn("Clinical.FootnoteLetterSequence", checks)


if __name__ == "__main__":
    unittest.main()
