from __future__ import annotations

import unittest

from runtime.commentpreflight import resolve_comment_offset


class CommentPreflightTests(unittest.TestCase):
    def test_span_resolves_match(self) -> None:
        self.assertEqual(
            resolve_comment_offset(
                "End of Study (EOS)",
                "End of Study",
                [0, 11],
            ),
            0,
        )

    def test_fallback_finds_match(self) -> None:
        self.assertEqual(
            resolve_comment_offset(
                "Use End of Study.",
                "End of Study",
                None,
            ),
            4,
        )

    def test_missing_match_returns_none(self) -> None:
        self.assertIsNone(
            resolve_comment_offset(
                "End of Trial",
                "End of Study",
                None,
            )
        )


if __name__ == "__main__":
    unittest.main()
