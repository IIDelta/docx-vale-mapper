from __future__ import annotations

import unittest

from validators.fieldprotection import (
    is_protected_field_code,
    ranges_overlap,
)


class FieldProtectionTests(unittest.TestCase):
    def test_citation_and_reference_field_codes_are_protected(self) -> None:
        for code in (
            " ADDIN EN.CITE <EndNote><Cite> ",
            " CITATION Smith 2025 ",
            " BIBLIOGRAPHY ",
            " ZOTERO_ITEM CSL_CITATION ",
            " PAGEREF _Ref123 ",
            " REF Table3 ",
        ):
            self.assertTrue(is_protected_field_code(code))

    def test_ordinary_text_is_not_a_protected_field(self) -> None:
        self.assertFalse(is_protected_field_code("ordinary prose"))

    def test_overlap_detection(self) -> None:
        protected = [(10, 20), (30, 40)]
        self.assertTrue(ranges_overlap(12, 14, protected))
        self.assertTrue(ranges_overlap(18, 22, protected))
        self.assertTrue(ranges_overlap(25, 35, protected))
        self.assertFalse(ranges_overlap(20, 25, protected))
        self.assertFalse(ranges_overlap(40, 45, protected))


if __name__ == "__main__":
    unittest.main()
