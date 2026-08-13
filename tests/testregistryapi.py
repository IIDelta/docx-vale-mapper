from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from abbreviations.legacyimport import (
    initialize_database,
    open_database,
)
from abbreviations.registryapi import (
    resolve_token,
    resolve_tokens,
)
from abbreviations.reviewpromote import (
    ensure_review_schema,
    upsert_registry_entry,
)


class RegistryApiTests(unittest.TestCase):
    """Tests for reviewed registry query behavior."""

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

            upsert_registry_entry(
                connection=connection,
                token="CFR",
                definition="Code of Federal Regulations",
                status="approved_expand",
                source_reference="test_source",
                replacement_token="",
                notes="Approved definition.",
            )

            upsert_registry_entry(
                connection=connection,
                token="FDA",
                definition="",
                status="approved_no_expand",
                source_reference="test_source",
                replacement_token="",
                notes="Protected term.",
            )

            upsert_registry_entry(
                connection=connection,
                token="EOS",
                definition="End of Study",
                status="deprecated",
                source_reference="test_source",
                replacement_token="EOT",
                notes="Use preferred replacement.",
            )

            upsert_registry_entry(
                connection=connection,
                token="FAS",
                definition="",
                status="ambiguous",
                source_reference="test_source",
                replacement_token="",
                notes="Multiple definitions require review.",
            )

        return database_path

    def test_approved_expand_resolution(self) -> None:
        database_path = self.create_database()

        result = resolve_token(
            database_path=database_path,
            token="CFR",
        )

        self.assertTrue(result.found)
        self.assertEqual(result.token, "CFR")
        self.assertEqual(
            result.preferred_definition,
            "Code of Federal Regulations",
        )
        self.assertEqual(result.status, "approved_expand")
        self.assertEqual(
            result.enforcement_action,
            "require_definition_or_list_entry",
        )

    def test_protected_term_resolution(self) -> None:
        database_path = self.create_database()

        result = resolve_token(
            database_path=database_path,
            token="FDA",
        )

        self.assertTrue(result.found)
        self.assertEqual(result.status, "approved_no_expand")
        self.assertEqual(
            result.enforcement_action,
            "do_not_require_expansion",
        )

    def test_deprecated_term_resolution(self) -> None:
        database_path = self.create_database()

        result = resolve_token(
            database_path=database_path,
            token="EOS",
        )

        self.assertTrue(result.found)
        self.assertEqual(result.status, "deprecated")
        self.assertEqual(result.replacement_token, "EOT")
        self.assertEqual(
            result.enforcement_action,
            "warn_and_suggest_replacement",
        )

    def test_ambiguous_term_resolution(self) -> None:
        database_path = self.create_database()

        result = resolve_token(
            database_path=database_path,
            token="FAS",
        )

        self.assertTrue(result.found)
        self.assertEqual(result.status, "ambiguous")
        self.assertEqual(
            result.enforcement_action,
            "manual_definition_review",
        )

    def test_unknown_term_resolution(self) -> None:
        database_path = self.create_database()

        result = resolve_token(
            database_path=database_path,
            token="XYZ",
        )

        self.assertFalse(result.found)
        self.assertEqual(result.status, "unknown")
        self.assertEqual(
            result.enforcement_action,
            "candidate_review",
        )

    def test_multiple_token_resolution_preserves_order(self) -> None:
        database_path = self.create_database()

        results = resolve_tokens(
            database_path=database_path,
            tokens=["FDA", "CFR", "XYZ"],
        )

        self.assertEqual(
            [result.requested_token for result in results],
            ["FDA", "CFR", "XYZ"],
        )

        self.assertEqual(
            [result.status for result in results],
            [
                "approved_no_expand",
                "approved_expand",
                "unknown",
            ],
        )


if __name__ == "__main__":
    unittest.main()
