from __future__ import annotations

import unittest

from validators.abbreviationvalidator import ParagraphRecord
from runtime.auditreport import enrich_finding


class AuditProvenanceTests(unittest.TestCase):
    def test_record_populates_missing_top_level_anchor_fields(self) -> None:
        record = ParagraphRecord(index=7, line=10, text="Dose was 5 mg.")
        finding = {"Check": "Clinical.Example", "Match": "5 mg", "Span": [9, 12]}
        result = enrich_finding(finding, record)
        self.assertEqual(result["ParagraphIndex"], 7)
        self.assertEqual(result["Line"], 10)
        self.assertEqual(result["Context"]["paragraph_text"], "Dose was 5 mg.")

    def test_existing_anchor_values_are_preserved(self) -> None:
        record = ParagraphRecord(index=7, line=10, text="Dose was 5 mg.")
        finding = {"Check": "Clinical.Example", "Line": 22, "ParagraphIndex": 15}
        result = enrich_finding(finding, record)
        self.assertEqual(result["ParagraphIndex"], 15)
        self.assertEqual(result["Line"], 22)


if __name__ == "__main__":
    unittest.main()
