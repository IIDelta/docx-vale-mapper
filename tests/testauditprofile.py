from __future__ import annotations

import unittest

from validators.auditprofile import (
    ADVANCED_AUDIT,
    STANDARD_AUDIT,
    is_advanced_profile,
    normalize_audit_profile,
)


class AuditProfileTests(unittest.TestCase):
    """Tests for production-safe and advanced audit profiles."""

    def test_standard_profile_is_default(self) -> None:
        self.assertEqual(
            normalize_audit_profile(""),
            STANDARD_AUDIT,
        )

    def test_standard_display_name(self) -> None:
        self.assertEqual(
            normalize_audit_profile(
                "Standard Audit"
            ),
            STANDARD_AUDIT,
        )

    def test_advanced_display_name(self) -> None:
        self.assertEqual(
            normalize_audit_profile(
                "Advanced Structural Review"
            ),
            ADVANCED_AUDIT,
        )

    def test_advanced_check(self) -> None:
        self.assertTrue(
            is_advanced_profile(
                "advanced"
            )
        )

        self.assertFalse(
            is_advanced_profile(
                "standard"
            )
        )


if __name__ == "__main__":
    unittest.main()
