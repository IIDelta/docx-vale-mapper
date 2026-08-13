from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from abbreviations.auditbridge import build_effective_policy
from abbreviations.legacyimport import (
    initialize_database,
    open_database,
)
from abbreviations.reviewpromote import (
    ensure_review_schema,
    upsert_registry_entry,
)
from validators.abbreviationvalidator import (
    ParagraphRecord,
    validate_deprecated_terms,
    validate_first_use,
)


def record(index: int, text: str) -> ParagraphRecord:
    """Create a short paragraph fixture."""

    return ParagraphRecord(
        index=index,
        line=index,
        text=text,
    )


class AuditBridgeTests(unittest.TestCase):
    """Tests for registry-aware structural audit policy."""

    def create_policy_file(
        self,
        root: Path,
    ) -> Path:
        """Create a minimal static policy fixture."""

        policy_path = root / "policy.json"

        policy_path.write_text(
            json.dumps(
                {
                    "never_expand": [
                        "FDA"
                    ],
                    "tracked_abbreviations": {
                        "AE": {
                            "expansion": "adverse event"
                        }
                    }
                }
            ),
            encoding="utf-8",
        )

        return policy_path

    def create_database(
        self,
        root: Path,
    ) -> Path:
        """Create a temporary reviewed registry database."""

        database_path = root / "abbreviations.sqlite"

        initialize_database(database_path)

        with open_database(database_path) as connection:
            ensure_review_schema(connection)

            upsert_registry_entry(
                connection=connection,
                token="AUC0-24",
                definition=(
                    "Area under the plasma concentration-time "
                    "curve over 24 hours"
                ),
                status="approved_expand",
                source_reference="test_source",
                replacement_token="",
                notes="Approved term.",
            )

            upsert_registry_entry(
                connection=connection,
                token="EOS",
                definition="End of Study",
                status="deprecated",
                source_reference="test_source",
                replacement_token="EOT",
                notes="Deprecated term.",
            )

            upsert_registry_entry(
                connection=connection,
                token="XYZ",
                definition="",
                status="ignored",
                source_reference="test_source",
                replacement_token="",
                notes="Ignored test token.",
            )

        return database_path

    def test_registry_terms_extend_static_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            policy_path = self.create_policy_file(root)
            database_path = self.create_database(root)

            policy = build_effective_policy(
                base_policy_path=policy_path,
                database_path=database_path,
            )

        self.assertIn(
            "AE",
            policy["tracked_abbreviations"],
        )

        self.assertIn(
            "AUC0-24",
            policy["tracked_abbreviations"],
        )

        self.assertIn(
            "FDA",
            policy["never_expand"],
        )

        self.assertEqual(
            policy["deprecated_terms"]["EOS"],
            "EOT",
        )

        self.assertNotIn(
            "XYZ",
            policy["tracked_abbreviations"],
        )

    def test_registry_approved_term_requires_definition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            policy_path = self.create_policy_file(root)
            database_path = self.create_database(root)

            policy = build_effective_policy(
                base_policy_path=policy_path,
                database_path=database_path,
            )

            findings = validate_first_use(
                paragraphs=[
                    record(
                        1,
                        "AUC0-24 was calculated after dosing.",
                    )
                ],
                policy=policy,
                has_abbreviation_list=False,
                abbreviation_entries=[],
                list_heading=None,
            )

        checks = [
            finding["Check"]
            for finding in findings
        ]

        self.assertIn(
            "Clinical.AbbreviationUndefinedAtFirstUse",
            checks,
        )

    def test_protected_and_ignored_terms_do_not_trigger_first_use(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            policy_path = self.create_policy_file(root)
            database_path = self.create_database(root)

            policy = build_effective_policy(
                base_policy_path=policy_path,
                database_path=database_path,
            )

            findings = validate_first_use(
                paragraphs=[
                    record(
                        1,
                        "The FDA reviewed the XYZ result.",
                    )
                ],
                policy=policy,
                has_abbreviation_list=False,
                abbreviation_entries=[],
                list_heading=None,
            )

        self.assertEqual(findings, [])

    def test_deprecated_registry_term_is_flagged(self) -> None:
        findings = validate_deprecated_terms(
            paragraphs=[
                record(
                    1,
                    "EOS occurred after Week 12.",
                )
            ],
            deprecated_terms={
                "EOS": "EOT"
            },
        )

        self.assertEqual(len(findings), 1)

        self.assertEqual(
            findings[0]["Check"],
            "Clinical.AbbreviationDeprecated",
        )

        self.assertEqual(
            findings[0]["Match"],
            "EOS",
        )


if __name__ == "__main__":
    unittest.main()
