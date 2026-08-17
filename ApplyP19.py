from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path.cwd()
EXPECTED_HEAD = "0ffd88b77eb0afa04fdf95b54feb76d89039a2d6"
TYPOGRAPHY = ROOT / "validators" / "typographyvalidator.py"
HEADING = ROOT / "validators" / "headingvalidator.py"
NUMERAL = ROOT / "Styles" / "Clinical" / "NumeralAtSentenceStart.yml"
TEST = ROOT / "tests" / "testcalibration.py"

NUMERAL_SOURCE = '''# Takeda Style Guide v6.0, section 7.1:
# Review integer-led narrative sentences only. Decimal values and section
# identifiers require structural or editorial context and are not flagged.
extends: existence
message: "Style guide numbers: Do not begin a running-text sentence with a numeral; spell it out or recast the sentence."
level: warning
tokens:
  - '^\\s*[1-9]\\d{0,2}\\s+[A-Za-z]'
'''

TEST_SOURCE = '''from __future__ import annotations

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
        self.assertEqual(finding["Action"]["Params"], ["5\\u00a0mg"])


if __name__ == "__main__":
    unittest.main()
'''


def head():
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

def once(text, old, new, label):
    if text.count(old) != 1:
        raise RuntimeError(f"Expected one {label} target; found {text.count(old)}.")
    return text.replace(old, new, 1)

def main():
    if head() != EXPECTED_HEAD:
        raise RuntimeError(f"Expected {EXPECTED_HEAD}; current HEAD is {head()}.")
    if TEST.exists():
        raise RuntimeError(f"Refusing to overwrite {TEST}")
    t = TYPOGRAPHY.read_text(encoding="utf-8").replace("\r\n", "\n")
    h = HEADING.read_text(encoding="utf-8").replace("\r\n", "\n")
    newline = "\r\n" if "\r\n" in TYPOGRAPHY.read_text(encoding="utf-8") else "\n"
    h = once(h, 'MINOR_WORDS = {\n', 'UNIT_ABBREVIATIONS = {"µg", "ug", "mg", "g", "kg", "ng", "pg", "ml", "l", "dl", "mm", "cm", "m", "km", "min", "h", "s"}\n\nMINOR_WORDS = {\n', "heading unit exemption")
    h = once(h, '    if alpha_text.isupper():\n', '    if alpha_text.isupper():\n        if paragraph.heading_level == 1:\n            return []\n', "Heading 1 caps exception")
    h = once(h, '            elif not should_be_minor and piece[0].islower():\n', '            elif (\n                not should_be_minor\n                and normalized not in UNIT_ABBREVIATIONS\n                and piece[0].islower()\n            ):\n', "heading unit check")
    old = '''        findings.append(
            make_finding(
                check="Clinical.UnitNonbreakingSpace",
                severity="warning",
                message=(
                    "Style guide units: Use a nonbreaking space between a "
                    "numeric value and its unit in body text."
                ),
                match=match.group(0),
                paragraph=paragraph,
            )
        )
'''
    new = '''        finding = make_finding(
            check="Clinical.UnitNonbreakingSpace",
            severity="suggestion",
            message=(
                "Style guide units: Use a nonbreaking space between a "
                "numeric value and its unit in body text."
            ),
            match=match.group(0),
            paragraph=paragraph,
        )
        finding["Action"] = {
            "Name": "replace",
            "Params": [match.group(0).replace(" ", "\\u00a0", 1)],
        }
        findings.append(finding)
'''
    t = once(t, old, new, "unit replacement suggestion")
    HEADING.write_text(h.replace("\n", newline), encoding="utf-8")
    TYPOGRAPHY.write_text(t.replace("\n", newline), encoding="utf-8")
    NUMERAL.write_text(NUMERAL_SOURCE, encoding="utf-8")
    TEST.write_text(TEST_SOURCE.replace("\n", newline), encoding="utf-8")
    print("P19 calibration installed successfully.")
    print("Run: python -m unittest tests.testcalibration -v")
    print("Then: python tests/runregressiontests.py")

if __name__ == "__main__":
    main()
