from __future__ import annotations

import re
from collections.abc import Callable

from validators.abbreviationvalidator import (
    ParagraphRecord,
    make_finding,
)


FormatLookup = Callable[[int, int], dict[str, bool]]


ITALIC_REQUIRED_PATTERNS = [
    (
        re.compile(
            r"\bStaphylococcus aureus\b"
        ),
        "Scientific species name",
    ),
    (
        re.compile(
            r"\bS aureus\b"
        ),
        "Abbreviated scientific species name",
    ),
    (
        re.compile(
            r"\b(?:cis|trans)-(?=[A-Za-z])"
        ),
        "Chemical isomer prefix",
    ),
    (
        re.compile(
            r"\([RS]\)-(?=[A-Za-z])"
        ),
        "Chemical chirality prefix",
    ),
]


ROMAN_REQUIRED_PATTERNS = [
    re.compile(r"\bin vitro\b"),
    re.compile(r"\bin vivo\b"),
    re.compile(r"\ba priori\b"),
    re.compile(r"\bad hoc\b"),
    re.compile(r"\bpost hoc\b"),
    re.compile(r"\bet al\b"),
]


RADIOLABEL_PATTERN = re.compile(
    r"\[(?P<isotope>\d+)(?P<element>[A-Za-z]{1,3})\]"
    r"(?P<compound>[A-Za-z0-9-]+)"
)


RADIOLABEL_SPACING_PATTERN = re.compile(
    r"\[(?P<isotope>\d+)\s+(?P<element>[A-Za-z]{1,3})\]"
    r"\s+(?P<compound>[A-Za-z0-9-]+)"
)


RADIOLABEL_HYPHEN_PATTERN = re.compile(
    r"\[(?P<isotope>\d+)(?P<element>[A-Za-z]{1,3})\]"
    r"-(?P<compound>[A-Za-z0-9-]+)"
)


def validate_typography_paragraph(
    paragraph: ParagraphRecord,
    offset_preserving_text: str,
    get_format: FormatLookup,
) -> list[dict]:
    """
    Validate known typography requirements for one paragraph.

    offset_preserving_text must retain one character for every Word
    character so regex offsets can be mapped back to Word ranges.
    """

    findings: list[dict] = []

    for pattern, label in ITALIC_REQUIRED_PATTERNS:
        for match in pattern.finditer(offset_preserving_text):
            format_state = get_format(
                match.start(),
                match.end(),
            )

            if not format_state.get("italic", False):
                findings.append(
                    make_finding(
                        check="Clinical.ItalicRequired",
                        severity="warning",
                        message=(
                            f"Style guide typography: Italicize "
                            f"this {label.lower()}."
                        ),
                        match=match.group(0),
                        paragraph=paragraph,
                    )
                )

    for pattern in ROMAN_REQUIRED_PATTERNS:
        for match in pattern.finditer(offset_preserving_text):
            format_state = get_format(
                match.start(),
                match.end(),
            )

            if format_state.get("italic", False):
                findings.append(
                    make_finding(
                        check="Clinical.RomanRequired",
                        severity="warning",
                        message=(
                            "Style guide typography: Do not italicize "
                            "this Latin expression."
                        ),
                        match=match.group(0),
                        paragraph=paragraph,
                    )
                )

    for match in RADIOLABEL_PATTERN.finditer(
        offset_preserving_text
    ):
        isotope_start = (
            match.start()
            + match.start("isotope")
        )

        isotope_end = (
            match.start()
            + match.end("isotope")
        )

        isotope_format = get_format(
            isotope_start,
            isotope_end,
        )

        if not isotope_format.get("superscript", False):
            findings.append(
                make_finding(
                    check="Clinical.RadiolabelSuperscript",
                    severity="warning",
                    message=(
                        "Style guide radiolabel format: Superscript "
                        "the isotope atomic number."
                    ),
                    match=match.group(0),
                    paragraph=paragraph,
                )
            )

    for pattern in [
        RADIOLABEL_SPACING_PATTERN,
        RADIOLABEL_HYPHEN_PATTERN,
    ]:
        for match in pattern.finditer(
            offset_preserving_text
        ):
            findings.append(
                make_finding(
                    check="Clinical.RadiolabelSpacing",
                    severity="warning",
                    message=(
                        "Style guide radiolabel format: Do not use "
                        "spaces or hyphens between the radiolabel "
                        "and compound name."
                    ),
                    match=match.group(0),
                    paragraph=paragraph,
                )
            )

    return findings

UNIT_NONBREAKING_SPACE_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])"
    r"\d+(?:\.\d+)? "
    r"(?:µg|ug|mg|g|kg|ng|pg|mL|L|dL|mm|cm|m|km|min|h|s|"
    r"day|days|week|weeks|month|months|year|years)\b"
)


def validate_unit_nonbreaking_spaces(
    paragraph: ParagraphRecord,
    raw_text: str,
) -> list[dict]:
    """Require nonbreaking spaces between numeric values and units in body text."""
    if paragraph.content_zone != "body_narrative":
        return []

    findings: list[dict] = []

    for match in UNIT_NONBREAKING_SPACE_PATTERN.finditer(raw_text):
        findings.append(
            make_finding(
                check="Clinical.UnitNonbreakingSpace",
                severity="warning",
                message=(
                    "Style guide units: Use a nonbreaking space between a "
                    "numeric value and its unit in body text."
                ),
                match=match.group(0),
                paragraph=paragraph,
            )
        )

    return findings

