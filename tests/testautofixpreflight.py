from __future__ import annotations
import unittest
from runtime.autofixpreflight import occurrence_offset
class AutoFixPreflightTests(unittest.TestCase):
    def test_repeated_match_uses_occurrence_index(self):
        self.assertEqual(occurrence_offset("5 mg and 5 mg", "5 mg", 0),0)
        self.assertEqual(occurrence_offset("5 mg and 5 mg", "5 mg", 1),9)
        self.assertIsNone(occurrence_offset("5 mg", "5 mg", 1))
if __name__=="__main__": unittest.main()
