import sys
from unittest.mock import MagicMock
sys.modules['pythoncom'] = MagicMock()
sys.modules['win32com'] = MagicMock()
sys.modules['win32com.client'] = MagicMock()

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from runtime.execution import execute_operational_audit
import json

class TestExecution(unittest.TestCase):
    def setUp(self):
        self.source_path = Path("test_source.docx")
        self.output_path = Path("test_output.docx")
        self.manifest_path = Path("test_manifest.json")
        self.autofix_preflight_path = Path("test_autofix.json")
        self.comment_preflight_path = Path("test_comment.json")
        self.output_base = Path("test_base")
        
        self.manifest_path.write_text('{"source_sha256": "dummy_sha"}')
        
        verified_autofixes = [
            {
                "rule_id": "Takeda.Spelling",
                "match": "MATCH",
                "replacement": "FIX",
                "paragraph_index": 1,
                "verified_range_start": 30,
                "verified_range_end": 35,
                "finding": {"Severity": "error", "Match": "MATCH", "Message": "Msg"}
            }
        ]
        
        verified_comments = [
            {
                "rule_id": "Takeda.Terminology",
                "match": "TEST",
                "aggregated": False,
                "paragraph_index": 1,
                "verified_range_start": 10,
                "verified_range_end": 14,
                "finding": {"Severity": "warning", "Match": "TEST", "Message": "Msg"}
            }
        ]
        
        self.autofix_preflight_path.write_text(json.dumps({
            "source_sha256_matches": True,
            "unverified_count": 0,
            "verified_auto_fixes": verified_autofixes
        }))
        
        self.comment_preflight_path.write_text(json.dumps({
            "source_sha256_matches": True,
            "unverified_count": 0,
            "verified_comments": verified_comments
        }))
        
    def tearDown(self):
        for path in [self.manifest_path, self.autofix_preflight_path, self.comment_preflight_path]:
            if path.exists(): path.unlink()
        for ext in [".autofixexecution.json", ".commentexecution.json", ".outputverification.json"]:
            if self.output_base.with_suffix(ext).exists():
                self.output_base.with_suffix(ext).unlink()

    @patch("runtime.execution.calculate_sha256")
    @patch("shutil.copy2")
    def test_execute_operational_audit_mock_com(self, mock_copy2, mock_sha):
        mock_sha.return_value = "dummy_sha"
        
        mock_word = MagicMock()
        mock_doc = MagicMock()
        mock_word.Documents.Open.return_value = mock_doc
        
        mock_comments = MagicMock()
        mock_comments.Add.return_value = MagicMock()
        mock_doc.Comments = mock_comments
        
        mock_paragraph = MagicMock()
        mock_range = MagicMock()
        mock_range.Text = "This is a test paragraph with a MATCH."
        mock_paragraph.Range = mock_range
        mock_paragraphs = MagicMock()
        mock_paragraphs.Item.return_value = mock_paragraph
        mock_doc.Paragraphs = mock_paragraphs
        
        with patch("word.lifecycle.WordAppSession") as mock_session_class:
            mock_session_instance = MagicMock()
            mock_session_class.return_value = mock_session_instance
            mock_session_instance.__enter__.return_value = mock_word
            
            result = execute_operational_audit(
                source_path=self.source_path,
                output_path=self.output_path,
                manifest_path=self.manifest_path,
                autofix_preflight_path=self.autofix_preflight_path,
                comment_preflight_path=self.comment_preflight_path,
                output_base=self.output_base,
                word_app=mock_word
            )
            
            self.assertTrue(result["autofixexecution"].exists())
            self.assertTrue(result["commentexecution"].exists())

if __name__ == "__main__":
    unittest.main()
