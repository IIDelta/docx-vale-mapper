from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = PROJECT_ROOT / "config" / "commentpolicy.json"
CATALOG_PATH = PROJECT_ROOT / "docs" / "rulecatalog.md"

class RuleCatalogTests(unittest.TestCase):
    def load_policy(self) -> dict:
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def test_catalog_matches_policy_exactly(self) -> None:
        policy = self.load_policy()
        policy_rules = set()
        for key in ["auto_fix_rules", "comment_rules", "report_only_rules", "disabled_rules"]:
            policy_rules.update(policy.get(key, []))
            
        catalog_content = CATALOG_PATH.read_text(encoding="utf-8")
        
        # Parse table rows: | `Clinical.RuleId` | Section | Disposition | Severity | Coverage | Rationale |
        # We need to find the main rule table.
        catalog_rules = set()
        table_matches = re.finditer(r"\|\s*`(Clinical\.[A-Za-z0-9\.]+)`\s*\|", catalog_content)
        for match in table_matches:
            catalog_rules.add(match.group(1))
            
        # The catalog must contain exactly all the rules in the policy
        self.assertSetEqual(policy_rules, catalog_rules)

    def test_catalog_columns_are_populated(self) -> None:
        catalog_content = CATALOG_PATH.read_text(encoding="utf-8")
        # Extract rows under the operational policy
        lines = catalog_content.splitlines()
        in_table = False
        for line in lines:
            if line.startswith("| `Clinical."):
                parts = [p.strip() for p in line.split("|")[1:-1]]
                self.assertEqual(len(parts), 6, f"Row does not have 6 columns: {line}")
                rule_id, section, disposition, severity, coverage, rationale = parts
                
                self.assertTrue(rule_id.startswith("`Clinical."))
                self.assertTrue(len(section) > 0)
                self.assertIn(disposition, ["auto_fix", "comment", "report_only", "disabled"])
                self.assertIn(severity, ["error", "warning"])
                self.assertTrue(len(coverage) > 0)
                self.assertTrue(len(rationale) > 0)

if __name__ == "__main__":
    unittest.main()
