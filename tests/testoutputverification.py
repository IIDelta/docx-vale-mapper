import unittest
from pathlib import Path
from runtime.outputverification import verify_output_document

class OutputVerificationTests(unittest.TestCase):
    def test_missing_file(self):
        result = verify_output_document(
            Path("nonexistent.docx"),
            Path("nonexistent.docx")
        )
        self.assertFalse(result["output_document_exists"])
        self.assertIn("Output document does not exist.", result["errors"])
