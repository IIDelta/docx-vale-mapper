from __future__ import annotations
import unittest
from runtime.autofixexecutor import select_summary_targets
class AutoFixSummaryTests(unittest.TestCase):
 def test_selects_lowest_range_per_rule(self):
  items=[{"rule_id":"A","verified_range_start":30},{"rule_id":"A","verified_range_start":10},{"rule_id":"B","verified_range_start":20}]
  selected=select_summary_targets(items)
  self.assertEqual(selected["A"]["verified_range_start"],10)
  self.assertEqual(selected["B"]["verified_range_start"],20)
if __name__=="__main__": unittest.main()
