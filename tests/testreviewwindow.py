from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from abbreviations.reviewwindow import (
    filter_candidates,
    load_candidates,
)


class ReviewWindowTests(unittest.TestCase):
    """Tests for B4.1 read-only review-window helpers."""

    def create_candidates(self) -> list[dict]:
        """Create representative candidate records."""

        return [
            {
                "token": "FDA",
                "review_bucket": "protected",
                "count": 1,
                "resolution": {
                    "status": "approved_no_expand",
                    "preferred_definition": "",
                    "replacement_token": "",
                    "notes": "Protected term.",
                },
            },
            {
                "token": "XYZ",
                "review_bucket": "likely_unknown",
                "count": 2,
                "resolution": {
                    "status": "unknown",
                    "preferred_definition": "",
                    "replacement_token": "",
                    "notes": "Unknown candidate.",
                },
            },
            {
                "token": "EOS",
                "review_bucket": "deprecated",
                "count": 1,
                "resolution": {
                    "status": "deprecated",
                    "preferred_definition": "End of Study",
                    "replacement_token": "EOT",
                    "notes": "Deprecated term.",
                },
            },
            {
                "token": "FAS",
                "review_bucket": "ambiguous",
                "count": 1,
                "resolution": {
                    "status": "ambiguous",
                    "preferred_definition": "",
                    "replacement_token": "",
                    "notes": "Multiple definitions.",
                },
            },
        ]

    def test_bucket_filter_returns_selected_bucket(self) -> None:
        candidates = self.create_candidates()

        filtered = filter_candidates(
            candidates=candidates,
            selected_bucket="deprecated",
            search_text="",
        )

        self.assertEqual(
            [candidate["token"] for candidate in filtered],
            ["EOS"],
        )

    def test_search_filter_uses_token_and_definition(self) -> None:
        candidates = self.create_candidates()

        filtered = filter_candidates(
            candidates=candidates,
            selected_bucket="All",
            search_text="study",
        )

        self.assertEqual(
            [candidate["token"] for candidate in filtered],
            ["EOS"],
        )

    def test_all_filter_uses_priority_order(self) -> None:
        candidates = self.create_candidates()

        filtered = filter_candidates(
            candidates=candidates,
            selected_bucket="All",
            search_text="",
        )

        self.assertEqual(
            [candidate["token"] for candidate in filtered],
            [
                "EOS",
                "FAS",
                "XYZ",
                "FDA",
            ],
        )

    def test_candidate_json_loads(self) -> None:
        payload = {
            "candidate_count": 1,
            "candidates": self.create_candidates()[:1],
        }

        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = (
                Path(temporary_directory)
                / "candidate.json"
            )

            report_path.write_text(
                json.dumps(payload),
                encoding="utf-8",
            )

            candidates = load_candidates(report_path)

        self.assertEqual(
            candidates[0]["token"],
            "FDA",
        )


if __name__ == "__main__":
    unittest.main()
