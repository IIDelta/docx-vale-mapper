from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


LIST_HEADING_PATTERNS = (
    "LIST OF ABBREVIATIONS",
    "LIST OF ABBREVIATIONS AND DEFINITION OF TERMS",
    "ABBREVIATIONS",
)


@dataclass(frozen=True)
class ParagraphRecord:
    """A Word paragraph normalized for structural style validation."""

    index: int
    line: int
    text: str
    style_name: str = ""
    range_start: int = 0
    range_end: int = 0
    list_marker: str = ""
    is_in_table: bool = False
    is_heading: bool = False
    heading_level: int = 0
    section_context: str = ""
    content_zone: str = "body_narrative"


@dataclass(frozen=True)
class AbbreviationEntry:
    """One abbreviation-definition entry from a List of Abbreviations."""

    abbreviation: str
    definition: str
    source_label: str


def load_policy(policy_path: Path) -> dict[str, Any]:
    """Load the project abbreviation policy registry."""

    with policy_path.open(encoding="utf-8") as input_file:
        return json.load(input_file)


def normalize_abbreviation(value: str) -> str:
    """Normalize an abbreviation for duplicate and ordering comparisons."""

    return re.sub(r"\s+", " ", value.strip()).casefold()

def abbreviation_is_listed(
    normalized_abbreviation: str,
    listed_abbreviations: set[str],
) -> bool:
    """
    Return True when an abbreviation is listed directly or through a
    simple singular/plural alias.

    Examples:
        AE  covers AEs
        PRO covers PROs
        SAE covers SAEs
    """

    if normalized_abbreviation in listed_abbreviations:
        return True

    if (
        normalized_abbreviation.endswith("s")
        and normalized_abbreviation[:-1]
        in listed_abbreviations
    ):
        return True

    if (
        normalized_abbreviation + "s"
        in listed_abbreviations
    ):
        return True

    return False

def clean_text(value: str) -> str:
    """
    Normalize Word/COM text while preserving token boundaries.

    Word paragraphs and table cells can contain carriage returns,
    cell-end markers, manual line breaks, and line feeds. These must
    become spaces rather than being deleted; otherwise adjacent tokens
    can merge, for example, XYZ + EOS becoming XYZEOS.
    """

    normalized_value = (
        value.replace("\r", " ")
        .replace("\x07", " ")
        .replace("\x0b", " ")
        .replace("\n", " ")
    )

    return re.sub(
        r"\s+",
        " ",
        normalized_value,
    ).strip()


def find_list_heading(
    paragraphs: list[ParagraphRecord],
) -> ParagraphRecord | None:
    """Return the first paragraph that identifies a List of Abbreviations."""

    for paragraph in paragraphs:
        heading = paragraph.text.strip().upper()

        if heading in LIST_HEADING_PATTERNS:
            return paragraph

    return None


def abbreviation_sort_key(abbreviation: str) -> tuple[int, str]:
    """
    Sort numeric-leading abbreviations before alphabetic-leading entries.

    Example:
        9vHPV
        ACS
        AE
        BP
    """

    cleaned = abbreviation.strip()

    if not cleaned:
        return (2, "")

    category = 0 if cleaned[0].isdigit() else 1

    return (category, cleaned.casefold())


def make_finding(
    check: str,
    severity: str,
    message: str,
    match: str,
    paragraph: ParagraphRecord,
) -> dict[str, Any]:
    """Create a Vale-compatible structural finding."""

    return {
        "Check": check,
        "Severity": severity,
        "Message": message,
        "Match": match,
        "Line": paragraph.line,
        "ParagraphIndex": paragraph.index,
        "Action": {
            "Name": "",
            "Params": None,
        },
    }


