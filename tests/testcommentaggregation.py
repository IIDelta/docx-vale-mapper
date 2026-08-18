import unittest
from runtime.commentpolicy import build_comment_plan

class CommentAggregationTests(unittest.TestCase):
    def test_aggregate_comments(self):
        policy = {
            "auto_fix_rules": [],
            "comment_rules": ["R1"],
            "report_only_rules": [],
            "disabled_rules": [],
            "aggregation_threshold": 5,
            "max_comments_per_rule": 5,
            "max_total_comments": 50
        }
        
        # Below threshold
        findings = [{"Check": "R1", "Context": {"content_zone": "body_narrative"}} for _ in range(3)]
        plan = build_comment_plan(findings, policy)
        self.assertEqual(len(plan["comment_plan"]), 3)

        # Above threshold
        findings = [{"Check": "R1", "Context": {"content_zone": "body_narrative"}} for _ in range(5)]
        plan = build_comment_plan(findings, policy)
        self.assertEqual(len(plan["comment_plan"]), 1)
        self.assertTrue(plan["comment_plan"][0].get("aggregated"))
