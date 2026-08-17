from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from validators.abbreviationvalidator import ParagraphRecord
from validators.scientificterms import load_scientific_terms, validate_scientific_terms


class ScientificTermsTests(unittest.TestCase):
    def test_registry_terms_are_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "terms.json"
            path.write_text(json.dumps({"italic_required": ["Escherichia coli", "Escherichia coli"], "roman_required": ["in vitro"]}), encoding="utf-8")
            registry = load_scientific_terms(path)
        self.assertEqual(registry["italic_required"], ["Escherichia coli"])

    def test_configured_italic_term_is_flagged_when_roman(self) -> None:
        paragraph = ParagraphRecord(index=1, line=1, text="Escherichia coli")
        findings = validate_scientific_terms(
            paragraph,
            "Escherichia coli",
            lambda start, end: {"italic": False},
            {"italic_required": ["Escherichia coli"], "roman_required": []},
        )
        self.assertEqual(findings[0]["Check"], "Clinical.ConfiguredItalicRequired")

    def test_unknown_scientific_looking_term_is_not_flagged(self) -> None:
        paragraph = ParagraphRecord(index=1, line=1, text="BRCA1")
        findings = validate_scientific_terms(
            paragraph,
            "BRCA1",
            lambda start, end: {"italic": False},
            {"italic_required": [], "roman_required": []},
        )
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
