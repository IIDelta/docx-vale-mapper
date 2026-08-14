from __future__ import annotations

import unittest
from pathlib import Path

from validators.abbreviationvalidator import (
    AbbreviationEntry,
    ParagraphRecord,
    clean_text,
    load_policy,
    validate_first_use,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = PROJECT_ROOT / "config" / "abbreviationpolicy.json"


def record(index: int, text: str) -> ParagraphRecord:
    """Create a concise paragraph fixture."""

    return ParagraphRecord(
        index=index,
        line=index,
        text=text,
    )


class AbbreviationValidatorTests(unittest.TestCase):
    """Regression tests for A4.2 structural abbreviation rules."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.policy = load_policy(POLICY_PATH)

    def test_sorted_abbreviation_list_passes(self) -> None:
        paragraphs = [
            record(1, "LIST OF ABBREVIATIONS"),
        ]

        entries = [
            AbbreviationEntry(
                abbreviation="9vHPV",
                definition="9-valent human papillomavirus",
                source_label="row 1",
            ),
            AbbreviationEntry(
                abbreviation="ACS",
                definition="abnormal clinically significant",
                source_label="row 2",
            ),
            AbbreviationEntry(
                abbreviation="BP",
                definition="blood pressure",
                source_label="row 3",
            ),
        ]

        findings = validate_first_use(
            paragraphs=paragraphs,
            policy=self.policy,
            has_abbreviation_list=True,
            abbreviation_entries=entries,
            list_heading=paragraphs[0],
        )

        checks = {finding["Check"] for finding in findings}

        self.assertNotIn(
            "Clinical.AbbreviationListOrder",
            checks,
        )

    def test_out_of_order_list_is_flagged(self) -> None:
        paragraphs = [
            record(1, "LIST OF ABBREVIATIONS"),
        ]

        entries = [
            AbbreviationEntry(
                abbreviation="BP",
                definition="blood pressure",
                source_label="row 1",
            ),
            AbbreviationEntry(
                abbreviation="9vHPV",
                definition="9-valent human papillomavirus",
                source_label="row 2",
            ),
            AbbreviationEntry(
                abbreviation="ACS",
                definition="abnormal clinically significant",
                source_label="row 3",
            ),
        ]

        findings = validate_first_use(
            paragraphs=paragraphs,
            policy=self.policy,
            has_abbreviation_list=True,
            abbreviation_entries=entries,
            list_heading=paragraphs[0],
        )

        checks = [finding["Check"] for finding in findings]

        self.assertIn(
            "Clinical.AbbreviationListOrder",
            checks,
        )

    def test_duplicate_entry_is_flagged(self) -> None:
        paragraphs = [
            record(1, "LIST OF ABBREVIATIONS"),
        ]

        entries = [
            AbbreviationEntry(
                abbreviation="AE",
                definition="adverse event",
                source_label="row 1",
            ),
            AbbreviationEntry(
                abbreviation="AE",
                definition="adverse event",
                source_label="row 2",
            ),
        ]

        findings = validate_first_use(
            paragraphs=paragraphs,
            policy=self.policy,
            has_abbreviation_list=True,
            abbreviation_entries=entries,
            list_heading=paragraphs[0],
        )

        checks = [finding["Check"] for finding in findings]

        self.assertIn(
            "Clinical.AbbreviationListDuplicate",
            checks,
        )

    def test_missing_definition_is_flagged(self) -> None:
        paragraphs = [
            record(1, "LIST OF ABBREVIATIONS"),
        ]

        entries = [
            AbbreviationEntry(
                abbreviation="AE",
                definition="",
                source_label="row 1",
            ),
        ]

        findings = validate_first_use(
            paragraphs=paragraphs,
            policy=self.policy,
            has_abbreviation_list=True,
            abbreviation_entries=entries,
            list_heading=paragraphs[0],
        )

        checks = [finding["Check"] for finding in findings]

        self.assertIn(
            "Clinical.AbbreviationListMissingDefinition",
            checks,
        )

    def test_defined_abbreviation_without_list_passes(self) -> None:
        paragraphs = [
            record(
                1,
                "The participant experienced an adverse event (AE).",
            ),
            record(
                2,
                "The AE was assessed by the investigator.",
            ),
        ]

        findings = validate_first_use(
            paragraphs=paragraphs,
            policy=self.policy,
            has_abbreviation_list=False,
            abbreviation_entries=[],
            list_heading=None,
        )

        checks = [finding["Check"] for finding in findings]

        self.assertNotIn(
            "Clinical.AbbreviationUndefinedAtFirstUse",
            checks,
        )

    def test_abbreviation_before_definition_is_flagged(self) -> None:
        paragraphs = [
            record(
                1,
                "The AE was assessed by the investigator.",
            ),
            record(
                2,
                "The participant experienced an adverse event (AE).",
            ),
        ]

        findings = validate_first_use(
            paragraphs=paragraphs,
            policy=self.policy,
            has_abbreviation_list=False,
            abbreviation_entries=[],
            list_heading=None,
        )

        checks = [finding["Check"] for finding in findings]

        self.assertIn(
            "Clinical.AbbreviationUndefinedAtFirstUse",
            checks,
        )

    def test_listed_abbreviation_redefined_in_text_is_flagged(self) -> None:
        paragraphs = [
            record(1, "LIST OF ABBREVIATIONS"),
            record(
                2,
                "The participant experienced an adverse event (AE).",
            ),
        ]

        entries = [
            AbbreviationEntry(
                abbreviation="AE",
                definition="adverse event",
                source_label="row 1",
            ),
        ]

        findings = validate_first_use(
            paragraphs=paragraphs,
            policy=self.policy,
            has_abbreviation_list=True,
            abbreviation_entries=entries,
            list_heading=paragraphs[0],
        )

        checks = [finding["Check"] for finding in findings]

        self.assertIn(
            "Clinical.AbbreviationRedefinedInText",
            checks,
        )

    def test_used_abbreviation_missing_from_list_is_flagged(self) -> None:
        paragraphs = [
            record(1, "LIST OF ABBREVIATIONS"),
            record(
                2,
                "The participant experienced an adverse event (AE).",
            ),
        ]

        entries = [
            AbbreviationEntry(
                abbreviation="LFT",
                definition="liver function test",
                source_label="row 1",
            ),
        ]

        findings = validate_first_use(
            paragraphs=paragraphs,
            policy=self.policy,
            has_abbreviation_list=True,
            abbreviation_entries=entries,
            list_heading=paragraphs[0],
        )

        checks = [finding["Check"] for finding in findings]

        self.assertIn(
            "Clinical.AbbreviationMissingFromList",
            checks,
        )

    def test_never_expand_term_is_not_flagged(self) -> None:
        paragraphs = [
            record(
                1,
                "The FDA reviewed the submission.",
            ),
        ]

        findings = validate_first_use(
            paragraphs=paragraphs,
            policy=self.policy,
            has_abbreviation_list=False,
            abbreviation_entries=[],
            list_heading=None,
        )

        self.assertEqual(findings, [])

    def test_clean_text_preserves_token_boundaries(
        self,
    ) -> None:
        raw_text = (
            "XYZ\rEOS\x07FAS\x0bCFR\nFDA"
        )

        cleaned_text = clean_text(raw_text)

        self.assertEqual(
            cleaned_text,
            "XYZ EOS FAS CFR FDA",
        )

    def test_plural_abbreviation_is_covered_by_singular_list_entry(
    self,
    ) -> None:
        paragraphs = [
            record(
                1,
                "LIST OF ABBREVIATIONS",
            ),
            record(
                2,
                "Adverse events (AEs) were reviewed.",
            ),
        ]

        entries = [
            AbbreviationEntry(
                abbreviation="AE",
                definition="adverse event",
                source_label="row 1",
            )
        ]

        findings = validate_first_use(
            paragraphs=paragraphs,
            policy=self.policy,
            has_abbreviation_list=True,
            abbreviation_entries=entries,
            list_heading=paragraphs[0],
        )

        checks = {
            finding["Check"]
            for finding in findings
        }

        self.assertNotIn(
            "Clinical.AbbreviationMissingFromList",
            checks,
        )



if __name__ == "__main__":
    unittest.main()
