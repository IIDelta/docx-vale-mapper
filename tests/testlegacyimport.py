from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from abbreviations.legacyimport import (
    import_legacy_source,
    open_database,
)

class LegacyImportTests(unittest.TestCase):
    """Tests for quarantined legacy acronym import behavior."""

    def test_import_detects_duplicates_and_conflicts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            source_path = root / "legacy.tsv"
            database_path = root / "abbreviations.sqlite"

            source_path.write_text(
                "\n".join(
                    [
                        "AE\tAdverse Event",
                        "AE\tAdverse Event",
                        "AE\tAdverse Event Different",
                        "FDA\tFood and Drug Administration",
                        "LFT\t",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            report = import_legacy_source(
                database_path=database_path,
                source_path=source_path,
            )

            self.assertFalse(report["already_imported"])
            self.assertEqual(report["candidate_count"], 5)

            self.assertEqual(
                report["issue_counts"]["duplicate_exact"],
                1,
            )

            self.assertEqual(
                report["issue_counts"]["definition_conflict"],
                1,
            )

            self.assertEqual(
                report["issue_counts"]["missing_definition"],
                1,
            )

            with open_database(database_path) as connection:
                statuses = connection.execute(
                    """
                    SELECT DISTINCT status
                    FROM candidate_terms
                    """
                ).fetchall()

            self.assertEqual(
                statuses,
                [("legacy_candidate",)],
            )

    def test_import_is_idempotent_for_identical_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            source_path = root / "legacy.tsv"
            database_path = root / "abbreviations.sqlite"

            source_path.write_text(
                "AE\tAdverse Event\n",
                encoding="utf-8",
            )

            first_report = import_legacy_source(
                database_path=database_path,
                source_path=source_path,
            )

            second_report = import_legacy_source(
                database_path=database_path,
                source_path=source_path,
            )

            self.assertFalse(first_report["already_imported"])
            self.assertTrue(second_report["already_imported"])

            with open_database(database_path) as connection:
                candidate_count = connection.execute(
                    """
                    SELECT COUNT(*)
                    FROM candidate_terms
                    """
                ).fetchone()[0]

            self.assertEqual(candidate_count, 1)

    def test_parser_accepts_two_space_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            source_path = root / "legacy.txt"
            database_path = root / "abbreviations.sqlite"

            source_path.write_text(
                "AE  Adverse Event\n",
                encoding="utf-8",
            )

            report = import_legacy_source(
                database_path=database_path,
                source_path=source_path,
            )

            self.assertEqual(report["candidate_count"], 1)
            self.assertEqual(report["issue_counts"], {})


if __name__ == "__main__":
    unittest.main()
