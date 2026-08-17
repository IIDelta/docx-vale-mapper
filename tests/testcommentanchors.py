from __future__ import annotations

import unittest

from runtime.commentpolicy import build_comment_plan


class CommentAnchorTests(unittest.TestCase):
    def test_auto_fix_plan_preserves_anchor_metadata(self) -> None:
        finding = {
            "Check": "Clinical.UnitNonbreakingSpace",
            "Match": "5 mg",
            "Line": 10,
            "ParagraphIndex": 7,
            "RangeStart": 100,
            "RangeEnd": 104,
            "Span": [5, 8],
            "Action": {"Name": "replace", "Params": ["5\u00a0mg"]},
            "Context": {"content_zone": "body_narrative", "paragraph_text": "Dose was 5 mg.", "has_protected_field": False},
        }
        policy = {
            "profile_name": "Operational Audit", "aggregation_threshold": 5,
            "max_total_comments": 50, "max_comments_per_rule": 5,
            "auto_fix_rules": ["Clinical.UnitNonbreakingSpace"],
            "comment_rules": [], "report_only_rules": [], "disabled_rules": [],
        }
        plan = build_comment_plan([finding], policy)
        item = plan["auto_fix_plan"][0]
        self.assertEqual(item["range_start"], 100)
        self.assertEqual(item["range_end"], 104)
        self.assertEqual(item["span"], [5, 8])
        self.assertEqual(item["occurrence_index"], 0)
        self.assertEqual(item["paragraph_text"], "Dose was 5 mg.")


if __name__ == "__main__":
    unittest.main()
