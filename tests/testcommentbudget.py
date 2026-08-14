from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.commentbudget import (
    apply_comment_budget,
    load_comment_budget,
    write_comment_queue,
)


class CommentBudgetTests(unittest.TestCase):
    def test_errors_are_prioritized_and_rule_caps_apply(self) -> None:
        findings = [
            {"Check": "Clinical.A", "Severity": "warning"},
            {"Check": "Clinical.A", "Severity": "warning"},
            {"Check": "Clinical.B", "Severity": "error"},
            {"Check": "Clinical.C", "Severity": "suggestion"},
        ]
        budget = {
            "max_comments": 2,
            "max_comments_per_rule": 1,
            "severity_order": ["error", "warning", "suggestion"],
            "write_full_review_queue": True,
        }
        selected, deferred = apply_comment_budget(findings, budget)
        self.assertEqual([item["Check"] for item in selected], ["Clinical.B", "Clinical.A"])
        self.assertEqual(len(deferred), 2)
        self.assertEqual(deferred[0]["DeferredReason"], "comment_budget_rule")
        self.assertEqual(deferred[1]["DeferredReason"], "comment_budget_total")

    def test_queue_preserves_selected_and_deferred_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "audited.docx"
            queue_path = write_comment_queue(
                output_path=output_path,
                all_findings=[{"Check": "Clinical.A"}],
                selected_findings=[],
                deferred_findings=[
                    {"Check": "Clinical.A", "DeferredReason": "comment_budget_total"}
                ],
                budget=load_comment_budget(Path(temporary_directory) / "missing.json"),
            )
            payload = json.loads(queue_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["candidate_finding_count"], 1)
        self.assertEqual(payload["deferred_comment_count"], 1)
        self.assertEqual(payload["deferred_reason_counts"], {"comment_budget_total": 1})


if __name__ == "__main__":
    unittest.main()