def validate_abbreviation_list(
    entries: list[AbbreviationEntry],
    heading: ParagraphRecord,
) -> list[dict[str, Any]]:
    """Validate duplicates, definitions, and ordering in a list."""

    findings: list[dict[str, Any]] = []

    cleaned_entries = [
        entry
        for entry in entries
        if entry.abbreviation.strip().casefold()
        not in {"abbreviation", "abbreviations"}
    ]

    abbreviations = [
        normalize_abbreviation(entry.abbreviation)
        for entry in cleaned_entries
        if entry.abbreviation.strip()
    ]

    duplicate_counts = Counter(abbreviations)

    display_abbreviations: dict[str, str] = {}

    for entry in cleaned_entries:
        normalized = normalize_abbreviation(entry.abbreviation)

        if normalized and normalized not in display_abbreviations:
            display_abbreviations[normalized] = entry.abbreviation.strip()

    for abbreviation, count in sorted(duplicate_counts.items()):
        if count > 1:
            display_value = display_abbreviations.get(
                abbreviation,
                abbreviation,
            )

            findings.append(
                make_finding(
                    check="Clinical.AbbreviationListDuplicate",
                    severity="error",
                    message=(
                        "Takeda abbreviation list: "
                        f"'{display_value}' appears {count} times."
                    ),
                    match=display_value,
                    paragraph=heading,
                )
            )


    for entry in cleaned_entries:
        if entry.abbreviation.strip() and not entry.definition.strip():
            findings.append(
                make_finding(
                    check="Clinical.AbbreviationListMissingDefinition",
                    severity="error",
                    message=(
                        "Takeda abbreviation list: "
                        "Each listed abbreviation requires a definition."
                    ),
                    match=entry.abbreviation,
                    paragraph=heading,
                )
            )

    actual_order = [
        entry.abbreviation.strip()
        for entry in cleaned_entries
        if entry.abbreviation.strip()
    ]

    expected_order = sorted(actual_order, key=abbreviation_sort_key)

    if actual_order != expected_order:
        findings.append(
            make_finding(
                check="Clinical.AbbreviationListOrder",
                severity="warning",
                message=(
                    "Takeda abbreviation list: Order numeric-leading "
                    "entries before alphabetic entries, then sort "
                    "alphabetically within each group."
                ),
                match=", ".join(actual_order),
                paragraph=heading,
            )
        )

    return findings


def definition_spans(
    paragraph: ParagraphRecord,
    abbreviation: str,
    expansion: str,
) -> list[tuple[int, int]]:
    """
    Return spans for exact approved first-use definitions.

    Example accepted text:
        adverse event (AE)
    """

    pattern = re.compile(
        rf"\b{re.escape(expansion)}\s+\(\s*{re.escape(abbreviation)}\s*\)",
        flags=re.IGNORECASE,
    )

    return [match.span() for match in pattern.finditer(paragraph.text)]


def usage_spans(
    paragraph: ParagraphRecord,
    abbreviation: str,
) -> list[tuple[int, int]]:
    """Return spans for independent abbreviation use."""

    pattern = re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(abbreviation)}(?![A-Za-z0-9])"
    )

    return [match.span() for match in pattern.finditer(paragraph.text)]


def span_is_inside(
    candidate_span: tuple[int, int],
    container_spans: list[tuple[int, int]],
) -> bool:
    """Return True when a candidate lies within a definition expression."""

    start, end = candidate_span

    return any(
        start >= container_start and end <= container_end
        for container_start, container_end in container_spans
    )


