from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path.cwd()
EXPECTED_HEAD = "50197f72d77c84668a72b369687eec2de27fc7b4"
MAIN_PATH = ROOT / "main.py"
MANIFEST_PATH = ROOT / "config" / "styleguidecoverage.json"
VALIDATOR_PATH = ROOT / "validators" / "headingvalidator.py"
TEST_PATH = ROOT / "tests" / "testheadingvalidator.py"

VALIDATOR_SOURCE = '''from __future__ import annotations

import re
from typing import Any

from validators.abbreviationvalidator import ParagraphRecord, make_finding


WORD_PATTERN = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)*")
MINOR_WORDS = {
    "a", "an", "the", "and", "as", "at", "by", "but", "for",
    "in", "nor", "of", "on", "or", "per", "so", "to", "up",
    "via", "yet",
}


def make_heading_finding(
    check: str,
    message: str,
    match: str,
    paragraph: ParagraphRecord,
) -> dict[str, Any]:
    return make_finding(
        check=check,
        severity="warning",
        message=message,
        match=match,
        paragraph=paragraph,
    )


def validate_heading_paragraph(
    paragraph: ParagraphRecord,
    text: str,
    format_state: dict[str, bool],
) -> list[dict]:
    """Review heading capitalization while respecting Word caps formatting."""
    if not paragraph.is_heading:
        return []

    words = list(WORD_PATTERN.finditer(text))
    if not words:
        return []

    alpha_text = "".join(match.group(0) for match in words)
    if alpha_text.isupper():
        if not (
            format_state.get("all_caps", False)
            or format_state.get("small_caps", False)
        ):
            return [
                make_heading_finding(
                    "Clinical.HeadingAllCapsTyped",
                    "Style guide headings: Use title case rather than manually typed all caps, unless an approved template requires otherwise.",
                    text,
                    paragraph,
                )
            ]
        return []

    findings: list[dict] = []
    word_count = len(words)
    for position, match in enumerate(words):
        token = match.group(0)
        pieces = token.split("-")
        for piece_index, piece in enumerate(pieces):
            normalized = piece.casefold()
            is_edge = position in {0, word_count - 1} and piece_index == 0
            should_be_minor = normalized in MINOR_WORDS and not is_edge
            if should_be_minor and piece[0].isupper():
                findings.append(
                    make_heading_finding(
                        "Clinical.HeadingMinorWordCase",
                        "Style guide headings: Lowercase articles, coordinating conjunctions, and short prepositions unless first or last.",
                        piece,
                        paragraph,
                    )
                )
            elif not should_be_minor and piece[0].islower():
                findings.append(
                    make_heading_finding(
                        "Clinical.HeadingTitleCase",
                        "Style guide headings: Capitalize major words and each applicable part of a hyphenated compound.",
                        piece,
                        paragraph,
                    )
                )
    return findings
'''

TEST_SOURCE = '''from __future__ import annotations

import unittest

from validators.abbreviationvalidator import ParagraphRecord
from validators.headingvalidator import validate_heading_paragraph


def heading(text: str) -> ParagraphRecord:
    return ParagraphRecord(
        index=1,
        line=1,
        text=text,
        is_heading=True,
    )


class HeadingValidatorTests(unittest.TestCase):
    def test_title_case_heading_passes(self) -> None:
        findings = validate_heading_paragraph(
            heading("Study Results for the Trial"),
            "Study Results for the Trial",
            {"all_caps": False, "small_caps": False},
        )
        self.assertEqual(findings, [])

    def test_minor_word_capitalization_is_flagged(self) -> None:
        findings = validate_heading_paragraph(
            heading("Study Results For The Trial"),
            "Study Results For The Trial",
            {"all_caps": False, "small_caps": False},
        )
        checks = {finding["Check"] for finding in findings}
        self.assertIn("Clinical.HeadingMinorWordCase", checks)

    def test_manually_typed_all_caps_is_flagged(self) -> None:
        findings = validate_heading_paragraph(
            heading("STUDY RESULTS FOR THE TRIAL"),
            "STUDY RESULTS FOR THE TRIAL",
            {"all_caps": False, "small_caps": False},
        )
        self.assertEqual(findings[0]["Check"], "Clinical.HeadingAllCapsTyped")

    def test_word_all_caps_formatting_is_not_flagged(self) -> None:
        findings = validate_heading_paragraph(
            heading("STUDY RESULTS FOR THE TRIAL"),
            "STUDY RESULTS FOR THE TRIAL",
            {"all_caps": True, "small_caps": False},
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
    if VALIDATOR_PATH.exists() or TEST_PATH.exists():
        raise RuntimeError("P16 files already exist. Refusing to overwrite committed work.")

    original_main = MAIN_PATH.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in original_main else "\n"
    main_source = original_main.replace("\r\n", "\n")

    main_source = replace_once(
        main_source,
        "from validators.referencevalidator import (\n",
        "from validators.headingvalidator import (\n    validate_heading_paragraph,\n)\nfrom validators.referencevalidator import (\n",
        "heading validator import",
    )
    main_source = replace_once(
        main_source,
        '                "superscript": (\n                    matched_range.Font.Superscript == -1\n                ),\n',
        '                "superscript": (\n                    matched_range.Font.Superscript == -1\n                ),\n                "all_caps": (\n                    matched_range.Font.AllCaps == -1\n                ),\n                "small_caps": (\n                    matched_range.Font.SmallCaps == -1\n                ),\n',
        "heading format state",
    )
    main_source = replace_once(
        main_source,
        "        findings.extend(\n            validate_typography_paragraph(\n                paragraph=record,\n                offset_preserving_text=offset_preserving_text,\n                get_format=get_format,\n            )\n        )\n",
        "        findings.extend(\n            validate_typography_paragraph(\n                paragraph=record,\n                offset_preserving_text=offset_preserving_text,\n                get_format=get_format,\n            )\n        )\n        findings.extend(\n            validate_heading_paragraph(\n                paragraph=record,\n                text=offset_preserving_text,\n                format_state=get_format(0, len(offset_preserving_text)),\n            )\n        )\n",
        "heading validation call",
    )

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest["remaining_backlog"] = [
        item for item in manifest.get("remaining_backlog", [])
        if item.get("topic") != "Heading capitalization with Word All Caps style awareness"
    ]
    for item in manifest.get("coverage", []):
        if item.get("guide_section") == "4.0":
            item["notes"] = item.get("notes", "").rstrip() + " Heading title-case review now respects Word All Caps and Small Caps formatting."

    VALIDATOR_PATH.write_text(VALIDATOR_SOURCE.replace("\n", newline), encoding="utf-8")
    MAIN_PATH.write_text(main_source.replace("\n", newline), encoding="utf-8")
    TEST_PATH.write_text(TEST_SOURCE.replace("\n", newline), encoding="utf-8")
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("P16 heading capitalization validation installed successfully.")
    print("Run: python -m unittest tests.testheadingvalidator -v")
    print("Then: python tests/runregressiontests.py")


if __name__ == "__main__":
    main()
