from __future__ import annotations

import unittest

from validators.findingmerge import merge_audit_findings


class FindingMergeTests(unittest.TestCase):
    """Tests for Vale and structural finding merge behavior."""

    def test_deprecated_warning_is_suppressed_when_vale_matches(
        self,
    ) -> None:
        vale_findings = [
            {
                "Check": "Clinical.EndOfTrial",
                "Severity": "error",
                "Match": "EOS",
                "Message": "Use EOT instead of EOS.",
            }
        ]

        structural_findings = [
            {
                "Check": "Clinical.AbbreviationDeprecated",
                "Severity": "warning",
                "Match": "EOS",
                "Message": "EOS is deprecated.",
            },
            {
                "Check": (
                    "Clinical.AbbreviationUndefinedAtFirstUse"
                ),
                "Severity": "warning",
                "Match": "AUC0-24",
                "Message": "Define AUC0-24 at first use.",
            },
        ]

        merged = merge_audit_findings(
            vale_findings=vale_findings,
            structural_findings=structural_findings,
        )

        checks = [
            finding["Check"]
            for finding in merged
        ]

        self.assertEqual(
            checks,
            [
                "Clinical.EndOfTrial",
                "Clinical.AbbreviationUndefinedAtFirstUse",
            ],
        )

    def test_deprecated_warning_is_kept_without_vale_match(
        self,
    ) -> None:
        merged = merge_audit_findings(
            vale_findings=[],
            structural_findings=[
                {
                    "Check": (
                        "Clinical.AbbreviationDeprecated"
                    ),
                    "Severity": "warning",
                    "Match": "EOS",
                    "Message": "EOS is deprecated.",
                }
            ],
        )

        self.assertEqual(len(merged), 1)

        self.assertEqual(
            merged[0]["Check"],
            "Clinical.AbbreviationDeprecated",
        )


if __name__ == "__main__":
    unittest.main()
