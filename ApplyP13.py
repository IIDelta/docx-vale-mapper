from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path.cwd()
EXPECTED_HEAD = "1b34f1e32d515f161a02b28de5a51703bff409e3"
CAPTION_PATH = ROOT / "validators" / "captionfootnotevalidator.py"
MAIN_PATH = ROOT / "main.py"
TEST_PATH = ROOT / "tests" / "testfootnoteorder.py"

HELPER_SOURCE = '''

FOOTNOTE_LETTER_PATTERN = re.compile(
    r"^(?P<letter>[a-z])(?:\\s|,)",
    flags=re.IGNORECASE,
)


def footnote_category(text: str) -> int | None:
    """Return source/general/statistical/lettered order for a footnote."""
    stripped = text.strip()
    lowered = stripped.casefold()
    if lowered.startswith("source:"):
        return 0
    if re.match(r"^[*†]\\s+p\\s*[<=>]", stripped, flags=re.IGNORECASE):
        return 2
    if FOOTNOTE_LETTER_PATTERN.match(stripped):
        return 3
    if is_table_footnote_like(stripped):
        return 1
    return None


def validate_footnote_group_order(
    footnotes: list[FootnoteRecord],
) -> list[dict]:
    """Validate recognized footnote category order and letter progression."""
    grouped: dict[str, list[FootnoteRecord]] = {}
    for footnote in footnotes:
        if footnote_category(footnote.text) is None:
            continue
        grouped.setdefault(footnote.container_key or "__document__", []).append(footnote)

    findings: list[dict] = []
    for group in grouped.values():
        previous_category = -1
        previous_letter = ""
        for footnote in sorted(group, key=lambda item: item.range_start):
            category = footnote_category(footnote.text)
            if category is None:
                continue
            if category < previous_category:
                findings.append(
                    make_range_finding(
                        check="Clinical.FootnoteOrder",
                        severity="warning",
                        message=(
                            "Style guide footnote format: Present source, "
                            "general, statistical, then lettered footnotes."
                        ),
                        match=footnote.text,
                        paragraph=footnote.paragraph,
                        range_start=footnote.range_start,
                        range_end=footnote.range_end,
                    )
                )
            previous_category = max(previous_category, category)

            letter_match = FOOTNOTE_LETTER_PATTERN.match(footnote.text.strip())
            if letter_match is None:
                continue
            current_letter = letter_match.group("letter").casefold()
            if previous_letter and ord(current_letter) != ord(previous_letter) + 1:
                findings.append(
                    make_range_finding(
                        check="Clinical.FootnoteLetterSequence",
                        severity="warning",
                        message=(
                            "Style guide footnote format: Use lowercase "
                            "letter designators in alphabetical order."
                        ),
                        match=footnote.text,
                        paragraph=footnote.paragraph,
                        range_start=footnote.range_start,
                        range_end=footnote.range_end,
                    )
                )
            previous_letter = current_letter
    return findings
'''

TEST_SOURCE = '''from __future__ import annotations

import unittest

from validators.abbreviationvalidator import ParagraphRecord
from validators.captionfootnotevalidator import FootnoteRecord, validate_footnotes


def footnote(text: str, position: int, container: str = "table:1") -> FootnoteRecord:
    return FootnoteRecord(
        text=text,
        paragraph=ParagraphRecord(index=position, line=position, text=text),
        range_start=position,
        range_end=position + len(text),
        container_key=container,
    )


class FootnoteOrderTests(unittest.TestCase):
    def test_out_of_order_statistical_note_is_flagged(self) -> None:
        findings = validate_footnotes(
            [
                footnote("Source: Table 1.", 1),
                footnote("a Safety population.", 30),
                footnote("* p<0.05.", 60),
            ]
        )
        checks = {finding["Check"] for finding in findings}
        self.assertIn("Clinical.FootnoteOrder", checks)

    def test_letter_gap_is_flagged_within_one_table(self) -> None:
        findings = validate_footnotes(
            [
                footnote("a Safety population.", 1),
                footnote("c Response population.", 40),
            ]
        )
        checks = {finding["Check"] for finding in findings}
        self.assertIn("Clinical.FootnoteLetterSequence", checks)

    def test_letter_sequence_restarts_for_next_table(self) -> None:
        findings = validate_footnotes(
            [
                footnote("a Safety population.", 1, "table:1"),
                footnote("a Response population.", 40, "table:2"),
            ]
        )
        checks = {finding["Check"] for finding in findings}
        self.assertNotIn("Clinical.FootnoteLetterSequence", checks)


if __name__ == "__main__":
    unittest.main()
'''


def git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
    ).strip()


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one {label} target; found {count}.")
    return source.replace(old, new, 1)


def main() -> None:
    if git_head() != EXPECTED_HEAD:
        raise RuntimeError(
            f"Expected HEAD {EXPECTED_HEAD}; current HEAD is {git_head()}."
        )
    if TEST_PATH.exists():
        raise RuntimeError(f"Refusing to overwrite existing test: {TEST_PATH}")

    original_caption = CAPTION_PATH.read_text(encoding="utf-8")
    original_main = MAIN_PATH.read_text(encoding="utf-8")
    newline = "\r\n" if "\r\n" in original_caption else "\n"
    caption_source = original_caption.replace("\r\n", "\n")
    main_source = original_main.replace("\r\n", "\n")

    footnote_class_start = caption_source.find("class FootnoteRecord:")
    if footnote_class_start < 0:
        raise RuntimeError("Could not locate FootnoteRecord.")
    footnote_field = "    range_end: int = 0\n"
    footnote_field_position = caption_source.find(
        footnote_field,
        footnote_class_start,
    )
    if footnote_field_position < 0:
        raise RuntimeError("Could not locate FootnoteRecord range_end field.")
    insertion_position = footnote_field_position + len(footnote_field)
    caption_source = (
        caption_source[:insertion_position]
        + "    container_key: str = \"\"\n"
        + caption_source[insertion_position:]
    )
    footnote_function_start = caption_source.find("def validate_footnotes(")
    if footnote_function_start < 0:
        raise RuntimeError("Could not locate validate_footnotes.")
    footnote_return = caption_source.find(
        "    return findings\n",
        footnote_function_start,
    )
    if footnote_return < 0:
        raise RuntimeError("Could not locate validate_footnotes return.")
    caption_source = (
        caption_source[:footnote_return]
        + "    findings.extend(validate_footnote_group_order(footnotes))\n"
        + caption_source[footnote_return:]
    )
    caption_source = caption_source.rstrip() + HELPER_SOURCE + "\n"

    main_source = replace_once(
        main_source,
        "                            range_start=footnote_start,\n                            range_end=footnote_end,\n",
        "                            range_start=footnote_start,\n                            range_end=footnote_end,\n                            container_key=f\"table:{table_index}\",\n",
        "table footnote container assignment",
    )

    CAPTION_PATH.write_text(caption_source.replace("\n", newline), encoding="utf-8")
    MAIN_PATH.write_text(main_source.replace("\n", newline), encoding="utf-8")
    TEST_PATH.write_text(TEST_SOURCE.replace("\n", newline), encoding="utf-8")

    print("P13 footnote order validation installed successfully.")
    print("Run: python -m unittest tests.testfootnoteorder -v")
    print("Then: python tests/runregressiontests.py")


if __name__ == "__main__":
    main()
