from __future__ import annotations

import unittest

from validators.abbreviationvalidator import ParagraphRecord
from validators.headingvalidator import validate_heading_paragraph


def heading(text: str) -> ParagraphRecord:
    return ParagraphRecord(
        index=1,
        line=1,
        text=text,
        is_heading=True,
    )


class HeadingValidatorTests(unittest.TestCase):
    def test_title_case_heading_passes(self) -> None:
        findings = validate_heading_paragraph(
            heading("Study Results for the Trial"),
            "Study Results for the Trial",
            {"all_caps": False, "small_caps": False},
        )
        self.assertEqual(findings, [])

    def test_minor_word_capitalization_is_flagged(self) -> None:
        findings = validate_heading_paragraph(
            heading("Study Results For The Trial"),
            "Study Results For The Trial",
            {"all_caps": False, "small_caps": False},
        )
        checks = {finding["Check"] for finding in findings}
        self.assertIn("Clinical.HeadingMinorWordCase", checks)

    def test_manually_typed_all_caps_is_flagged(self) -> None:
        findings = validate_heading_paragraph(
            heading("STUDY RESULTS FOR THE TRIAL"),
            "STUDY RESULTS FOR THE TRIAL",
            {"all_caps": False, "small_caps": False},
        )
        self.assertEqual(findings[0]["Check"], "Clinical.HeadingAllCapsTyped")

    def test_word_all_caps_formatting_is_not_flagged(self) -> None:
        findings = validate_heading_paragraph(
            heading("STUDY RESULTS FOR THE TRIAL"),
            "STUDY RESULTS FOR THE TRIAL",
            {"all_caps": True, "small_caps": False},
        )
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
