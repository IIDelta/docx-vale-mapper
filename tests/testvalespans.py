from __future__ import annotations

import unittest

from validators.valespan import (
    vale_span_to_word_range,
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
