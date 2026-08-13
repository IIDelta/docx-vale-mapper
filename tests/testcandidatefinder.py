from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from abbreviations.candidatefinder import (
    TextRecord,
    discover_candidates,
)
from abbreviations.legacyimport import (
    initialize_database,
    open_database,
)
from abbreviations.reviewpromote import (
    ensure_review_schema,
    upsert_registry_entry,
)


class CandidateFinderTests(unittest.TestCase):
    """Tests for B3.2 candidate discovery and classification."""

    def create_database(self) -> Path:
        """Create a temporary reviewed registry."""

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
                notes="Approved.",
            )

            upsert_registry_entry(
                connection=connection,
                token="FDA",
                definition="",
                status="approved_no_expand",
                source_reference="test_source",
                replacement_token="",
                notes="Protected.",
            )

            upsert_registry_entry(
                connection=connection,
                token="EOS",
                definition="End of Study",
                status="deprecated",
                source_reference="test_source",
                replacement_token="EOT",
                notes="Deprecated.",
            )

            upsert_registry_entry(
                connection=connection,
                token="FAS",
                definition="",
                status="ambiguous",
                source_reference="test_source",
                replacement_token="",
                notes="Ambiguous.",
            )

            upsert_registry_entry(
                connection=connection,
                token="CIOMS",
                definition=(
                    "Council for International Organizations "
                    "of Medical Sciences"
                ),
                status="reviewed_candidate",
                source_reference="test_source",
                replacement_token="",
                notes="Review candidate.",
            )

        return database_path

    def summaries_by_token(
        self,
        summaries,
    ) -> dict:
        """Create an easy candidate lookup for assertions."""

        return {
            summary.token: summary
            for summary in summaries
        }

    def test_known_terms_are_classified(self) -> None:
        database_path = self.create_database()

        records = [
            TextRecord(
                index=1,
                text=(
                    "The CFR applies and the FDA reviewed the file."
                ),
            ),
            TextRecord(
                index=2,
                text=(
                    "EOS was used in the legacy document."
                ),
            ),
            TextRecord(
                index=3,
                text=(
                    "The FAS was reviewed by CIOMS."
                ),
            ),
        ]

        summaries = discover_candidates(
            database_path=database_path,
            records=records,
        )

        by_token = self.summaries_by_token(summaries)

        self.assertEqual(
            by_token["CFR"].review_bucket,
            "known_expand",
        )

        self.assertEqual(
            by_token["FDA"].review_bucket,
            "protected",
        )

        self.assertEqual(
            by_token["EOS"].review_bucket,
            "deprecated",
        )

        self.assertEqual(
            by_token["FAS"].review_bucket,
            "ambiguous",
        )

        self.assertEqual(
            by_token["CIOMS"].review_bucket,
            "reviewed_candidate",
        )

    def test_unknown_repeated_token_is_likely(self) -> None:
        database_path = self.create_database()

        records = [
            TextRecord(
                index=1,
                text="The XYZ result was reviewed.",
            ),
            TextRecord(
                index=2,
                text="The XYZ result was confirmed.",
            ),
        ]

        summaries = discover_candidates(
            database_path=database_path,
            records=records,
        )

        by_token = self.summaries_by_token(summaries)

        self.assertEqual(
            by_token["XYZ"].review_bucket,
            "likely_unknown",
        )

        self.assertEqual(
            by_token["XYZ"].count,
            2,
        )

    def test_unknown_single_token_is_possible(self) -> None:
        database_path = self.create_database()

        records = [
            TextRecord(
                index=1,
                text=(
                    "AUC0-24 was calculated after dosing."
                ),
            ),
        ]

        summaries = discover_candidates(
            database_path=database_path,
            records=records,
        )

        by_token = self.summaries_by_token(summaries)

        self.assertEqual(
            by_token["AUC0-24"].review_bucket,
            "possible_unknown",
        )

        self.assertEqual(
            by_token["AUC0-24"].confidence,
            "possible",
        )

    def test_ordinary_title_case_words_are_not_candidates(self) -> None:
        database_path = self.create_database()

        records = [
            TextRecord(
                index=1,
                text=(
                    "The participant completed the assessment."
                ),
            ),
        ]

        summaries = discover_candidates(
            database_path=database_path,
            records=records,
        )

        tokens = {
            summary.token
            for summary in summaries
        }

        self.assertNotIn("The", tokens)
        self.assertNotIn("participant", tokens)
        self.assertNotIn("assessment", tokens)


if __name__ == "__main__":
    unittest.main()
