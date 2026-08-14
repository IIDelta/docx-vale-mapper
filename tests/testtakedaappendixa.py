from __future__ import annotations

import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = PROJECT_ROOT / "config" / "abbreviationpolicy.json"


class TakedaAppendixATests(unittest.TestCase):
    def test_policy_contains_all_appendix_a_protected_abbreviations(self) -> None:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        protected = set(policy["never_expand"])
        appendix_a = {
            "AIDS", "BCG", "CEDEX", "CI", "COVID-19", "cf", "DDT",
            "DNA", "EDTA", "FDA", "HIV", "HLA", "IQ", "IQR", "logMAR",
            "LS", "N", "n", "nb", "Nd:YAG", "OMIM", "PDF", "pH", "PO2",
            "Rh", "RNA", "SARS-CoV-2", "SD", "SE", "SEM", "SPSS", "SSC",
            "SSPE", "TNM", "ul", "US", "UV", "UV-A", "UV-B", "UV-C",
            "VDRL", "vs", "WHO",
        }

        self.assertSetEqual(
            appendix_a - protected,
            set(),
            "Appendix A protected abbreviations are missing from policy.",
        )


if __name__ == "__main__":
    unittest.main()
