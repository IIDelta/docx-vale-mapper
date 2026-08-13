from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from abbreviations.legacyimport import (
    import_legacy_source,
    open_database,
)
from abbreviations.reviewpromote import apply_review_seed


class ReviewPromotionTests(unittest.TestCase):
    """Tests for B2 registry review and promotion."""

    def test_review_seed_creates_registry_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            database_path = root / "abbreviations.sqlite"
            source_path = root / "legacy.tsv"
            seed_path = root / "reviewseed.json"
            policy_path = root / "policy.json"

            source_path.write_text(
                "\n".join(
                    [
                        "CFR\tCode of Federal Regulation",
                        "CFR\tCode of Federal Regulations",
                        "EOS\tEnd of Study",
                        "FAS\tFull Analysis Set",
                        "FAS\tFull Analysis Set Population",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            seed_path.write_text(
                json.dumps(
                    {
                        "decision_set": "test_review",
                        "decisions": [
                            {
                                "token": "CFR",
                                "definition": (
                                    "Code of Federal Regulations"
                                ),
                                "status": "approved_expand",
                                "source_reference": "test_source",
                                "notes": "Resolved conflict."
                            },
                            {
                                "token": "EOS",
                                "definition": "End of Study",
                                "status": "deprecated",
                                "source_reference": "test_source",
                                "replacement_token": "EOT",
                                "notes": "Deprecated term."
                            },
                            {
                                "token": "FAS",
                                "definition": "",
                                "status": "ambiguous",
                                "source_reference": "test_source",
                                "notes": "Multiple definitions."
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            policy_path.write_text(
                json.dumps(
                    {
                        "never_expand": [
                            "FDA",
                            "US",
                        ]
                    }
                ),
                encoding="utf-8",
            )

            import_legacy_source(
                database_path=database_path,
                source_path=source_path,
            )

            report = apply_review_seed(
                database_path=database_path,
                seed_path=seed_path,
                policy_path=policy_path,
            )

            self.assertEqual(
                report["seed_decisions_applied"],
                3,
            )

            with open_database(database_path) as connection:
                rows = connection.execute(
                    """
                    SELECT
                        token,
                        preferred_definition,
                        status,
                        replacement_token
                    FROM registry_entries
                    ORDER BY token
                    """
                ).fetchall()

            self.assertIn(
                (
                    "CFR",
                    "Code of Federal Regulations",
                    "approved_expand",
                    "",
                ),
                rows,
            )

            self.assertIn(
                (
                    "EOS",
                    "End of Study",
                    "deprecated",
                    "EOT",
                ),
                rows,
            )

            self.assertIn(
                (
                    "FAS",
                    "",
                    "ambiguous",
                    "",
                ),
                rows,
            )

            self.assertIn(
                (
                    "FDA",
                    "",
                    "approved_no_expand",
                    "",
                ),
                rows,
            )

    def test_review_promotion_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            database_path = root / "abbreviations.sqlite"
            source_path = root / "legacy.tsv"
            seed_path = root / "reviewseed.json"
            policy_path = root / "policy.json"

            source_path.write_text(
                "CFR\tCode of Federal Regulations\n",
                encoding="utf-8",
            )

            seed_path.write_text(
                json.dumps(
                    {
                        "decision_set": "test_review",
                        "decisions": [
                            {
                                "token": "CFR",
                                "definition": (
                                    "Code of Federal Regulations"
                                ),
                                "status": "approved_expand",
                                "source_reference": "test_source",
                                "notes": "Reviewed."
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            policy_path.write_text(
                json.dumps(
                    {
                        "never_expand": []
                    }
                ),
                encoding="utf-8",
            )

            import_legacy_source(
                database_path=database_path,
                source_path=source_path,
            )

            apply_review_seed(
                database_path=database_path,
                seed_path=seed_path,
                policy_path=policy_path,
            )

            apply_review_seed(
                database_path=database_path,
                seed_path=seed_path,
                policy_path=policy_path,
            )

            with open_database(database_path) as connection:
                registry_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM registry_entries
                    """
                ).fetchone()[0]

                decision_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM review_decisions
                    """
                ).fetchone()[0]

            self.assertEqual(registry_count, 1)
            self.assertEqual(decision_count, 1)


if __name__ == "__main__":
    unittest.main()
