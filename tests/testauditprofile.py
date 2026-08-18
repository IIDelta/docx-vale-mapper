from __future__ import annotations

import unittest

from validators.auditprofile import (
    OPERATIONAL_AUDIT,
    normalize_audit_profile,
)


class AuditProfileTests(unittest.TestCase):
    """Tests for operational audit profiles."""

    def test_operational_profile_normalization(self) -> None:
        self.assertEqual(
            normalize_audit_profile(""),
            OPERATIONAL_AUDIT,
        )
        self.assertEqual(
            normalize_audit_profile("Standard Audit"),
            OPERATIONAL_AUDIT,
        )
        self.assertEqual(
            normalize_audit_profile("Operational Audit"),
            OPERATIONAL_AUDIT,
        )


if __name__ == "__main__":
    unittest.main()
