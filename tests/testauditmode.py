from __future__ import annotations

import unittest

from runtime.auditmode import (
    REPORTS_ONLY,
    WORD_COMMENTS,
    comments_are_enabled,
    normalize_audit_mode,
)


class AuditModeTests(unittest.TestCase):
    def test_reports_only_is_the_safe_default(self) -> None:
        self.assertEqual(normalize_audit_mode("unknown"), REPORTS_ONLY)
        self.assertEqual(normalize_audit_mode(""), REPORTS_ONLY)

    def test_comment_mode_requires_explicit_selection(self) -> None:
        self.assertTrue(comments_are_enabled(WORD_COMMENTS))
        self.assertFalse(comments_are_enabled(REPORTS_ONLY))
