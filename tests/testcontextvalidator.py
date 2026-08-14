from __future__ import annotations

import unittest

from validators.contextvalidator import (
    classify_content_zone,
)


class ContextValidatorTests(unittest.TestCase):
    """Tests for R2 document context classification."""

    def test_title_page_table_is_classified(self) -> None:
        zone = classify_content_zone(
            protocol_summary_active=False,
            text="Protocol Number:",
            style_name="Normal",
            is_in_table=True,
            list_marker="",
            title_page_active=True,
            summary_active=False,
            reference_active=False,
        )

        self.assertEqual(zone, "title_page")

    def test_summary_content_is_classified(self) -> None:
        zone = classify_content_zone(
            protocol_summary_active=False,
            text="Updated inclusion criteria.",
            style_name="Normal",
            is_in_table=False,
            list_marker="",
            title_page_active=False,
            summary_active=True,
            reference_active=False,
        )

        self.assertEqual(
            zone,
            "summary_of_changes",
        )

    def test_body_list_is_classified(self) -> None:
        zone = classify_content_zone(
            protocol_summary_active=False,
            text="First item.",
            style_name="Normal",
            is_in_table=False,
            list_marker="•",
            title_page_active=False,
            summary_active=False,
            reference_active=False,
        )

        self.assertEqual(zone, "list_item")

    def test_table_cell_is_classified(self) -> None:
        zone = classify_content_zone(
            protocol_summary_active=False,
            text="Treatment Group",
            style_name="Normal",
            is_in_table=True,
            list_marker="",
            title_page_active=False,
            summary_active=False,
            reference_active=False,
        )

        self.assertEqual(zone, "table_cell")

    def test_protocol_summary_content_is_classified(
        self,
    ) -> None:
        zone = classify_content_zone(
            text="Overall Design",
            style_name="Normal",
            is_in_table=False,
            list_marker="•",
            title_page_active=False,
            summary_active=False,
            protocol_summary_active=True,
            reference_active=False,
        )

        self.assertEqual(
            zone,
            "protocol_summary",
        )

