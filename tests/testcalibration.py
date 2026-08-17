from __future__ import annotations

import unittest

from validators.abbreviationvalidator import ParagraphRecord
from validators.headingvalidator import validate_heading_paragraph
from validators.typographyvalidator import validate_unit_nonbreaking_spaces


class CalibrationTests(unittest.TestCase):
    def test_heading_one_all_caps_is_template_exception(self) -> None:
        paragraph = ParagraphRecord(index=1, line=1, text="SIGNATURE", is_heading=True, heading_level=1)
        findings = validate_heading_paragraph(paragraph, "SIGNATURE", {"all_caps": False, "small_caps": False})
        self.assertEqual(findings, [])

    def test_unit_abbreviation_in_heading_is_not_title_case_error(self) -> None:
        paragraph = ParagraphRecord(index=1, line=1, text="Dose of 5 mg", is_heading=True)
        findings = validate_heading_paragraph(paragraph, "Dose of 5 mg", {"all_caps": False, "small_caps": False})
        self.assertNotIn("Clinical.HeadingTitleCase", {item["Check"] for item in findings})

    def test_unit_spacing_exposes_safe_replacement(self) -> None:
        paragraph = ParagraphRecord(index=1, line=1, text="5 mg")
        finding = validate_unit_nonbreaking_spaces(paragraph, "5 mg")[0]
        self.assertEqual(finding["Severity"], "suggestion")
        self.assertEqual(finding["Action"]["Params"], ["5\u00a0mg"])


if __name__ == "__main__":
    unittest.main()
