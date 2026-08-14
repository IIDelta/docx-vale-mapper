from __future__ import annotations

import unittest

from validators.citationvalidator import (
    CitationFieldRecord,
    classify_field_code,
    is_protected_citation_field,
    target_overlaps_citation_field,
)


class CitationValidatorTests(unittest.TestCase):
    """Tests for citation and bibliography field detection."""

    def test_endnote_field_is_citation(self) -> None:
        self.assertEqual(
            classify_field_code(
                "ADDIN EN.CITE <EndNote field data>"
            ),
            "citation",
        )

    def test_word_citation_field_is_citation(self) -> None:
        self.assertEqual(
            classify_field_code(
                "CITATION Smith2026"
            ),
            "citation",
        )

    def test_zotero_field_is_citation(self) -> None:
        self.assertEqual(
            classify_field_code(
                "ADDIN ZOTERO_ITEM CSL_CITATION"
            ),
            "citation",
        )

    def test_bibliography_field_is_detected(self) -> None:
        self.assertEqual(
            classify_field_code(
                "BIBLIOGRAPHY"
            ),
            "bibliography",
        )

    def test_non_citation_field_is_other(self) -> None:
        self.assertEqual(
            classify_field_code(
                "PAGE"
            ),
            "other",
        )

    def test_citation_field_is_protected(self) -> None:
        self.assertTrue(
            is_protected_citation_field(
                "ADDIN EN.CITE <data>"
            )
        )

    def test_overlap_is_detected(self) -> None:
        fields = [
            CitationFieldRecord(
                field_type="citation",
                code_text="CITATION Smith2026",
                result_start=100,
                result_end=120,
            )
        ]

        self.assertTrue(
            target_overlaps_citation_field(
                target_start=105,
                target_end=110,
                citation_fields=fields,
            )
        )

    def test_non_overlapping_range_is_allowed(self) -> None:
        fields = [
            CitationFieldRecord(
                field_type="citation",
                code_text="CITATION Smith2026",
                result_start=100,
                result_end=120,
            )
        ]

        self.assertFalse(
            target_overlaps_citation_field(
                target_start=130,
                target_end=140,
                citation_fields=fields,
            )
        )
