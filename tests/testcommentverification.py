from __future__ import annotations

import unittest

from validators.commentverification import (
    normalize_comment_text,
    vale_anchor_is_verified,
)


class CommentVerificationTests(unittest.TestCase):
    """Tests for production-safe comment verification."""

    def test_exact_match_is_verified(self) -> None:
        self.assertTrue(
            vale_anchor_is_verified(
                "healthcare",
                "healthcare",
            )
        )

    def test_nonbreaking_space_is_normalized(self) -> None:
        self.assertTrue(
            vale_anchor_is_verified(
                "≥\xa020",
                "≥ 20",
            )
        )

    def test_wrong_anchor_is_rejected(self) -> None:
        self.assertFalse(
            vale_anchor_is_verified(
                "r populati",
                "healthcare",
            )
        )

    def test_blank_anchor_is_rejected(self) -> None:
        self.assertFalse(
            vale_anchor_is_verified(
                "",
                "and/or",
            )
        )

    def test_word_markers_are_removed(self) -> None:
        self.assertEqual(
            normalize_comment_text(
                "healthcare\r\x07"
            ),
            "healthcare",
        )
