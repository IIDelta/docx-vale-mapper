from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from abbreviations.legacyimport import (
    initialize_database,
    open_database,
)
from abbreviations.reviewactions import (
    apply_local_decision,
)
from abbreviations.reviewpromote import ensure_review_schema


class ReviewActionTests(unittest.TestCase):
    """Tests for direct local registry decisions."""

    def create_database(self) -> Path:
        """Create a temporary reviewed registry database."""

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

    def test_approved_expand_decision_updates_registry(
        self,
    ) -> None:
        database_path = self.create_database()

        resolution, report = apply_local_decision(
            database_path=database_path,
            token="AUC0-24",
            status="approved_expand",
            definition=(
                "Area under the plasma concentration-time "
                "curve over 24 hours"
            ),
            notes="Approved test entry.",
            reviewer="test_user",
        )

        self.assertTrue(resolution.found)

        self.assertEqual(
            resolution.status,
            "approved_expand",
        )

        self.assertEqual(
            resolution.preferred_definition,
            (
                "Area under the plasma concentration-time "
                "curve over 24 hours"
            ),
        )

        self.assertEqual(
            resolution.source_reference,
            "gui_review:test_user",
        )

        self.assertEqual(
            report["decision_origin"],
            "gui_review",
        )

        self.assertEqual(
            report["review_rows_applied"],
            1,
        )

    def test_ignored_decision_updates_registry(self) -> None:
        database_path = self.create_database()

        resolution, _ = apply_local_decision(
            database_path=database_path,
            token="XYZ",
            status="ignored",
            notes="Fixture-only placeholder.",
            reviewer="test_user",
        )

        self.assertTrue(resolution.found)

        self.assertEqual(
            resolution.status,
            "ignored",
        )

        self.assertEqual(
            resolution.enforcement_action,
            "ignore",
        )

    def test_approved_expand_requires_definition(self) -> None:
        database_path = self.create_database()

        with self.assertRaises(ValueError) as error:
            apply_local_decision(
                database_path=database_path,
                token="XYZ",
                status="approved_expand",
                definition="",
                reviewer="test_user",
            )

        self.assertIn(
            "has no preferred_definition",
            str(error.exception),
        )

    def test_deprecated_requires_replacement(self) -> None:
        database_path = self.create_database()

        with self.assertRaises(ValueError) as error:
            apply_local_decision(
                database_path=database_path,
                token="OLD",
                status="deprecated",
                definition="Old term",
                replacement_token="",
                reviewer="test_user",
            )

        self.assertIn(
            "has no replacement_token",
            str(error.exception),
        )


if __name__ == "__main__":
    unittest.main()
