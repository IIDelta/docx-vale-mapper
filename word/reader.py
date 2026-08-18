"""
Purpose:
    Extract normalized Word paragraphs and preserve audit-relevant location data.

Inputs:
    Open Word COM document.

Outputs:
    Vale input payload, line/range maps, ParagraphRecord collection.

Must not:
    Insert comments.
    Apply auto-fixes.
    Write output DOCX files.
"""

import re

from validators.abbreviationvalidator import (
    ParagraphRecord,
    clean_text,
)
from validators.contextvalidator import (
    classify_content_zone,
    heading_level_from_style,
    is_protocol_summary_heading,
    is_reference_heading,
    is_summary_heading,
)
from validators.fieldprotection import (
    protected_field_ranges,
    ranges_overlap,
)

def vale_text_with_offset(
    raw_text: str,
) -> tuple[str, int]:
    """
    Produce Vale input text while preserving Word character offsets.

    Word control characters become spaces, but internal whitespace is
    not collapsed. This keeps Vale spans aligned with Word ranges.
    """

    offset_preserving_text = (
        raw_text.replace("\xa0", " ")
        .replace("\r", " ")
        .replace("\x07", " ")
        .replace("\x0b", " ")
        .replace("\n", " ")
    )

    leading_offset = len(
        offset_preserving_text
    ) - len(
        offset_preserving_text.lstrip()
    )

    vale_text = offset_preserving_text.strip()

    return vale_text, leading_offset


def build_paragraph_records(doc):
    """
    Extract body paragraphs, retain Word location metadata, and build
    the Vale batch payload and line-to-paragraph map.
    """

    batch_parts: list[str] = []
    line_to_range: dict[int, tuple[int, int]] = {}
    line_to_vale_text: dict[int, str] = {}
    paragraph_records: list[ParagraphRecord] = []

    current_line = 1
    total_paragraphs = doc.Paragraphs.Count
    protected_ranges = protected_field_ranges(doc)

    title_page_active = True

    summary_active = False
    summary_heading_level = 0

    protocol_summary_active = False
    protocol_summary_heading_level = 0

    reference_active = False

    section_context = "title_page"



    for index, paragraph in enumerate(doc.Paragraphs, start=1):
        raw_text = paragraph.Range.Text
        normalized_text = clean_text(raw_text)

        vale_text, vale_offset = vale_text_with_offset(
            raw_text
        )

        if not normalized_text or not vale_text:
            continue

        try:
            style_name = paragraph.Style.NameLocal
        except Exception:
            style_name = ""

        try:
            list_format = paragraph.Range.ListFormat

            list_marker = list_format.ListString

            if not list_marker:
                list_type = list_format.ListType

                if list_type not in (0, None):
                    list_marker = (
                        f"word_list_{list_type}"
                    )

        except Exception:
            list_marker = ""

        heading_level = heading_level_from_style(
            style_name
        )

        is_heading = heading_level > 0

        try:
            is_in_table = bool(
                paragraph.Range.Information(12)
            )
        except Exception:
            try:
                is_in_table = bool(
                    paragraph.Range.Tables.Count
                )
            except Exception:
                is_in_table = False

        if is_summary_heading(normalized_text):
            summary_active = True

            summary_heading_level = (
                heading_level or 1
            )

            section_context = "summary_of_changes"

        elif (
            summary_active
            and is_heading
            and heading_level > 0
            and heading_level <= summary_heading_level
        ):
            summary_active = False
            section_context = "body_narrative"

        if is_protocol_summary_heading(normalized_text):
            protocol_summary_active = True

            protocol_summary_heading_level = (
                heading_level or 1
            )

            section_context = "protocol_summary"

        elif (
            protocol_summary_active
            and is_heading
            and heading_level > 0
            and heading_level
            <= protocol_summary_heading_level
        ):
            protocol_summary_active = False
            section_context = "body_narrative"

        if is_reference_heading(normalized_text):
            reference_active = True
            section_context = "reference"

        elif (
            is_heading
            and not summary_active
            and not protocol_summary_active
            and not is_reference_heading(normalized_text)
        ):
            reference_active = False

        content_zone = classify_content_zone(
            text=normalized_text,
            style_name=style_name,
            is_in_table=is_in_table,
            list_marker=list_marker,
            title_page_active=title_page_active,
            summary_active=summary_active,
            protocol_summary_active=protocol_summary_active,
            reference_active=reference_active,
        )


        try:
            paragraph_range = paragraph.Range.Duplicate
            paragraph_start = int(paragraph_range.Start)
            paragraph_end = int(paragraph_range.End)
        except Exception as paragraph_range_error:
            print(
                "Skipping unavailable Word paragraph "
                f"{index}: {paragraph_range_error}"
            )
            continue

        has_protected_field = ranges_overlap(
            paragraph_start,
            paragraph_end,
            protected_ranges,
        )
        record = ParagraphRecord(
            index=index,
            line=current_line,
            text=normalized_text,
            style_name=style_name,
            range_start=paragraph_start,
            range_end=paragraph_end,
            list_marker=list_marker,
            is_in_table=is_in_table,
            is_heading=is_heading,
            heading_level=heading_level,
            section_context=section_context,
            content_zone=content_zone,
            has_protected_field=has_protected_field,
        )

        paragraph_records.append(record)
        line_to_range[current_line] = (
            paragraph_start + vale_offset,
            paragraph_start
            + vale_offset
            + len(vale_text),
        )

        if is_protocol_summary_heading(
            normalized_text
        ):
            title_page_active = False



        batch_parts.append(vale_text)


        current_line += 2

    batch_payload = "\n\n".join(batch_parts)

    return (
        batch_payload,
        line_to_range,
        line_to_vale_text,
        paragraph_records,
        total_paragraphs,
    )

