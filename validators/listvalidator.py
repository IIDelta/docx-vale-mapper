from __future__ import annotations

import re
from typing import Iterable

from validators.abbreviationvalidator import (
    ParagraphRecord,
    make_finding,
)

MANUAL_LIST_MARKER_PATTERN = re.compile(
    r"^\s*(?:[•◦▪▫‣⁃]|[-–—]|\(?\d+[.)]|\(?[A-Za-z][.)])\s+"
)

def is_list_item(
    paragraph: ParagraphRecord,
) -> bool:
    """
    Return True for a true Word list item or a manually typed marker.

    Supported manual markers include:
      • Bullet characters
      • Dash bullets
      • 1. Numbered items
      • 1) Numbered items
      • a. Lettered items
      • a) Lettered items
    """

    if paragraph.list_marker.strip():
        return True

    return bool(
        MANUAL_LIST_MARKER_PATTERN.match(
            paragraph.text
        )
    )


def find_list_groups(
    paragraphs: list[ParagraphRecord],
) -> list[list[ParagraphRecord]]:
    """Return contiguous groups of Word list-item paragraphs."""

    groups: list[list[ParagraphRecord]] = []
    current_group: list[ParagraphRecord] = []

    for paragraph in paragraphs:
        if is_list_item(paragraph):
            current_group.append(paragraph)
            continue

        if current_group:
            groups.append(current_group)
            current_group = []

    if current_group:
        groups.append(current_group)

    return groups


def first_letter(
    text: str,
) -> str:
    """Return the first alphabetical character in text, if present."""

    match = re.search(
        r"[A-Za-z]",
        text,
    )

    return match.group(0) if match else ""


def validate_list_structure(
    paragraphs: list[ParagraphRecord],
) -> list[dict]:
    """
    Validate safe list-structure rules.

    Checks:
      - list introduction should end with a colon;
      - vertical lists should contain more than one item;
      - each list item should begin with a capital letter;
      - each list item should end with a period.
    """

    findings: list[dict] = []

    paragraph_positions = {
        paragraph.index: position
        for position, paragraph in enumerate(paragraphs)
    }

    for group in find_list_groups(paragraphs):
        first_item = group[0]

        first_position = paragraph_positions[
            first_item.index
        ]

        previous_paragraph = (
            paragraphs[first_position - 1]
            if first_position > 0
            else None
        )

        if (
            previous_paragraph is not None
            and not is_list_item(previous_paragraph)
            and previous_paragraph.text.strip()
            and not previous_paragraph.text.rstrip().endswith(":")
        ):
            findings.append(
                make_finding(
                    check="Clinical.ListIntroductionColon",
                    severity="warning",
                    message=(
                        "Style guide list format: Introduce a "
                        "vertical list with a complete clause ending "
                        "in a colon."
                    ),
                    match=previous_paragraph.text,
                    paragraph=previous_paragraph,
                )
            )

        if len(group) == 1:
            findings.append(
                make_finding(
                    check="Clinical.SingleItemList",
                    severity="warning",
                    message=(
                        "Style guide list format: Do not use a "
                        "vertical list for only one item."
                    ),
                    match=first_item.text,
                    paragraph=first_item,
                )
            )

        for item in group:
            item_text = item.text.strip()

            letter = first_letter(item_text)

            if letter and letter.islower():
                findings.append(
                    make_finding(
                        check="Clinical.ListItemCapitalization",
                        severity="warning",
                        message=(
                            "Style guide list format: Start each "
                            "list item with a capital letter."
                        ),
                        match=item_text,
                        paragraph=item,
                    )
                )

            if item_text and not item_text.endswith("."):
                findings.append(
                    make_finding(
                        check="Clinical.ListItemEndPunctuation",
                        severity="warning",
                        message=(
                            "Style guide list format: End each "
                            "vertical list item with a period."
                        ),
                        match=item_text,
                        paragraph=item,
                    )
                )

    return findings
