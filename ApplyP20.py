from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path.cwd()
EXPECTED_HEAD = "9638dacbc4e18c2f3e443480b7fe657f0fcdb188"
REPORT_PATH = ROOT / "runtime" / "auditreport.py"
HEADING_PATH = ROOT / "validators" / "headingvalidator.py"
HEADING_TERMS_PATH = ROOT / "validators" / "headingterms.py"
CONFIG_PATH = ROOT / "config" / "headingterms.json"
MAIN_PATH = ROOT / "main.py"
TEST_PATH = ROOT / "tests" / "testheadingterms.py"

CONFIG = {"acronym_exemptions": [], "title_case_exemptions": []}

TERMS_SOURCE = '''from __future__ import annotations

import json
from pathlib import Path


def load_heading_terms(config_path: Path) -> dict[str, set[str]]:
    """Load controlled heading exemptions without inferring terminology."""
    result = {"acronym_exemptions": set(), "title_case_exemptions": set()}
    if not config_path.is_file():
        return result
    with config_path.open(encoding="utf-8") as input_file:
        payload = json.load(input_file)
    if not isinstance(payload, dict):
        raise ValueError("Heading term registry must be a JSON object.")
    for key in result:
        values = payload.get(key, [])
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f"Heading term registry key '{key}' must be a string list.")
        result[key] = {value.casefold() for value in values if value.strip()}
    return result
'''

TEST_SOURCE = '''from __future__ import annotations

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
'''


def head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

def once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise RuntimeError(f"Expected one {label} target; found {text.count(old)}.")
    return text.replace(old, new, 1)

def main() -> None:
    if head() != EXPECTED_HEAD:
        raise RuntimeError(f"Expected {EXPECTED_HEAD}; current HEAD is {head()}.")
    if any(path.exists() for path in (HEADING_TERMS_PATH, CONFIG_PATH, TEST_PATH)):
        raise RuntimeError("P20 files already exist. Refusing to overwrite committed work.")
    newline = "\r\n" if "\r\n" in MAIN_PATH.read_text(encoding="utf-8") else "\n"
    main = MAIN_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
    report = REPORT_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")
    heading = HEADING_PATH.read_text(encoding="utf-8").replace("\r\n", "\n")

    report = once(report, 'def write_audit_findings_report(\n', 'def enrich_finding(finding: dict[str, Any], record) -> dict[str, Any]:\n    result = serialize_finding(finding)\n    if record is not None:\n        result["Context"] = {\n            "content_zone": record.content_zone,\n            "section_context": record.section_context,\n            "style_name": record.style_name,\n            "heading_level": record.heading_level,\n            "is_in_table": record.is_in_table,\n            "list_marker": record.list_marker,\n            "has_protected_field": record.has_protected_field,\n            "paragraph_text": record.text,\n        }\n    return result\n\n\ndef write_audit_findings_report(\n', 'audit report enrichment helper')
    report = once(report, '    suppressed_findings: Counter,\n) -> Path:\n', '    suppressed_findings: Counter,\n    paragraph_records=(),\n) -> Path:\n', 'audit report signature')
    report = once(report, '    report_path = output_path.with_suffix(".audit_findings.json")\n', '    report_path = output_path.with_suffix(".audit_findings.json")\n    record_by_line = {record.line: record for record in paragraph_records}\n', 'audit report context map')
    report = once(report, '        "findings": [serialize_finding(item) for item in findings],\n', '        "findings": [enrich_finding(item, record_by_line.get(item.get("Line"))) for item in findings],\n', 'audit report findings payload')

    main = once(main, 'from validators.headingvalidator import (\n', 'from validators.headingterms import (\n    load_heading_terms,\n)\nfrom validators.headingvalidator import (\n', 'heading terms import')
    main = once(main, 'SCIENTIFIC_TERMS_PATH = (\n    PROJECT_ROOT / "config" / "scientificterms.json"\n)\n', 'SCIENTIFIC_TERMS_PATH = (\n    PROJECT_ROOT / "config" / "scientificterms.json"\n)\n\nHEADING_TERMS_PATH = (\n    PROJECT_ROOT / "config" / "headingterms.json"\n)\n', 'heading terms path')
    main = once(main, '    scientific_terms = load_scientific_terms(\n        SCIENTIFIC_TERMS_PATH\n    )\n', '    scientific_terms = load_scientific_terms(\n        SCIENTIFIC_TERMS_PATH\n    )\n    heading_terms = load_heading_terms(HEADING_TERMS_PATH)\n', 'heading terms load')
    main = once(main, '                format_state=get_format(0, len(offset_preserving_text)),\n            )\n', '                format_state=get_format(0, len(offset_preserving_text)),\n                heading_terms=heading_terms,\n            )\n', 'heading terms validation argument')
    main = once(main, '            suppressed_findings=suppressed_findings,\n        )\n', '            suppressed_findings=suppressed_findings,\n            paragraph_records=paragraph_records,\n        )\n', 'audit findings provenance argument')

    heading = once(heading, '    format_state: dict[str, bool],\n) -> list[dict]:\n', '    format_state: dict[str, bool],\n    heading_terms: dict[str, set[str]] | None = None,\n) -> list[dict]:\n', 'heading validator signature')
    heading = once(heading, '    if not paragraph.is_heading:\n        return []\n', '    if not paragraph.is_heading:\n        return []\n    heading_terms = heading_terms or {"acronym_exemptions": set(), "title_case_exemptions": set()}\n', 'heading terms default')
    heading = once(heading, '    if alpha_text.isupper():\n', '    if alpha_text.isupper():\n        if text.strip().casefold() in heading_terms["acronym_exemptions"]:\n            return []\n', 'heading acronym exemption')
    heading = once(heading, '            elif (\n                not should_be_minor\n', '            elif (\n                normalized in heading_terms["title_case_exemptions"]\n            ):\n                continue\n            elif (\n                not should_be_minor\n', 'heading title exemption')

    REPORT_PATH.write_text(report.replace("\n", newline), encoding="utf-8")
    MAIN_PATH.write_text(main.replace("\n", newline), encoding="utf-8")
    HEADING_PATH.write_text(heading.replace("\n", newline), encoding="utf-8")
    HEADING_TERMS_PATH.write_text(TERMS_SOURCE.replace("\n", newline), encoding="utf-8")
    CONFIG_PATH.write_text(json.dumps(CONFIG, indent=2) + "\n", encoding="utf-8")
    TEST_PATH.write_text(TEST_SOURCE.replace("\n", newline), encoding="utf-8")
    print("P20 provenance and heading-term calibration installed successfully.")
    print("Run: python -m unittest tests.testheadingterms -v")
    print("Then: python tests/runregressiontests.py")

if __name__ == "__main__":
    main()
