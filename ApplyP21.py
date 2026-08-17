from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path.cwd()
EXPECTED_HEAD = "177debad1653191746fe7f772d0f1656eb0df6af"
TYPOGRAPHY_PATH = ROOT / "validators" / "typographyvalidator.py"
UNIT_STYLES_PATH = ROOT / "validators" / "unitstyles.py"
CONFIG_PATH = ROOT / "config" / "unitstyles.json"
MAIN_PATH = ROOT / "main.py"
TEST_PATH = ROOT / "tests" / "testunitstyles.py"

CONFIG = {"excluded_style_names": ["A-Table Footnote", "A-Footnote"]}

UNIT_STYLES_SOURCE = '''from __future__ import annotations

import json
from pathlib import Path


def load_unit_style_exemptions(config_path: Path) -> set[str]:
    """Load exact Word style names exempt from unit-spacing suggestions."""
    if not config_path.is_file():
        return set()
    with config_path.open(encoding="utf-8") as input_file:
        payload = json.load(input_file)
    values = payload.get("excluded_style_names", [])
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError("excluded_style_names must be a list of strings.")
    return {value.strip().casefold() for value in values if value.strip()}
'''

TEST_SOURCE = '''from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from validators.abbreviationvalidator import ParagraphRecord
from validators.typographyvalidator import validate_unit_nonbreaking_spaces
from validators.unitstyles import load_unit_style_exemptions


class UnitStyleTests(unittest.TestCase):
    def test_table_footnote_style_is_exempt(self) -> None:
        paragraph = ParagraphRecord(index=1, line=1, text="0.75 mg", style_name="A-Table Footnote")
        findings = validate_unit_nonbreaking_spaces(paragraph, "0.75 mg", {"a-table footnote"})
        self.assertEqual(findings, [])

    def test_body_text_remains_eligible(self) -> None:
        paragraph = ParagraphRecord(index=1, line=1, text="0.75 mg", style_name="A-Body Text")
        findings = validate_unit_nonbreaking_spaces(paragraph, "0.75 mg", {"a-table footnote"})
        self.assertEqual(findings[0]["Check"], "Clinical.UnitNonbreakingSpace")

    def test_style_registry_normalizes_case(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "styles.json"
            path.write_text(json.dumps({"excluded_style_names": ["A-Footnote"]}), encoding="utf-8")
            styles = load_unit_style_exemptions(path)
        self.assertEqual(styles, {"a-footnote"})


if __name__ == "__main__":
    unittest.main()
'''


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

def once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"Expected one {label} target; found {text.count(old)}.")
    return text.replace(old, new, 1)

def main() -> None:
    if head() != EXPECTED_HEAD:
        raise RuntimeError(f"Expected {EXPECTED_HEAD}; current HEAD is {head()}.")
    if any(path.exists() for path in (UNIT_STYLES_PATH, CONFIG_PATH, TEST_PATH)):
        raise RuntimeError("P21 files already exist. Refusing to overwrite committed work.")
    newline = "\r\n" if "\r\n" in MAIN_PATH.read_text(encoding="utf-8") else "\n"
    main = MAIN_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
    typography = TYPOGRAPHY_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")

    typography = once(typography, '    raw_text: str,\n) -> list[dict]:\n', '    raw_text: str,\n    excluded_style_names: set[str] | None = None,\n) -> list[dict]:\n', 'unit validator signature')
    typography = once(typography, '    if paragraph.content_zone != "body_narrative":\n        return []\n', '    if paragraph.content_zone != "body_narrative":\n        return []\n    if paragraph.style_name.casefold() in (excluded_style_names or set()):\n        return []\n', 'unit style exclusion')

    main = once(main, 'from validators.typographyvalidator import (\n', 'from validators.unitstyles import (\n    load_unit_style_exemptions,\n)\nfrom validators.typographyvalidator import (\n', 'unit style import')
    main = once(main, 'HEADING_TERMS_PATH = (\n    PROJECT_ROOT / "config" / "headingterms.json"\n)\n', 'HEADING_TERMS_PATH = (\n    PROJECT_ROOT / "config" / "headingterms.json"\n)\n\nUNIT_STYLES_PATH = (\n    PROJECT_ROOT / "config" / "unitstyles.json"\n)\n', 'unit style path')
    main = once(main, '    heading_terms = load_heading_terms(HEADING_TERMS_PATH)\n', '    heading_terms = load_heading_terms(HEADING_TERMS_PATH)\n    unit_style_exemptions = load_unit_style_exemptions(UNIT_STYLES_PATH)\n', 'unit style load')
    main = once(main, '                raw_text=raw_text,\n            )\n', '                raw_text=raw_text,\n                excluded_style_names=unit_style_exemptions,\n            )\n', 'unit style argument')

    TYPOGRAPHY_PATH.write_text(typography.replace("\n", newline), encoding="utf-8")
    MAIN_PATH.write_text(main.replace("\n", newline), encoding="utf-8")
    UNIT_STYLES_PATH.write_text(UNIT_STYLES_SOURCE.replace("\n", newline), encoding="utf-8")
    CONFIG_PATH.write_text(json.dumps(CONFIG, indent=2) + "\n", encoding="utf-8")
    TEST_PATH.write_text(TEST_SOURCE.replace("\n", newline), encoding="utf-8")
    print("P21 unit style exclusions installed successfully.")
    print("Run: python -m unittest tests.testunitstyles -v")
    print("Then: python tests/runregressiontests.py")

if __name__ == "__main__":
    main()
