from __future__ import annotations

import unittest
from pathlib import Path

from abbreviations.listinserter import (
    document_has_list_heading,
    verify_active_document,
)


class ListInserterTests(unittest.TestCase):
    """Tests for B4.4 pure insertion safeguards."""

    def test_existing_list_heading_is_detected(self) -> None:
        self.assertTrue(
            document_has_list_heading(
                "Text before.\n"
                "LIST OF ABBREVIATIONS AND DEFINITION OF TERMS\n"
                "Text after."
            )
        )

    def test_missing_list_heading_is_not_detected(self) -> None:
        self.assertFalse(
            document_has_list_heading(
                "This document has no abbreviation list."
            )
        )

    def test_matching_document_paths_are_accepted(self) -> None:
        verify_active_document(
            active_document_path=(
                "C:/Documents/protocol_AUDITED.docx"
            ),
            expected_document_path=Path(
                "C:/Documents/protocol_AUDITED.docx"
            ),
        )

    def test_mismatched_document_paths_are_rejected(
        self,
    ) -> None:
        with self.assertRaises(ValueError) as error:
            verify_active_document(
                active_document_path=(
                    "C:/Documents/other.docx"
                ),
                expected_document_path=Path(
                    "C:/Documents/protocol_AUDITED.docx"
                ),
            )

        self.assertIn(
            "does not match",
            str(error.exception),
        )


if __name__ == "__main__":
    unittest.main()
