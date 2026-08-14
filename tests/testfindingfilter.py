from __future__ import annotations

import unittest

from validators.abbreviationvalidator import (
    ParagraphRecord,
)
from validators.findingfilter import (
    deduplicate_findings,
    filter_findings_by_context,
)


def record(
    line: int,
    zone: str,
) -> ParagraphRecord:
    """Create a compact context fixture."""

    return ParagraphRecord(
        index=line,
        line=line,
        text="Fixture text",
        content_zone=zone,
    )


class FindingFilterTests(unittest.TestCase):
    """Tests for R2 rule routing and deduplication."""

    def test_body_rule_is_suppressed_on_title_page(self) -> None:
        findings = [
            {
                "Check": "Clinical.Participant",
                "Line": 1,
                "Match": "Patients",
            }
        ]

        retained, suppressed = filter_findings_by_context(
            findings=findings,
            paragraph_records=[
                record(1, "title_page")
            ],
        )

        self.assertEqual(retained, [])
        self.assertEqual(
            sum(suppressed.values()),
            1,
        )

    def test_body_rule_is_kept_in_body_narrative(self) -> None:
        findings = [
            {
                "Check": "Clinical.Participant",
                "Line": 1,
                "Match": "Patients",
            }
        ]

        retained, suppressed = filter_findings_by_context(
            findings=findings,
            paragraph_records=[
                record(1, "body_narrative")
            ],
        )

        self.assertEqual(len(retained), 1)
        self.assertEqual(
            sum(suppressed.values()),
            0,
        )

    def test_duplicate_findings_are_removed(self) -> None:
        findings = [
            {
                "Check": "Clinical.ForwardSlashReview",
                "Line": 3,
                "Span": [12, 17],
                "Match": "and/or",
            },
            {
                "Check": "Clinical.ForwardSlashReview",
                "Line": 3,
                "Span": [12, 17],
                "Match": "and/or",
            },
        ]

        deduplicated = deduplicate_findings(
            findings
        )

        self.assertEqual(
            len(deduplicated),
            1,
        )
