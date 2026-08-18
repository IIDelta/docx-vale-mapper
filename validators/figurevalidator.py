"""
Purpose:
    Apply verified safe auto-fixes to copied Word documents.

Inputs:
    Source/output paths, verified auto-fix plan, protected field ranges.

Outputs:
    Modified output DOCX and auto-fix execution artifact.

Must not:
    Modify source DOCX.
    Apply unverified fixes.
    Apply report-only or disabled rules.
    Replace broad Word ranges without exact verification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from validators.abbreviationvalidator import (
    ParagraphRecord,
)
from validators.captionfootnotevalidator import (
    CaptionRecord,
    make_range_finding,
)


FIGURE_LABEL_PATTERN = re.compile(
    r"^\s*Figure\s+"
    r"(?P<label>\d+(?:\.[a-z])?)"
    r"(?P<terminal>\.)?",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class FigureRecord:
    """One detected Word figure/image anchor."""

    figure_index: int
    position: int
    paragraph: ParagraphRecord


def validate_figures(
    captions: list[CaptionRecord],
    figures: list[FigureRecord],
) -> list[dict]:
    """
    Validate figure captions, numbering, title placement, and
    visual-review requirements.
    """

    findings: list[dict] = []

    figure_captions = [
        caption
        for caption in captions
        if caption.kind == "Figure"
    ]

    seen_labels: dict[str, CaptionRecord] = {}

    for caption in figure_captions:
        label_match = FIGURE_LABEL_PATTERN.match(
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
                    check="Clinical.FigureDuplicateLabel",
                    severity="warning",
                    message=(
                        "Style guide figure format: Figure labels "
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
                    check="Clinical.FigureLabelPeriod",
                    severity="warning",
                    message=(
                        "Style guide figure format: Use a period "
                        "after a numbered figure label."
                    ),
                    match=caption.text,
                    paragraph=caption.paragraph,
                    range_start=caption.range_start,
                    range_end=caption.range_end,
                )
            )

    for figure in figures:
        captions_before = [
            caption
            for caption in figure_captions
            if (
                caption.range_end <= figure.position
                and figure.position - caption.range_end <= 1200
            )
        ]

        captions_after = [
            caption
            for caption in figure_captions
            if (
                caption.range_start >= figure.position
                and caption.range_start - figure.position <= 1200
            )
        ]

        caption_before = (
            max(
                captions_before,
                key=lambda caption: caption.range_end,
            )
            if captions_before
            else None
        )

        caption_after = (
            min(
                captions_after,
                key=lambda caption: caption.range_start,
            )
            if captions_after
            else None
        )

        if caption_before is None and caption_after is not None:
            findings.append(
                make_range_finding(
                    check="Clinical.FigureTitleBelow",
                    severity="warning",
                    message=(
                        "Style guide figure format: Place figure "
                        "titles above figures."
                    ),
                    match=caption_after.text,
                    paragraph=caption_after.paragraph,
                    range_start=caption_after.range_start,
                    range_end=caption_after.range_end,
                )
            )

        if caption_before is None and caption_after is None:
            findings.append(
                make_range_finding(
                    check="Clinical.FigureCaptionMissing",
                    severity="warning",
                    message=(
                        "Style guide figure format: Add a figure "
                        "title above the figure."
                    ),
                    match="Figure",
                    paragraph=figure.paragraph,
                    range_start=figure.paragraph.range_start,
                    range_end=figure.paragraph.range_end,
                )
            )

        review_target = (
            caption_before
            or caption_after
        )

        if review_target is not None:
            findings.append(
                make_range_finding(
                    check="Clinical.FigureVisualReview",
                    severity="warning",
                    message=(
                        "Style guide figure review: Verify that the "
                        "figure is scalable without pixel distortion "
                        "and that annotations are overlaid on the image."
                    ),
                    match=review_target.text,
                    paragraph=review_target.paragraph,
                    range_start=review_target.range_start,
                    range_end=review_target.range_end,
                )
            )
        else:
            findings.append(
                make_range_finding(
                    check="Clinical.FigureVisualReview",
                    severity="warning",
                    message=(
                        "Style guide figure review: Verify that the "
                        "figure is scalable without pixel distortion "
                        "and that annotations are overlaid on the image."
                    ),
                    match="Figure",
                    paragraph=figure.paragraph,
                    range_start=figure.paragraph.range_start,
                    range_end=figure.paragraph.range_end,
                )
            )

    findings.extend(
        validate_figure_label_sequence(
            captions=figure_captions,
        )
    )
    return findings


def validate_figure_label_sequence(
    captions: list[CaptionRecord],
) -> list[dict]:
    """Flag gaps or reversals in numeric figure labels per section."""
    grouped: dict[str, list[tuple[int, CaptionRecord]]] = {}

    for position, caption in enumerate(captions):
        label_match = FIGURE_LABEL_PATTERN.match(caption.text)
        if label_match is None:
            continue
        raw_label = label_match.group("label")
        if not raw_label.isdigit():
            # Figure 5.a is a subdivision rather than a sequence position.
            continue
        section_key = (
            caption.paragraph.section_context.strip().casefold()
            or "__document__"
        )
        grouped.setdefault(section_key, []).append((position, caption))

    findings: list[dict] = []
    for section_captions in grouped.values():
        previous_number: int | None = None
        for _, caption in sorted(
            section_captions,
            key=lambda item: (item[1].range_start, item[0]),
        ):
            label_match = FIGURE_LABEL_PATTERN.match(caption.text)
            if label_match is None:
                continue
            current_number = int(label_match.group("label"))
            if (
                previous_number is not None
                and current_number != previous_number + 1
            ):
                findings.append(
                    make_range_finding(
                        check="Clinical.FigureLabelSequence",
                        severity="warning",
                        message=(
                            "Style guide figure format: Number figure "
                            "labels consecutively within each document "
                            "section."
                        ),
                        match=caption.text,
                        paragraph=caption.paragraph,
                        range_start=caption.range_start,
                        range_end=caption.range_end,
                    )
                )
            previous_number = current_number

    return findings
