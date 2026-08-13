from __future__ import annotations

import unittest
from pathlib import Path

from abbreviations.reportpaths import (
    candidate_report_path_for_document,
)


class ReportPathTests(unittest.TestCase):
    """Tests for document-specific candidate report paths."""

    def test_candidate_report_uses_document_stem(self) -> None:
        document_path = Path(
            "C:/Documents/protocol_AUDITED.docx"
        )

        report_path = candidate_report_path_for_document(
            document_path
        )

        self.assertEqual(
            report_path,
            Path(
                "C:/Documents/"
                "protocol_AUDITED.abbreviationreview.json"
            ),
        )

    def test_candidate_report_replaces_existing_extension(
        self,
    ) -> None:
        document_path = Path(
            "C:/Documents/report.final.docx"
        )

        report_path = candidate_report_path_for_document(
            document_path
        )

        self.assertEqual(
            report_path.name,
            "report.final.abbreviationreview.json",
        )


if __name__ == "__main__":
    unittest.main()
