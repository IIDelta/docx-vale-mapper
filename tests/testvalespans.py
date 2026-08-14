from __future__ import annotations

import unittest

from validators.valespan import (
    vale_span_to_word_range,
)

from validators.valespan import (
    resolve_match_offsets,
    vale_span_to_word_range,
    vale_match_occurrence_index,
)


class ValeSpanTests(unittest.TestCase):
    """Tests for Vale-to-Word exact range conversion."""

    def test_valid_span_maps_to_word_range(self) -> None:
        result = vale_span_to_word_range(
            paragraph_start=100,
            paragraph_end=124,
            span=[17, 23],
        )

        self.assertEqual(
            result,
            (116, 123),
        )

    def test_invalid_span_returns_none(self) -> None:
        result = vale_span_to_word_range(
            paragraph_start=100,
            paragraph_end=124,
            span=None,
        )

        self.assertIsNone(result)

    def test_span_is_clamped_to_paragraph_range(self) -> None:
        result = vale_span_to_word_range(
            paragraph_start=100,
            paragraph_end=124,
            span=[1, 999],
        )

        self.assertEqual(
            result,
            (100, 124),
        )

    def test_match_offset_selects_nearest_occurrence(
        self,
    ) -> None:
        text = (
            "healthcare is one term. "
            "Another healthcare term appears later."
        )

        result = resolve_match_offsets(
            vale_text=text,
            match_text="healthcare",
            span=[33, 43],
        )

        self.assertEqual(
            result,
            (32, 42),
        )


    def test_match_offset_returns_none_when_absent(
        self,
    ) -> None:
        result = resolve_match_offsets(
            vale_text="No matching content.",
            match_text="healthcare",
            span=[1, 11],
        )

        self.assertIsNone(result)

    def test_match_occurrence_index_uses_nearest_span(
        self,
    ) -> None:
        text = (
            "healthcare is first. "
            "healthcare is second."
        )

        result = vale_match_occurrence_index(
            vale_text=text,
            match_text="healthcare",
            span=[22, 32],
        )

        self.assertEqual(
            result,
            1,
        )



