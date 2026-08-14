from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.auditmanifest import (
    build_audit_manifest,
    sha256_file,
    write_audit_manifest,
)


class AuditManifestTests(unittest.TestCase):
    """Tests for audit manifest generation."""

    def test_sha256_file_is_repeatable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_path = (
                Path(temporary_directory)
                / "source.docx"
            )

            source_path.write_bytes(
                b"fixture content"
            )

            first_hash = sha256_file(source_path)
            second_hash = sha256_file(source_path)

        self.assertEqual(
            first_hash,
            second_hash,
        )

    def test_manifest_writes_expected_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            source_path = root / "source.docx"
            output_path = root / "output.docx"

            source_path.write_bytes(
                b"source fixture"
            )

            output_path.write_bytes(
                b"output fixture"
            )

            manifest = build_audit_manifest(
                source_path=source_path,
                output_path=output_path,
                audit_profile="standard",
                vale_version="Vale 3.x",
                final_findings=[
                    {
                        "Check": "Clinical.Example"
                    }
                ],
                suppressed_findings={},
                comment_metrics={
                    "candidate_comment_count": 1,
                    "inserted_comment_count": 1,
                    "skipped_comment_reasons": {},
                },
                content_zone_counts={
                    "body_narrative": 1
                },
                preflight_result={
                    "passed": True,
                    "checks": [],
                },
            )

            manifest_path = write_audit_manifest(
                manifest,
                output_path,
            )

            loaded_manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(
            loaded_manifest["audit_profile"],
            "standard",
        )

        self.assertEqual(
            loaded_manifest[
                "inserted_comment_count"
            ],
            1,
        )

        self.assertIn(
            "source_sha256",
            loaded_manifest,
        )
