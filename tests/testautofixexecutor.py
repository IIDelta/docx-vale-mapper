from __future__ import annotations
import unittest
from runtime.autofixexecutor import replacement_operations
class AutoFixExecutorTests(unittest.TestCase):
 def test_nbsp_replacement_changes_one_character(self): self.assertEqual(replacement_operations("5 mg","5\u00a0mg"),[("replace",1,2,"\u00a0")])
 def test_math_spacing_deletes_one_character(self): self.assertEqual(replacement_operations("< 4","<4"),[("delete",1,2,"")])
if __name__=="__main__": unittest.main()
