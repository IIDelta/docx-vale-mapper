from __future__ import annotations

import unittest

from runtime.commentpolicy import build_comment_plan


def finding(rule: str, line: int, action=None) -> dict:
    return {
        "Check": rule,
        "Line": line,
        "Match": "example",
        "Action": action or {"Name": "", "Params": None},
        "Context": {"content_zone": "body_narrative", "has_protected_field": False},
    }


class CommentPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = {
            "profile_name": "Operational Audit",
            "aggregation_threshold": 5,
            "max_total_comments": 50,
            "max_comments_per_rule": 5,
            "auto_fix_rules": ["Clinical.UnitNonbreakingSpace"],
            "comment_rules": ["Clinical.EndOfTrial"],
            "report_only_rules": ["Clinical.ForwardSlashReview"],
            "disabled_rules": ["Clinical.FigureVisualReview"],
        }

    def test_four_occurrences_create_four_comments(self) -> None:
        plan = build_comment_plan([finding("Clinical.EndOfTrial", line) for line in range(1, 5)], self.policy)
        self.assertEqual(plan["comment_count"], 4)
        self.assertFalse(plan["comment_plan"][0]["aggregated"])

    def test_five_occurrences_create_one_aggregated_comment(self) -> None:
        plan = build_comment_plan([finding("Clinical.EndOfTrial", line) for line in range(1, 6)], self.policy)
        self.assertEqual(plan["comment_count"], 1)
        self.assertTrue(plan["comment_plan"][0]["aggregated"])
        self.assertEqual(plan["comment_plan"][0]["occurrence_count"], 5)

    def test_safe_replace_action_creates_auto_fix_plan(self) -> None:
        plan = build_comment_plan([finding("Clinical.UnitNonbreakingSpace", 1, {"Name": "replace", "Params": ["5\u00a0mg"]})], self.policy)
        self.assertEqual(plan["auto_fix_count"], 1)
        self.assertEqual(plan["comment_count"], 0)

    def test_disabled_rule_creates_no_comment(self) -> None:
        plan = build_comment_plan([finding("Clinical.FigureVisualReview", 1)], self.policy)
        self.assertEqual(plan["disabled_count"], 1)
        self.assertEqual(plan["comment_count"], 0)
