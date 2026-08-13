from __future__ import annotations

import re
from dataclasses import dataclass

from validators.abbreviationvalidator import (
    ParagraphRecord,
    make_finding,
)


APPENDIX_HEADING_PATTERN = re.compile(
    r"^\s*Appendix\s+(?P<letter>[A-Z])\b",
    flags=re.IGNORECASE,
)


ELEMENT_LABEL_PATTERN = re.compile(
    r"^\s*(?P<kind>Table|Figure)\s+"
    r"(?P<label>(?:[A-Z]-)?\d+(?:\.[a-z])?)",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class AppendixElementRecord:
    """One table or figure label found in appendix content."""

    kind: str
    label: str
    text: str
    appendix_letter: str
    paragraph: ParagraphRecord
    range_start: int = 0
    range_end: int = 0


def find_appendix_context(
    paragraphs: list[ParagraphRecord],
) -> dict[int, str]:
    """
    Map each paragraph index to its current Appendix letter.

    Only paragraphs after an Appendix A/B/C heading are assigned an
    appendix context.
    """

    context: dict[int, str] = {}
    current_letter = ""

    for paragraph in paragraphs:
        heading_match = APPENDIX_HEADING_PATTERN.match(
            paragraph.text
        )

        if heading_match:
            current_letter = heading_match.group(
                "letter"
            ).upper()

        if current_letter:
            context[paragraph.index] = current_letter

    return context


def validate_appendix_elements(
    elements: list[AppendixElementRecord],
) -> list[dict]:
    """
    Validate appendix table/figure prefixes and numeric sequences.
    """

    findings: list[dict] = []

    sequences: dict[
        tuple[str, str],
        list[tuple[int, AppendixElementRecord]],
    ] = {}

    for element in elements:
        label_match = re.match(
            r"(?P<prefix>[A-Z])-"
            r"(?P<number>\d+)",
            element.label,
            flags=re.IGNORECASE,
        )

        if label_match is None:
            findings.append(
                make_finding(
                    check="Clinical.AppendixElementPrefix",
                    severity="warning",
                    message=(
                        "Style guide appendix format: Use appendix "
                        f"labels such as {element.kind} "
                        f"{element.appendix_letter}-1."
                    ),
                    match=element.text,
                    paragraph=element.paragraph,
                )
            )
            continue

        prefix = label_match.group(
            "prefix"
        ).upper()

        number = int(
            label_match.group("number")
        )

        if prefix != element.appendix_letter:
            findings.append(
                make_finding(
                    check="Clinical.AppendixElementPrefix",
                    severity="warning",
                    message=(
                        "Style guide appendix format: Use the "
                        "current appendix letter in table and figure "
                        "labels."
                    ),
                    match=element.text,
                    paragraph=element.paragraph,
                )
            )

        sequences.setdefault(
            (
                element.appendix_letter,
                element.kind,
            ),
            [],
        ).append(
            (
                number,
                element,
            )
        )

    for (
        appendix_letter,
        kind,
    ), numbered_elements in sequences.items():
        ordered_elements = sorted(
            numbered_elements,
            key=lambda item: item[0],
        )

        observed_numbers = [
            number
            for number, _ in ordered_elements
        ]

        expected_numbers = list(
            range(
                1,
                len(observed_numbers) + 1,
            )
        )

        if observed_numbers != expected_numbers:
            target_element = ordered_elements[0][1]

            findings.append(
                make_finding(
                    check="Clinical.AppendixElementSequence",
                    severity="warning",
                    message=(
                        "Style guide appendix format: Number "
                        f"{kind.lower()}s consecutively within "
                        f"Appendix {appendix_letter}."
                    ),
                    match=", ".join(
                        element.text
                        for _, element in ordered_elements
                    ),
                    paragraph=target_element.paragraph,
                )
            )

    return findings
