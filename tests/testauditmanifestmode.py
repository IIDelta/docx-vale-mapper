from __future__ import annotations

import tempfile
import unittest
from collections import Counter
from pathlib import Path

from runtime.auditmanifest import build_audit_manifest


class AuditManifestModeTests(unittest.TestCase):
    def test_reports_only_manifest_records_no_output_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / "source.docx"
            source_path.write_bytes(b"source")
            manifest = build_audit_manifest(
                source_path=source_path,
                output_path=root / "reportbase.docx",
                audit_profile="Operational Audit",
                audit_mode="reports_only",
                output_document_created=False,
                vale_version="vale test",
                final_findings=[],
                suppressed_findings=Counter(),
                comment_metrics={
                    "candidate_comment_count": 0,
                    "inserted_comment_count": 0,
                    "skipped_comment_reasons": Counter(),
                },
                content_zone_counts={},
                preflight_result={"passed": True, "checks": []},
            )

        self.assertEqual(manifest["audit_mode"], "reports_only")
        self.assertFalse(manifest["output_document_created"])


if __name__ == "__main__":
    unittest.main()
