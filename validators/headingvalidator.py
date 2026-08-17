from __future__ import annotations

import re
from typing import Any

from validators.abbreviationvalidator import ParagraphRecord, make_finding


WORD_PATTERN = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)*")
UNIT_ABBREVIATIONS = {"µg", "ug", "mg", "g", "kg", "ng", "pg", "ml", "l", "dl", "mm", "cm", "m", "km", "min", "h", "s"}

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
    heading_terms: dict[str, set[str]] | None = None,
) -> list[dict]:
    """Review heading capitalization while respecting Word caps formatting."""
    if not paragraph.is_heading:
        return []
    heading_terms = heading_terms or {"acronym_exemptions": set(), "title_case_exemptions": set()}

    words = list(WORD_PATTERN.finditer(text))
    if not words:
        return []

    alpha_text = "".join(match.group(0) for match in words)
    if alpha_text.isupper():
        if text.strip().casefold() in heading_terms["acronym_exemptions"]:
            return []
        if paragraph.heading_level == 1:
            return []
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
            elif (
                normalized in heading_terms["title_case_exemptions"]
            ):
                continue
            elif (
                not should_be_minor
                and normalized not in UNIT_ABBREVIATIONS
                and piece[0].islower()
            ):
                findings.append(
                    make_heading_finding(
                        "Clinical.HeadingTitleCase",
                        "Style guide headings: Capitalize major words and each applicable part of a hyphenated compound.",
                        piece,
                        paragraph,
                    )
                )
    return findings
