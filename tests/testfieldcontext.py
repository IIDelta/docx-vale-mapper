from __future__ import annotations

import unittest

from validators.abbreviationvalidator import ParagraphRecord
from validators.findingfilter import filter_findings_by_context


class FieldContextTests(unittest.TestCase):
    def test_generic_prose_rule_is_suppressed_in_protected_field(self) -> None:
        record = ParagraphRecord(
            index=1,
            line=1,
            text="Citation field",
            has_protected_field=True,
        )
        findings, suppressed = filter_findings_by_context(
            findings=[
                {
                    "Check": "Clinical.PreferredWordChoices",
                    "Line": 1,
                    "Match": "utilize",
                }
            ],
            paragraph_records=[record],
        )
        self.assertEqual(findings, [])
        self.assertEqual(
            suppressed["Clinical.PreferredWordChoices:protected_word_field"],
            1,
        )

    def test_reference_rule_remains_eligible_in_protected_field(self) -> None:
        record = ParagraphRecord(
            index=1,
            line=1,
            text="Citation field",
            has_protected_field=True,
        )
        findings, suppressed = filter_findings_by_context(
            findings=[
                {
                    "Check": "Clinical.CitationPlacement",
                    "Line": 1,
                    "Match": ". (Smith et al, 2025)",
                }
            ],
            paragraph_records=[record],
        )
        self.assertEqual(len(findings), 1)
        self.assertEqual(suppressed, {})


if __name__ == "__main__":
    unittest.main()
