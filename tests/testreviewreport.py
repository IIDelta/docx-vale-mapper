from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from abbreviations.reviewreport import (
    build_review_rows,
    load_candidate_report,
    write_csv_report,
    write_markdown_report,
)


class ReviewReportTests(unittest.TestCase):
    """Tests for B3.3 candidate review exports."""

    def create_candidate_report(self) -> dict:
        """Create a representative candidate report."""

        return {
            "candidate_count": 4,
            "candidates": [
                {
                    "token": "FDA",
                    "count": 1,
                    "first_paragraph_index": 1,
                    "contexts": [
                        "The FDA reviewed the document."
                    ],
                    "review_bucket": "protected",
                    "confidence": "high",
                    "resolution": {
                        "status": "approved_no_expand",
                        "preferred_definition": "",
                        "replacement_token": "",
                        "enforcement_action": (
                            "do_not_require_expansion"
                        ),
                        "source_reference": "policy_protected_terms",
                        "notes": "Protected term.",
                    },
                },
                {
                    "token": "XYZ",
                    "count": 2,
                    "first_paragraph_index": 4,
                    "contexts": [
                        "The XYZ result was reviewed.",
                        "The XYZ result was confirmed.",
                    ],
                    "review_bucket": "likely_unknown",
                    "confidence": "likely",
                    "resolution": {
                        "status": "unknown",
                        "preferred_definition": "",
                        "replacement_token": "",
                        "enforcement_action": "candidate_review",
                        "source_reference": "",
                        "notes": (
                            "No reviewed registry entry exists."
                        ),
                    },
                },
                {
                    "token": "EOS",
                    "count": 1,
                    "first_paragraph_index": 2,
                    "contexts": [
                        "The legacy file uses EOS."
                    ],
                    "review_bucket": "deprecated",
                    "confidence": "high",
                    "resolution": {
                        "status": "deprecated",
                        "preferred_definition": "End of Study",
                        "replacement_token": "EOT",
                        "enforcement_action": (
                            "warn_and_suggest_replacement"
                        ),
                        "source_reference": "style_guide_appendix_c",
                        "notes": "Deprecated term.",
                    },
                },
                {
                    "token": "FAS",
                    "count": 1,
                    "first_paragraph_index": 3,
                    "contexts": [
                        "The FAS was analyzed."
                    ],
                    "review_bucket": "ambiguous",
                    "confidence": "high",
                    "resolution": {
                        "status": "ambiguous",
                        "preferred_definition": "",
                        "replacement_token": "",
                        "enforcement_action": (
                            "manual_definition_review"
                        ),
                        "source_reference": "legacy_source",
                        "notes": "Multiple definitions.",
                    },
                },
            ],
        }

    def test_review_rows_are_priority_sorted(self) -> None:
        rows = build_review_rows(
            self.create_candidate_report()
        )

        self.assertEqual(
            [row["token"] for row in rows],
            [
                "EOS",
                "FAS",
                "XYZ",
                "FDA",
            ],
        )

        self.assertEqual(
            [row["priority"] for row in rows],
            [1, 2, 3, 8],
        )

    def test_csv_export_contains_reviewer_columns(self) -> None:
        rows = build_review_rows(
            self.create_candidate_report()
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = (
                Path(temporary_directory)
                / "review.csv"
            )

            write_csv_report(
                rows=rows,
                output_path=output_path,
            )

            with output_path.open(
                newline="",
                encoding="utf-8",
            ) as input_file:
                exported_rows = list(
                    csv.DictReader(input_file)
                )

        self.assertEqual(
            len(exported_rows),
            4,
        )

        self.assertIn(
            "reviewer_decision",
            exported_rows[0],
        )

        self.assertIn(
            "reviewer_notes",
            exported_rows[0],
        )

        self.assertEqual(
            exported_rows[0]["token"],
            "EOS",
        )

    def test_markdown_export_contains_summary_and_context(
        self,
    ) -> None:
        rows = build_review_rows(
            self.create_candidate_report()
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = (
                Path(temporary_directory)
                / "review.md"
            )

            write_markdown_report(
                rows=rows,
                output_path=output_path,
            )

            markdown = output_path.read_text(
                encoding="utf-8",
            )

        self.assertIn(
            "# Abbreviation Candidate Review Report",
            markdown,
        )

        self.assertIn(
            "### EOS — deprecated",
            markdown,
        )

        self.assertIn(
            "Replacement token:** EOT",
            markdown,
        )

        self.assertIn(
            "The XYZ result was reviewed.",
            markdown,
        )

    def test_json_report_can_be_loaded(self) -> None:
        report = self.create_candidate_report()

        with tempfile.TemporaryDirectory() as temporary_directory:
            input_path = (
                Path(temporary_directory)
                / "candidate.json"
            )

            input_path.write_text(
                json.dumps(report),
                encoding="utf-8",
            )

            loaded_report = load_candidate_report(
                input_path
            )

        self.assertEqual(
            loaded_report["candidate_count"],
            4,
        )


if __name__ == "__main__":
    unittest.main()
