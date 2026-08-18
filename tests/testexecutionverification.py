import unittest
from pathlib import Path
import json
import tempfile
from runtime.executionverification import verify_execution_artifacts

class ExecutionVerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.af_path = Path(self.temp_dir.name) / "af.json"
        self.com_path = Path(self.temp_dir.name) / "com.json"
        
        self.af_path.write_text(json.dumps({
            "source_sha256": "abc",
            "output_sha256": "def",
            "applied_count": 5
        }), encoding="utf-8")
        
        self.com_path.write_text(json.dumps({
            "source_sha256": "abc",
            "output_sha256": "def",
            "inserted_count": 3,
            "aggregated_count": 1,
            "inserted": []
        }), encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_verify_success(self):
        result = verify_execution_artifacts(
            self.af_path, self.com_path,
            expected_source_sha="abc",
            expected_output_sha="def",
            expected_autofix_count=5,
            expected_individual_comment_count=3,
            expected_aggregated_comment_count=1
        )
        self.assertTrue(result["passed"])
        self.assertEqual(len(result["errors"]), 0)

    def test_verify_failure_counts(self):
        result = verify_execution_artifacts(
            self.af_path, self.com_path,
            expected_source_sha="abc",
            expected_output_sha="def",
            expected_autofix_count=10,
            expected_individual_comment_count=3,
            expected_aggregated_comment_count=1
        )
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["errors"]), 1)
        self.assertIn("Expected 10 auto-fixes", result["errors"][0])
