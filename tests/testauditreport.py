from __future__ import annotations

import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from runtime.auditreport import write_audit_findings_report


class AuditReportTests(unittest.TestCase):
    def test_report_writes_all_findings_and_rule_counts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            report_path = write_audit_findings_report(
                output_path=root / "audit.docx",
                source_path=root / "source.docx",
                audit_profile="Operational Audit",
                audit_mode="reports_only",
                findings=[
                    {
                        "Check": "Clinical.Example",
                        "Severity": "warning",
                        "Message": "Example message",
                        "Match": "example",
                        "Line": 1,
                    }
                ],
                suppressed_findings=Counter({"Clinical.Other:heading": 2}),
            )
            payload = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["audit_mode"], "reports_only")
        self.assertEqual(payload["finding_count"], 1)
        self.assertEqual(payload["rule_counts"], {"Clinical.Example": 1})
        self.assertEqual(payload["findings"][0]["Match"], "example")
