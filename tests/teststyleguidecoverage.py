from __future__ import annotations

import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "config" / "styleguidecoverage.json"
REQUIRED_SECTIONS = {
    "1.0", "2.0", "3.0", "4.0", "5.0", "6.0", "7.0", "8.0",
    "9.0", "10.0", "11.0", "12.0", "Appendix A", "Appendix B",
    "Appendix C", "Appendix D",
}


class StyleGuideCoverageTests(unittest.TestCase):
    def load_manifest(self) -> dict:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

    def test_manifest_covers_every_required_section(self) -> None:
        manifest = self.load_manifest()
        self.assertIsInstance(manifest, dict)
        self.assertIn("status_values", manifest)
        self.assertIn("coverage", manifest)
        self.assertIsInstance(manifest["coverage"], list)

        sections = {
            item["guide_section"]
            for item in manifest["coverage"]
        }
        self.assertSetEqual(REQUIRED_SECTIONS - sections, set())

    def test_coverage_entries_use_declared_statuses_and_notes(self) -> None:
        manifest = self.load_manifest()
        allowed_statuses = set(manifest["status_values"])
        for item in manifest["coverage"]:
            self.assertIn(item.get("status"), allowed_statuses)
            self.assertTrue(item.get("topic", "").strip())
            self.assertTrue(item.get("notes", "").strip())

    def test_backlog_entries_are_explicit_and_prioritized(self) -> None:
        manifest = self.load_manifest()
        self.assertIn("remaining_backlog", manifest)
        for item in manifest["remaining_backlog"]:
            self.assertTrue(item.get("topic", "").strip())
            self.assertIn(
                item.get("target_status"),
                set(manifest["status_values"]),
            )
            self.assertIn(item.get("priority"), {"high", "medium", "low"})

    def test_no_requirement_is_unclassified(self) -> None:
        manifest = self.load_manifest()
        statuses = {
            item["status"]
            for item in manifest["coverage"]
        }
        self.assertNotIn("unclassified", statuses)


if __name__ == "__main__":
    unittest.main()
