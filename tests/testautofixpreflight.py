from __future__ import annotations
import unittest
from runtime.autofixpreflight import resolve_preflight_offset

class AutoFixPreflightTests(unittest.TestCase):
    def test_repeated_match_uses_occurrence_index(self):
        self.assertEqual(resolve_preflight_offset("5 mg and 5 mg", {"match": "5 mg", "occurrence_index": 0}),0)
        self.assertEqual(resolve_preflight_offset("5 mg and 5 mg", {"match": "5 mg", "occurrence_index": 1}),9)
        self.assertIsNone(resolve_preflight_offset("5 mg", {"match": "5 mg", "occurrence_index": 1}))
        
    def test_uses_span_when_available(self):
        # "5 mg" length is 4. So span [1, 4] for 1-based inclusive.
        self.assertEqual(resolve_preflight_offset("5 mg and 5 mg", {"match": "5 mg", "span": [10, 13]}), 9)

if __name__=="__main__": unittest.main()
