from __future__ import annotations

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