def validate_first_use(
    paragraphs: list[ParagraphRecord],
    policy: dict[str, Any],
    has_abbreviation_list: bool,
    abbreviation_entries: list[AbbreviationEntry],
    list_heading: ParagraphRecord | None,
) -> list[dict[str, Any]]:
    """
    Validate tracked first-use behavior.

    Documents with a List of Abbreviations:
      - tracked abbreviations used in text should appear in the list;
      - inline first-use definitions are flagged as redundant.

    Documents without a List of Abbreviations:
      - tracked abbreviations must be defined before ordinary use.
    """

    findings: list[dict[str, Any]] = []

    tracked = policy.get("tracked_abbreviations", {})
    never_expand = {
        normalize_abbreviation(value)
        for value in policy.get("never_expand", [])
    }

    listed_abbreviations = {
        normalize_abbreviation(entry.abbreviation)
        for entry in abbreviation_entries
        if entry.abbreviation.strip()
    }

    for abbreviation, metadata in tracked.items():
        normalized_abbreviation = normalize_abbreviation(abbreviation)

        if normalized_abbreviation in never_expand:
            continue

        expansion = metadata["expansion"]

        definitions: list[tuple[ParagraphRecord, tuple[int, int]]] = []
        ordinary_uses: list[tuple[ParagraphRecord, tuple[int, int]]] = []

        for paragraph in paragraphs:
            current_definition_spans = definition_spans(
                paragraph,
                abbreviation,
                expansion,
            )

            for current_span in current_definition_spans:
                definitions.append((paragraph, current_span))

            for current_span in usage_spans(paragraph, abbreviation):
                if not span_is_inside(
                    current_span,
                    current_definition_spans,
                ):
                    ordinary_uses.append((paragraph, current_span))

        abbreviation_appears = bool(definitions or ordinary_uses)

        if not abbreviation_appears:
            continue

        if has_abbreviation_list:
            if not abbreviation_is_listed(
                normalized_abbreviation,
                listed_abbreviations,
            ):
                target = ordinary_uses[0][0] if ordinary_uses else definitions[0][0]

                findings.append(
                    make_finding(
                        check="Clinical.AbbreviationMissingFromList",
                        severity="warning",
                        message=(
                            "Takeda abbreviation rule: "
                            f"'{abbreviation}' is used in the document but "
                            "is absent from the List of Abbreviations."
                        ),
                        match=abbreviation,
                        paragraph=target,
                    )
                )

            if definitions:
                for definition_paragraph, _ in definitions:
                    findings.append(
                        make_finding(
                            check="Clinical.AbbreviationRedefinedInText",
                            severity="warning",
                            message=(
                                "Takeda abbreviation rule: "
                                f"'{abbreviation}' is defined in running "
                                "text even though the document contains "
                                "a List of Abbreviations."
                            ),
                            match=f"{expansion} ({abbreviation})",
                            paragraph=definition_paragraph,
                        )
                    )

        else:
            if not definitions:
                target = ordinary_uses[0][0]

                findings.append(
                    make_finding(
                        check="Clinical.AbbreviationUndefinedAtFirstUse",
                        severity="warning",
                        message=(
                            "Takeda abbreviation rule: "
                            f"Define '{abbreviation}' at first use as "
                            f"'{expansion} ({abbreviation})'."
                        ),
                        match=abbreviation,
                        paragraph=target,
                    )
                )

                continue

            first_definition_index = min(
                paragraph.index
                for paragraph, _ in definitions
            )

            first_use_index = min(
                paragraph.index
                for paragraph, _ in ordinary_uses
            ) if ordinary_uses else first_definition_index

            if first_use_index < first_definition_index:
                target = next(
                    paragraph
                    for paragraph, _ in ordinary_uses
                    if paragraph.index == first_use_index
                )

                findings.append(
                    make_finding(
                        check="Clinical.AbbreviationUndefinedAtFirstUse",
                        severity="warning",
                        message=(
                            "Takeda abbreviation rule: "
                            f"'{abbreviation}' appears before its first "
                            f"definition, '{expansion} ({abbreviation})'."
                        ),
                        match=abbreviation,
                        paragraph=target,
                    )
                )

    if has_abbreviation_list and list_heading is not None:
        findings.extend(
            validate_abbreviation_list(
                entries=abbreviation_entries,
                heading=list_heading,
            )
        )

    return findings


def validate_deprecated_terms(
    paragraphs: list[ParagraphRecord],
    deprecated_terms: dict[str, str],
) -> list[dict[str, Any]]:
    """
    Flag reviewed deprecated abbreviations.

    Deprecated terms are warned about, but never automatically replaced
    in Word because surrounding sentence grammar and document context
    may require review.
    """

    findings: list[dict[str, Any]] = []

    for token, replacement_token in deprecated_terms.items():
        for paragraph in paragraphs:
            for _ in usage_spans(paragraph, token):
                findings.append(
                    make_finding(
                        check="Clinical.AbbreviationDeprecated",
                        severity="warning",
                        message=(
                            f"Abbreviation '{token}' is deprecated. "
                            f"Use '{replacement_token}' instead."
                        ),
                        match=token,
                        paragraph=paragraph,
                    )
                )

    return findings
