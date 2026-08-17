from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path.cwd()
EXPECTED_HEAD = "4b094bc061f6dbd5266e441353557c0369887b6d"
CONFIG_PATH = ROOT / "config" / "scientificterms.json"
VALIDATOR_PATH = ROOT / "validators" / "scientificterms.py"
MAIN_PATH = ROOT / "main.py"
MANIFEST_PATH = ROOT / "config" / "styleguidecoverage.json"
TEST_PATH = ROOT / "tests" / "testscientificterms.py"

CONFIG = {"italic_required": [], "roman_required": []}

VALIDATOR_SOURCE = '''from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from validators.abbreviationvalidator import ParagraphRecord, make_finding


def load_scientific_terms(config_path: Path) -> dict[str, list[str]]:
    """Load controlled scientific typography terms without guessing context."""
    empty = {"italic_required": [], "roman_required": []}
    if not config_path.is_file():
        return empty
    with config_path.open(encoding="utf-8") as input_file:
        payload = json.load(input_file)
    if not isinstance(payload, dict):
        raise ValueError("Scientific term registry must be a JSON object.")
    result: dict[str, list[str]] = {}
    for key in empty:
        values = payload.get(key, [])
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f"Scientific term registry key '{key}' must be a string list.")
        result[key] = sorted({value.strip() for value in values if value.strip()}, key=str.casefold)
    return result


def validate_scientific_terms(
    paragraph: ParagraphRecord,
    text: str,
    get_format,
    registry: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Check only registry-approved terms for italic or roman formatting."""
    findings: list[dict[str, Any]] = []
    for term in registry["italic_required"]:
        for match in re.finditer(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", text):
            if not get_format(match.start(), match.end()).get("italic", False):
                findings.append(make_finding(
                    "Clinical.ConfiguredItalicRequired",
                    "warning",
                    "Scientific typography: Italicize this configured scientific term.",
                    match.group(0),
                    paragraph,
                ))
    for term in registry["roman_required"]:
        for match in re.finditer(rf"(?<![A-Za-z0-9]){re.escape(term)}(?![A-Za-z0-9])", text, flags=re.IGNORECASE):
            if get_format(match.start(), match.end()).get("italic", False):
                findings.append(make_finding(
                    "Clinical.ConfiguredRomanRequired",
                    "warning",
                    "Scientific typography: Do not italicize this configured term.",
                    match.group(0),
                    paragraph,
                ))
    return findings
'''

TEST_SOURCE = '''from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from validators.abbreviationvalidator import ParagraphRecord
from validators.scientificterms import load_scientific_terms, validate_scientific_terms


class ScientificTermsTests(unittest.TestCase):
    def test_registry_terms_are_deduplicated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "terms.json"
            path.write_text(json.dumps({"italic_required": ["Escherichia coli", "Escherichia coli"], "roman_required": ["in vitro"]}), encoding="utf-8")
            registry = load_scientific_terms(path)
        self.assertEqual(registry["italic_required"], ["Escherichia coli"])

    def test_configured_italic_term_is_flagged_when_roman(self) -> None:
        paragraph = ParagraphRecord(index=1, line=1, text="Escherichia coli")
        findings = validate_scientific_terms(
            paragraph,
            "Escherichia coli",
            lambda start, end: {"italic": False},
            {"italic_required": ["Escherichia coli"], "roman_required": []},
        )
        self.assertEqual(findings[0]["Check"], "Clinical.ConfiguredItalicRequired")

    def test_unknown_scientific_looking_term_is_not_flagged(self) -> None:
        paragraph = ParagraphRecord(index=1, line=1, text="BRCA1")
        findings = validate_scientific_terms(
            paragraph,
            "BRCA1",
            lambda start, end: {"italic": False},
            {"italic_required": [], "roman_required": []},
        )
        self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
'''


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, encoding="utf-8").strip()


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {label} target; found {count}.")
    return source.replace(old, new, 1)


def main() -> None:
    if git_head() != EXPECTED_HEAD:
        raise RuntimeError(f"Expected HEAD {EXPECTED_HEAD}; current HEAD is {git_head()}.")
    if any(path.exists() for path in (CONFIG_PATH, VALIDATOR_PATH, TEST_PATH)):
        raise RuntimeError("P17 files already exist. Refusing to overwrite committed work.")

    original_main = MAIN_PATH.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in original_main else "\n"
    main_source = original_main.replace("\r\n", "\n")
    main_source = replace_once(
        main_source,
        "from validators.typographyvalidator import (\n",
        "from validators.scientificterms import (\n    load_scientific_terms,\n    validate_scientific_terms,\n)\nfrom validators.typographyvalidator import (\n",
        "scientific term imports",
    )
    main_source = replace_once(
        main_source,
        "ABBREVIATION_DATABASE_PATH = (\n    PROJECT_ROOT / \"data\" / \"abbreviations.sqlite\"\n)\n",
        "ABBREVIATION_DATABASE_PATH = (\n    PROJECT_ROOT / \"data\" / \"abbreviations.sqlite\"\n)\n\nSCIENTIFIC_TERMS_PATH = (\n    PROJECT_ROOT / \"config\" / \"scientificterms.json\"\n)\n",
        "scientific registry path",
        )
    registry_marker = "    record_by_index = {\n"

    if registry_marker not in main_source:
        raise RuntimeError(
            "Could not locate the typography record index."
        )

    main_source = main_source.replace(
        registry_marker,
        (
            "    scientific_terms = load_scientific_terms(\n"
            "        SCIENTIFIC_TERMS_PATH\n"
            "    )\n"
            + registry_marker
        ),
        1,
    )
    main_source = replace_once(
        main_source,
        "        findings.extend(\n            validate_unit_nonbreaking_spaces(\n                paragraph=record,\n                raw_text=raw_text,\n            )\n        )\n",
        "        findings.extend(\n            validate_unit_nonbreaking_spaces(\n                paragraph=record,\n                raw_text=raw_text,\n            )\n        )\n        findings.extend(\n            validate_scientific_terms(\n                paragraph=record,\n                text=offset_preserving_text,\n                get_format=get_format,\n                registry=scientific_terms,\n            )\n        )\n",
        "configured scientific term validation",
    )

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for item in manifest.get("coverage", []):
        if item.get("guide_section") == "10.0":
            item["notes"] = item.get("notes", "").rstrip() + " Registry-approved scientific terms can now be checked for italic or roman formatting."

    CONFIG_PATH.write_text(json.dumps(CONFIG, indent=2) + "\n", encoding="utf-8")
    VALIDATOR_PATH.write_text(VALIDATOR_SOURCE.replace("\n", newline), encoding="utf-8")
    MAIN_PATH.write_text(main_source.replace("\n", newline), encoding="utf-8")
    TEST_PATH.write_text(TEST_SOURCE.replace("\n", newline), encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("P17 configurable scientific typography installed successfully.")
    print("Run: python -m unittest tests.testscientificterms -v")
    print("Then: python tests/runregressiontests.py")


if __name__ == "__main__":
    main()
