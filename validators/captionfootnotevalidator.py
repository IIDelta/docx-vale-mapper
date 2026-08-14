from __future__ import annotations

import re
from dataclasses import dataclass

from validators.abbreviationvalidator import (
    ParagraphRecord,
    make_finding,
)


TABLE_LABEL_PATTERN = re.compile(
    r"^\s*Table\s+"
    r"(?P<label>\d+(?:\.[a-z])?)"
    r"(?P<terminal>\.)?",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class CaptionRecord:
    """A table or figure caption candidate."""

    kind: str
    text: str
    inside_table: bool
    paragraph: ParagraphRecord
    range_start: int = 0
    range_end: int = 0


@dataclass(frozen=True)
class FootnoteRecord:
    """A possible table/figure/appendix footnote."""

    text: str
    paragraph: ParagraphRecord
    range_start: int = 0
    range_end: int = 0


def make_range_finding(
    check: str,
    severity: str,
    message: str,
    match: str,
    paragraph: ParagraphRecord,
    range_start: int,
    range_end: int,
) -> dict:
    """Create a finding that can attach to an exact Word range."""

    finding = make_finding(
        check=check,
        severity=severity,
        message=message,
        match=match,
        paragraph=paragraph,
    )

    if range_end > range_start:
        finding["RangeStart"] = range_start
        finding["RangeEnd"] = range_end

    return finding


def is_table_footnote_like(
    text: str,
) -> bool:
    """
    Return True for recognizable table/figure footnote text.

    Lowercase lettered designators are accepted. Uppercase title text,
    such as "A Phase 3...", must not be treated as a footnote.
    """

    stripped = text.strip()

    if stripped.lower().startswith("source"):
        return True

    return bool(
        re.match(
            r"^(?:[a-z](?:,\s*[a-z])*|[*†])(?:\s|,)",
            stripped,
        )
    )


def validate_captions(
    captions: list[CaptionRecord],
) -> list[dict]:
    """
    Validate table-caption placement and numbered-label punctuation.
    """

    findings: list[dict] = []

    seen_labels: dict[str, CaptionRecord] = {}

    for caption in captions:
        if caption.kind != "Table":
            continue

        label_match = TABLE_LABEL_PATTERN.match(
            caption.text
        )

        if label_match is None:
            continue

        raw_label = label_match.group("label")
        terminal = label_match.group("terminal")

        label_key = raw_label.casefold()

        if label_key in seen_labels:
            findings.append(
                make_range_finding(
                    check="Clinical.TableDuplicateLabel",
                    severity="warning",
                    message=(
                        "Style guide table format: Table labels "
                        "should be unique within the document."
                    ),
                    match=caption.text,
                    paragraph=caption.paragraph,
                    range_start=caption.range_start,
                    range_end=caption.range_end,
                )
            )
        else:
            seen_labels[label_key] = caption

        label_has_letter = bool(
            re.fullmatch(
                r"\d+\.[a-z]",
                raw_label,
                flags=re.IGNORECASE,
            )
        )

        if not terminal and not label_has_letter:
            findings.append(
                make_range_finding(
                    check="Clinical.TableLabelPeriod",
                    severity="warning",
                    message=(
                        "Style guide table format: Use a period "
                        "after a numbered table label."
                    ),
                    match=caption.text,
                    paragraph=caption.paragraph,
                    range_start=caption.range_start,
                    range_end=caption.range_end,
                )
            )

        if not caption.inside_table:
            findings.append(
                make_range_finding(
                    check="Clinical.TableCaptionOutsideCell",
                    severity="warning",
                    message=(
                        "Style guide table format: Place in-text "
                        "table captions in table cells."
                    ),
                    match=caption.text,
                    paragraph=caption.paragraph,
                    range_start=caption.range_start,
                    range_end=caption.range_end,
                )
            )

    return findings


def validate_footnotes(
    footnotes: list[FootnoteRecord],
) -> list[dict]:
    """
    Validate basic table/figure footnote mechanics.

    This covers deterministic syntax only. It does not attempt to
    determine whether a note is semantically source, general,
    statistical, or lettered.
    """

    findings: list[dict] = []

    for footnote in footnotes:
        text = footnote.text.strip()

        if not is_table_footnote_like(text):
            continue

        if (
            text.lower().startswith("source")
            and not text.lower().startswith("source:")
        ):
            findings.append(
                make_range_finding(
                    check="Clinical.FootnoteSourceColon",
                    severity="warning",
                    message=(
                        "Style guide footnote format: Use "
                        "'Source:' for source information."
                    ),
                    match=text,
                    paragraph=footnote.paragraph,
                    range_start=footnote.range_start,
                    range_end=footnote.range_end,
                )
            )

        if re.search(
            r"\b[a-z],\s+[a-z]\b",
            text,
            flags=re.IGNORECASE,
        ):
            findings.append(
                make_range_finding(
                    check="Clinical.FootnoteDesignatorSpacing",
                    severity="warning",
                    message=(
                        "Style guide footnote format: Separate "
                        "multiple designators with commas and no spaces."
                    ),
                    match=text,
                    paragraph=footnote.paragraph,
                    range_start=footnote.range_start,
                    range_end=footnote.range_end,
                )
            )

        if (
            re.match(
                r"^[*†]\s+",
                text,
            )
            and not re.match(
                r"^[*†]\s+p\s*[<=>]",
                text,
                flags=re.IGNORECASE,
            )
        ):
            findings.append(
                make_range_finding(
                    check="Clinical.FootnoteSymbolDesignator",
                    severity="warning",
                    message=(
                        "Style guide footnote format: Do not use "
                        "symbol footnote designators except for "
                        "statistical notes or approved exceptions."
                    ),
                    match=text,
                    paragraph=footnote.paragraph,
                    range_start=footnote.range_start,
                    range_end=footnote.range_end,
                )
            )

        if not text.endswith("."):
            findings.append(
                make_range_finding(
                    check="Clinical.FootnoteEndPunctuation",
                    severity="warning",
                    message=(
                        "Style guide footnote format: End each "
                        "footnote with a period."
                    ),
                    match=text,
                    paragraph=footnote.paragraph,
                    range_start=footnote.range_start,
                    range_end=footnote.range_end,
                )
            )

    return findings
