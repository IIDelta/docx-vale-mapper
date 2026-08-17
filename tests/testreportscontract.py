from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.reportscontract import validate_reports_only_artifacts


class ReportsOnlyContractTests(unittest.TestCase):
    def test_valid_reports_only_artifacts_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.docx"
            base = root / "audit.docx"
            source.write_bytes(b"source")
            (root / "audit.audit_findings.json").write_text(
                json.dumps(
                    {
                        "audit_mode": "reports_only",
                        "finding_count": 1,
                        "findings": [{"Check": "Clinical.Example"}],
                    }
                ),
                encoding="utf-8",
            )
            (root / "audit.audit_summary.json").write_text(
                json.dumps(
                    {
                        "final_finding_count": 1,
                        "inserted_comment_count": 0,
                        "skipped_comment_reasons": {
                            "comment_insertion_disabled": 1
                        },
                    }
                ),
                encoding="utf-8",
            )
            (root / "audit.audit_manifest.json").write_text(
                json.dumps(
                    {
                        "audit_mode": "reports_only",
                        "output_document_created": False,
                    }
                ),
                encoding="utf-8",
            )
            failures = validate_reports_only_artifacts(source, base)
        self.assertEqual(failures, [])

    def test_created_docx_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.docx"
            base = root / "audit.docx"
            source.write_bytes(b"source")
            base.write_bytes(b"unexpected")
            failures = validate_reports_only_artifacts(source, base)
        self.assertTrue(any("created an audited DOCX" in item for item in failures))


if __name__ == "__main__":
    unittest.main()
