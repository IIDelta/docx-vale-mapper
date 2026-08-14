from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from abbreviations.auditbridge import build_effective_policy
from abbreviations.legacyimport import open_database
from abbreviations.reviewpromote import (
    ensure_review_schema,
    upsert_registry_entry,
)


class AuditBridgePolicyTests(unittest.TestCase):
    def write_policy(self, directory: Path) -> Path:
        policy_path = directory / "policy.json"
        policy_path.write_text(
            json.dumps(
                {
                    "never_expand": [],
                    "tracked_abbreviations": {},
                    "deprecated_terms": {
                        "patient": "participant",
                    },
                }
            ),
            encoding="utf-8",
        )
        return policy_path

    def test_static_deprecated_terms_survive_empty_registry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            policy = build_effective_policy(
                self.write_policy(directory),
                directory / "abbreviations.sqlite",
            )

        self.assertEqual(
            policy["deprecated_terms"],
            {"patient": "participant"},
        )

    def test_registry_deprecated_term_overrides_static_term(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            database_path = directory / "abbreviations.sqlite"
            with open_database(database_path) as connection:
                ensure_review_schema(connection)
                upsert_registry_entry(
                    connection=connection,
                    token="patient",
                    definition="",
                    status="deprecated",
                    source_reference="unit_test",
                    replacement_token="trial participant",
                    notes="",
                )

            policy = build_effective_policy(
                self.write_policy(directory),
                database_path,
            )

        self.assertEqual(
            policy["deprecated_terms"],
            {"patient": "trial participant"},
        )


if __name__ == "__main__":
    unittest.main()
