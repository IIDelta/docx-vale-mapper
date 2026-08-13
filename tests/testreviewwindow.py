from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from abbreviations.reviewwindow import (
    filter_candidates,
    format_generation_blockers,
    load_candidates,
    update_candidate_payload,
)


class ReviewWindowTests(unittest.TestCase):
    """Tests for B4.1 read-only review-window helpers."""

    def test_candidate_resolution_update_refreshes_bucket(
        self,
    ) -> None:
        payload = {
            "candidate_count": 1,
            "candidates": [
                {
                    "token": "XYZ",
                    "count": 2,
                    "inline_definition_count": 0,
                    "review_bucket": "likely_unknown",
                    "confidence": "likely",
                    "resolution": {
                        "found": False,
                        "status": "unknown",
                    },
                }
            ],
        }

        resolution = {
            "found": True,
            "token": "XYZ",
            "status": "ignored",
            "preferred_definition": "",
            "replacement_token": "",
            "source_reference": "gui_review:test_user",
            "notes": "Fixture-only placeholder.",
            "enforcement_action": "ignore",
        }

        updated = update_candidate_payload(
            payload=payload,
            token="XYZ",
            resolution=resolution,
        )

        self.assertTrue(updated)

        candidate = payload["candidates"][0]

        self.assertEqual(
            candidate["review_bucket"],
            "ignored",
        )

        self.assertEqual(
            candidate["confidence"],
            "high",
        )

        self.assertEqual(
            candidate["resolution"]["status"],
            "ignored",
        )


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

    def test_generation_blocker_formatting(self) -> None:
        class Blocker:
            def __init__(
                self,
                token: str,
                message: str,
            ) -> None:
                self.token = token
                self.message = message

        blocker_text = format_generation_blockers(
            [
                Blocker(
                    "EOS",
                    "Use EOT before generating the list.",
                ),
                Blocker(
                    "FAS",
                    "Choose an approved definition first.",
                ),
            ]
        )

        self.assertIn(
            "• EOS: Use EOT before generating the list.",
            blocker_text,
        )

        self.assertIn(
            "• FAS: Choose an approved definition first.",
            blocker_text,
        )



if __name__ == "__main__":
    unittest.main()
