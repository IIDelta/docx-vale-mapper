from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from validators.headingterms import load_heading_terms


class HeadingTermsTests(unittest.TestCase):
    def test_registry_normalizes_case(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "terms.json"
            path.write_text(json.dumps({"acronym_exemptions": ["EORTC QLQ-C30"], "title_case_exemptions": ["sEPO"]}), encoding="utf-8")
            terms = load_heading_terms(path)
        self.assertIn("eortc qlq-c30", terms["acronym_exemptions"])
        self.assertIn("sepo", terms["title_case_exemptions"])


if __name__ == "__main__":
    unittest.main()
