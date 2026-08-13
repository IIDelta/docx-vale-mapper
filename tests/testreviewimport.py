from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from abbreviations.legacyimport import (
    initialize_database,
    open_database,
)
from abbreviations.registryapi import resolve_token
from abbreviations.reviewimport import (
    apply_review_import,
    load_review_rows,
    validate_review_rows,
)
from abbreviations.reviewpromote import ensure_review_schema


CSV_HEADERS = [
    "token",
    "preferred_definition",
    "replacement_token",
    "reviewer_decision",
    "reviewer_notes",
]


class ReviewImportTests(unittest.TestCase):
    """Tests for B3.4 reviewer decision import."""

    def create_database(self) -> Path:
        """Create a temporary reviewed-registry database."""

        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)

        database_path = (
            Path(temporary_directory.name)
            / "abbreviations.sqlite"
        )

        initialize_database(database_path)

        with open_database(database_path) as connection:
            ensure_review_schema(connection)

        return database_path

    def write_csv(
        self,
        output_path: Path,
        rows: list[dict[str, str]],
    ) -> None:
        """Write a compact review CSV fixture."""

        with output_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as output_file:
            writer = csv.DictWriter(
                output_file,
                fieldnames=CSV_HEADERS,
            )

            writer.writeheader()
            writer.writerows(rows)

    def test_valid_csv_promotes_and_ignores_terms(self) -> None:
        database_path = self.create_database()

        with tempfile.TemporaryDirectory() as temporary_directory:
            csv_path = (
                Path(temporary_directory)
                / "review.csv"
            )

            self.write_csv(
                csv_path,
                [
                    {
                        "token": "AUC0-24",
                        "preferred_definition": (
                            "Area under the plasma concentration-time "
                            "curve over 24 hours"
                        ),
                        "replacement_token": "",
                        "reviewer_decision": "approved_expand",
                        "reviewer_notes": (
                            "Approved pharmacokinetic term."
                        ),
                    },
                    {
                        "token": "XYZ",
                        "preferred_definition": "",
                        "replacement_token": "",
                        "reviewer_decision": "ignored",
                        "reviewer_notes": (
                            "Placeholder term in test fixture."
                        ),
                    },
                    {
                        "token": "FAS",
                        "preferred_definition": "",
                        "replacement_token": "",
                        "reviewer_decision": "",
                        "reviewer_notes": "",
                    },
                ],
            )

            raw_rows = load_review_rows(csv_path)

            review_rows, skipped_rows = validate_review_rows(
                raw_rows
            )

        self.assertEqual(len(review_rows), 2)
        self.assertEqual(skipped_rows, 1)

        report = apply_review_import(
            database_path=database_path,
            review_rows=review_rows,
            reviewer="test_reviewer",
            decision_set="test_csv_import",
        )

        self.assertEqual(
            report["review_rows_applied"],
            2,
        )

        auc_result = resolve_token(
            database_path=database_path,
            token="AUC0-24",
        )

        xyz_result = resolve_token(
            database_path=database_path,
            token="XYZ",
        )

        self.assertTrue(auc_result.found)
        self.assertEqual(
            auc_result.status,
            "approved_expand",
        )

        self.assertEqual(
            auc_result.preferred_definition,
            (
                "Area under the plasma concentration-time "
                "curve over 24 hours"
            ),
        )

        self.assertTrue(xyz_result.found)
        self.assertEqual(
            xyz_result.status,
            "ignored",
        )

    def test_approved_expand_requires_definition(self) -> None:
        invalid_rows = [
            {
                "token": "XYZ",
                "preferred_definition": "",
                "replacement_token": "",
                "reviewer_decision": "approved_expand",
                "reviewer_notes": "",
            }
        ]

        with self.assertRaises(ValueError) as error:
            validate_review_rows(invalid_rows)

        self.assertIn(
            "has no preferred_definition",
            str(error.exception),
        )

    def test_deprecated_requires_replacement(self) -> None:
        invalid_rows = [
            {
                "token": "OLD",
                "preferred_definition": "Old term",
                "replacement_token": "",
                "reviewer_decision": "deprecated",
                "reviewer_notes": "",
            }
        ]

        with self.assertRaises(ValueError) as error:
            validate_review_rows(invalid_rows)

        self.assertIn(
            "has no replacement_token",
            str(error.exception),
        )

    def test_duplicate_decisions_are_rejected(self) -> None:
        invalid_rows = [
            {
                "token": "XYZ",
                "preferred_definition": "",
                "replacement_token": "",
                "reviewer_decision": "ignored",
                "reviewer_notes": "",
            },
            {
                "token": "xyz",
                "preferred_definition": "",
                "replacement_token": "",
                "reviewer_decision": "ignored",
                "reviewer_notes": "",
            },
        ]

        with self.assertRaises(ValueError) as error:
            validate_review_rows(invalid_rows)

        self.assertIn(
            "multiple reviewer decisions",
            str(error.exception),
        )


if __name__ == "__main__":
    unittest.main()
