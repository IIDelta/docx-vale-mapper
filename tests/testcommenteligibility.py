from __future__ import annotations

import unittest

from runtime.commentpolicy import comment_eligible


class CommentEligibilityTests(unittest.TestCase):
    def test_body_narrative_is_eligible(self) -> None:
        finding = {
            "Context": {
                "content_zone": "body_narrative",
                "is_in_table": False,
                "has_protected_field": False,
                "style_name": "A-Body Text",
            }
        }

        self.assertTrue(comment_eligible(finding))

    def test_title_page_is_ineligible(self) -> None:
        finding = {
            "Context": {
                "content_zone": "title_page",
                "is_in_table": True,
                "has_protected_field": False,
                "style_name": "Table:Text",
            }
        }

        self.assertFalse(comment_eligible(finding))

    def test_bibliography_style_is_ineligible(self) -> None:
        finding = {
            "Context": {
                "content_zone": "body_narrative",
                "is_in_table": False,
                "has_protected_field": False,
                "style_name": "EndNote Bibliography",
            }
        }

        self.assertFalse(comment_eligible(finding))

    def test_table_footnote_style_is_ineligible(self) -> None:
        finding = {
            "Context": {
                "content_zone": "body_narrative",
                "is_in_table": False,
                "has_protected_field": False,
                "style_name": "A-Table Footnote",
            }
        }

        self.assertFalse(comment_eligible(finding))


if __name__ == "__main__":
    unittest.main()
