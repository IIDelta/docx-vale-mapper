from __future__ import annotations

import unittest

from validators.abbreviationvalidator import (
    ParagraphRecord,
)
from validators.referencevalidator import (
    validate_active_external_link,
    validate_reference_text,
)


def record(
    index: int,
    text: str,
) -> ParagraphRecord:
    """Create a compact paragraph fixture."""

    return ParagraphRecord(
        index=index,
        line=index,
        text=text,
    )


class ReferenceValidatorTests(unittest.TestCase):
    """Tests for A8.2 reference mechanics."""

    def test_raw_urls_are_flagged(self) -> None:
        findings = validate_reference_text(
            [
                record(
                    1,
                    (
                        "See https://example.org/reference "
                        "and www.example.com."
                    ),
                )
            ]
        )

        self.assertEqual(
            len(findings),
            2,
        )

        self.assertEqual(
            findings[0]["Check"],
            "Clinical.RawExternalURL",
        )

        self.assertEqual(
            findings[1]["Check"],
            "Clinical.RawExternalURL",
        )

    def test_external_link_is_flagged(self) -> None:
        finding = validate_active_external_link(
            paragraph=record(
                1,
                "External guidance was reviewed.",
            ),
            display_text="External guidance",
            address="https://example.org",
        )

        self.assertEqual(
            finding["Check"],
            "Clinical.ActiveExternalLink",
        )

        self.assertEqual(
            finding["Severity"],
            "error",
        )


if __name__ == "__main__":
    unittest.main()
