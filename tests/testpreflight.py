from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.preflight import (
    check_file,
    check_output_directory,
    format_preflight_failure,
)


class PreflightTests(unittest.TestCase):
    """Tests for runtime preflight helpers."""

    def test_existing_file_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            file_path = (
                Path(temporary_directory)
                / "config.ini"
            )

            file_path.write_text(
                "test",
                encoding="utf-8",
            )

            result = check_file(
                "Test file",
                file_path,
            )

        self.assertTrue(result.passed)

    def test_missing_file_fails(self) -> None:
        result = check_file(
            "Missing file",
            Path("does_not_exist.ini"),
        )

        self.assertFalse(result.passed)

    def test_output_directory_is_created_and_writable(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = (
                Path(temporary_directory)
                / "new_folder"
                / "output.docx"
            )

            result = check_output_directory(
                output_path
            )

        self.assertTrue(result.passed)

    def test_failure_message_contains_failed_check(
        self,
    ) -> None:
        message = format_preflight_failure(
            {
                "checks": [
                    {
                        "name": "Vale CLI",
                        "passed": False,
                        "details": "Vale missing",
                    }
                ]
            }
        )

        self.assertIn(
            "Vale CLI",
            message,
        )

        self.assertIn(
            "Vale missing",
            message,
        )
