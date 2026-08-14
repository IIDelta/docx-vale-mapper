from __future__ import annotations

import unittest

from runtime.commentlifecycle import (
    COMMENT_MODE_APPEND,
    COMMENT_MODE_REPLACE,
    TOOL_COMMENT_AUTHOR,
    TOOL_COMMENT_INITIALS,
    is_tool_comment_metadata,
    normalize_comment_mode,
)


class CommentLifecycleTests(unittest.TestCase):
    """Tests for tool-comment lifecycle behavior."""

    def test_default_mode_is_replace(self) -> None:
        self.assertEqual(
            normalize_comment_mode(""),
            COMMENT_MODE_REPLACE,
        )

    def test_append_mode_is_supported(self) -> None:
        self.assertEqual(
            normalize_comment_mode(
                "Append Comments"
            ),
            COMMENT_MODE_APPEND,
        )

    def test_tool_comment_is_recognized(self) -> None:
        self.assertTrue(
            is_tool_comment_metadata(
                TOOL_COMMENT_AUTHOR,
                TOOL_COMMENT_INITIALS,
            )
        )

    def test_human_comment_is_not_recognized(self) -> None:
        self.assertFalse(
            is_tool_comment_metadata(
                "Jaustin",
                "JD",
            )
        )

    def test_partial_metadata_is_not_recognized(self) -> None:
        self.assertFalse(
            is_tool_comment_metadata(
                TOOL_COMMENT_AUTHOR,
                "JD",
            )
        )
