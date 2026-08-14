import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from typing import Any
import threading
import pythoncom
import win32com.client
import subprocess
import json
import os
import sys
import re
import traceback
from pathlib import Path
from validators.abbreviationvalidator import (
    AbbreviationEntry,
    ParagraphRecord,
    clean_text,
    find_list_heading,
    normalize_abbreviation,
    validate_deprecated_terms,
    validate_first_use,
)
from abbreviations.auditbridge import build_effective_policy
from validators.findingmerge import merge_audit_findings
from abbreviations.candidatefinder import (
    TextRecord,
    discover_candidates,
    write_report as write_candidate_report,
)
from abbreviations.reviewwindow import open_review_window
from abbreviations.reportpaths import (
    candidate_report_path_for_document,
)
from validators.listvalidator import (
    validate_list_structure,
)
from validators.typographyvalidator import (
    validate_typography_paragraph,
)
from validators.referencevalidator import (
    validate_active_external_link,
    validate_reference_text,
)
from validators.tablevalidator import (
    TableCellRecord,
    validate_table_cells,
)
from validators.captionfootnotevalidator import (
    CaptionRecord,
    FootnoteRecord,
    validate_captions,
    validate_footnotes,
)
from validators.captionfootnotevalidator import (
    CaptionRecord,
)
from validators.figurevalidator import (
    FigureRecord,
    validate_figures,
)
from validators.appendixvalidator import (
    AppendixElementRecord,
    ELEMENT_LABEL_PATTERN,
    find_appendix_context,
    validate_appendix_elements,
)
from validators.valespan import (
    vale_span_to_word_range,
)
from validators.contextvalidator import (
    classify_content_zone,
    heading_level_from_style,
    is_protocol_summary_heading,
    is_reference_heading,
    is_summary_heading,
)
from validators.findingfilter import (
    deduplicate_findings,
    filter_findings_by_context,
)

PROJECT_ROOT = Path(__file__).resolve().parent

REGRESSION_TEST_RUNNER = PROJECT_ROOT / "tests" / "runregressiontests.py"

ABBREVIATION_POLICY_PATH = (
    PROJECT_ROOT / "config" / "abbreviationpolicy.json"
)

ABBREVIATION_DATABASE_PATH = (
    PROJECT_ROOT / "data" / "abbreviations.sqlite"
)


def run_regression_gate() -> None:
    """Run all approved Vale fixtures before auditing a live document."""

    command = [
        sys.executable,
        str(REGRESSION_TEST_RUNNER),
    ]

    audit_stage = "Running Vale"
    process = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        encoding="utf-8",
        check=False,
    )

    if process.returncode != 0:
        output = process.stdout.strip()
        errors = process.stderr.strip()

        details = "\n\n".join(
            value
            for value in [output, errors]
            if value
        )

        raise RuntimeError(
            "The Takeda Vale regression suite failed. "
            "The live-document audit was not started.\n\n"
            f"{details}"
        )


ABBREVIATION_CELL_PATTERN = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9+*'’:/.\-]{0,24}$"
)


def extract_entries_from_table(
    table,
    table_index: int,
) -> list[AbbreviationEntry]:
    """
    Extract potential abbreviation-definition pairs from a Word table.

    The first nonempty cell is treated as the abbreviation, and the
    second nonempty cell is treated as its definition. This handles
    ordinary two-column tables and many merged-cell layouts.
    """

    entries: list[AbbreviationEntry] = []

    for row_index in range(1, table.Rows.Count + 1):
        try:
            row = table.Rows.Item(row_index)

        except Exception as table_row_error:
            print(
                f"Skipping table {table_index} row traversal "
                f"because of merged cells: {table_row_error}"
            )
            break

        cell_values: list[str] = []

        try:
            cell_count = row.Cells.Count
        except Exception:
            continue

        for cell_index in range(1, cell_count + 1):
            try:
                cell_value = clean_text(
                    row.Cells.Item(cell_index).Range.Text
                )
            except Exception:
                cell_value = ""

            # Preserve blank cells. A blank second cell is meaningful because
            # it represents a missing abbreviation definition.
            cell_values.append(cell_value)

        if len(cell_values) < 2:
            continue

        abbreviation = cell_values[0].strip()
        definition = cell_values[1].strip()

        # Ignore rows that have no abbreviation in the first column.
        if not abbreviation:
            continue

        abbreviation_upper = abbreviation.upper()

        if (
            normalize_abbreviation(abbreviation) in {
                "abbreviation",
                "abbreviations",
                "term",
                "terms",
            }
            or "LIST OF ABBREVIATIONS" in abbreviation_upper
        ):
            continue

        entries.append(
            AbbreviationEntry(
                abbreviation=abbreviation,
                definition=definition,
                source_label=(
                    f"List of Abbreviations table {table_index}, "
                    f"row {row_index}"
                ),
            )
        )

    return entries


def score_abbreviation_table(
    entries: list[AbbreviationEntry],
    tracked_abbreviations: set[str],
) -> int:
    """
    Score a candidate Word table.

    High scores indicate that a table resembles a List of Abbreviations:
    - multiple short abbreviation-like first-column values;
    - populated definition cells;
    - matches to tracked abbreviations such as AE, DLT, LFT, or MedDRA.
    """

    if len(entries) < 2:
        return 0

    abbreviation_like_count = sum(
        bool(
            ABBREVIATION_CELL_PATTERN.fullmatch(
                entry.abbreviation.strip()
            )
        )
        for entry in entries
    )

    definition_count = sum(
        bool(entry.definition.strip())
        for entry in entries
    )

    tracked_match_count = sum(
        normalize_abbreviation(entry.abbreviation)
        in tracked_abbreviations
        for entry in entries
    )

    return (
        abbreviation_like_count * 10
        + definition_count * 2
        + tracked_match_count * 100
    )


def extract_abbreviation_entries_from_word(
    doc,
    heading_record: ParagraphRecord | None,
    policy: dict,
) -> list[AbbreviationEntry]:
    """
    Locate and extract the most likely List of Abbreviations table.

    Rather than using the first table after the heading, this function
    evaluates every later table and chooses the nearest high-confidence
    abbreviation-definition table.
    """

    if heading_record is None:
        return []

    tracked_abbreviations = {
        normalize_abbreviation(abbreviation)
        for abbreviation in policy.get(
            "tracked_abbreviations",
            {},
        )
    }

    candidates: list[
        tuple[int, int, int, list[AbbreviationEntry]]
    ] = []


    for table_index in range(1, doc.Tables.Count + 1):
        table = doc.Tables.Item(table_index)

        # Skip only tables that end before the List of Abbreviations heading.
        #
        # Important: a List of Abbreviations heading may be inside the same
        # Word table as its abbreviation rows. In that case, table.Range.Start
        # occurs before the heading, but table.Range.End occurs after it.
        if table.Range.End <= heading_record.range_end:
            continue


        entries = extract_entries_from_table(
            table=table,
            table_index=table_index,
        )

        score = score_abbreviation_table(
            entries=entries,
            tracked_abbreviations=tracked_abbreviations,
        )

        if score == 0:
            continue

        if (
            table.Range.Start
            <= heading_record.range_start
            <= table.Range.End
        ):
            # The heading is inside this table.
            distance_from_heading = 0
        else:
            # The table follows the heading in the document body.
            distance_from_heading = max(
                0,
                table.Range.Start - heading_record.range_end,
            )

        preview = ", ".join(
            entry.abbreviation
            for entry in entries[:10]
        )

        print(
            f"A4.2 candidate table {table_index}; "
            f"start={table.Range.Start}; "
            f"end={table.Range.End}; "
            f"score={score}; "
            f"entries={len(entries)}; "
            f"preview=[{preview}]"
        )

        candidates.append(
            (
                score,
                distance_from_heading,
                table_index,
                entries,
            )
        )

    if not candidates:
        print(
            "A4.2: List of Abbreviations heading found, "
            "but no candidate abbreviation table was extracted."
        )
        return []

    # Highest structural score wins. If scores tie, choose the table
    # nearest to the List of Abbreviations heading.
    candidates.sort(
        key=lambda candidate: (
            -candidate[0],
            candidate[1],
        )
    )

    best_score, best_distance, best_table_index, best_entries = (
        candidates[0]
    )

    preview = ", ".join(
        entry.abbreviation
        for entry in best_entries[:10]
    )

    print(
        "A4.2: Selected List of Abbreviations "
        f"table {best_table_index}; "
        f"score={best_score}; "
        f"distance={best_distance}; "
        f"entries={len(best_entries)}; "
        f"preview=[{preview}]"
    )

    return best_entries


def vale_text_with_offset(
    raw_text: str,
) -> tuple[str, int]:
    """
    Produce Vale input text while preserving Word character offsets.

    Word control characters become spaces, but internal whitespace is
    not collapsed. This keeps Vale spans aligned with Word ranges.
    """

    offset_preserving_text = (
        raw_text.replace("\r", " ")
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
    paragraph_records: list[ParagraphRecord] = []

    current_line = 1
    total_paragraphs = doc.Paragraphs.Count

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


        record = ParagraphRecord(
            index=index,
            line=current_line,
            text=normalized_text,
            style_name=style_name,
            range_start=paragraph.Range.Start,
            range_end=paragraph.Range.End,
            list_marker=list_marker,
            is_in_table=is_in_table,
            is_heading=is_heading,
            heading_level=heading_level,
            section_context=section_context,
            content_zone=content_zone,
        )

        paragraph_records.append(record)
        line_to_range[current_line] = (
            paragraph.Range.Start + vale_offset,
            paragraph.Range.Start
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
        paragraph_records,
        total_paragraphs,
    )


def add_typography_findings(
    doc,
    paragraph_records: list[ParagraphRecord],
) -> list[dict]:
    """
    Inspect actual Word formatting for typography requirements.

    Uses offset-preserving text so regex match positions align with
    the underlying Word range.
    """

    findings: list[dict] = []

    record_by_index = {
        record.index: record
        for record in paragraph_records
    }

    for paragraph_index, paragraph in enumerate(
        doc.Paragraphs,
        start=1,
    ):
        record = record_by_index.get(paragraph_index)

        if record is None:
            continue

        raw_text = paragraph.Range.Text

        offset_preserving_text = (
            raw_text.replace("\r", " ")
            .replace("\x07", " ")
            .replace("\x0b", " ")
            .replace("\n", " ")
        )

        if not offset_preserving_text.strip():
            continue

        paragraph_start = paragraph.Range.Start

        def get_format(
            start: int,
            end: int,
        ) -> dict[str, bool]:
            matched_range = doc.Range(
                paragraph_start + start,
                paragraph_start + end,
            )

            return {
                "italic": (
                    matched_range.Font.Italic == -1
                ),
                "superscript": (
                    matched_range.Font.Superscript == -1
                ),
            }

        findings.extend(
            validate_typography_paragraph(
                paragraph=record,
                offset_preserving_text=offset_preserving_text,
                get_format=get_format,
            )
        )

    return findings


def add_reference_findings(
    doc,
    paragraph_records: list[ParagraphRecord],
) -> list[dict]:
    """
    Validate raw URLs and active external Word hyperlinks.

    Raw URL text is checked in all extracted paragraphs.
    Active hyperlinks are checked through Word COM.
    """

    findings = validate_reference_text(
        paragraphs=paragraph_records,
    )

    record_by_position = sorted(
        paragraph_records,
        key=lambda record: record.range_start,
    )

    for hyperlink_index in range(
        1,
        doc.Hyperlinks.Count + 1,
    ):
        try:
            hyperlink = doc.Hyperlinks.Item(
                hyperlink_index
            )

            address = str(
                hyperlink.Address or ""
            ).strip()

            if not address.lower().startswith(
                ("http://", "https://")
            ):
                continue

            display_text = clean_text(
                hyperlink.Range.Text
            )

            # A visible raw URL is already handled by
            # Clinical.RawExternalURL. Avoid duplicate comments.
            if display_text.lower().startswith(
                ("http://", "https://", "www.")
            ):
                continue

            hyperlink_start = hyperlink.Range.Start

        except Exception as hyperlink_error:
            print(
                "Skipping unavailable Word hyperlink "
                f"{hyperlink_index}: {hyperlink_error}"
            )
            continue

        target_record = next(
            (
                record
                for record in record_by_position
                if (
                    record.range_start
                    <= hyperlink_start
                    <= record.range_end
                )
            ),
            None,
        )

        if target_record is None:
            continue

        findings.append(
            validate_active_external_link(
                paragraph=target_record,
                display_text=display_text,
                address=address,
            )
        )


    return findings


def is_schedule_table(
    table,
) -> bool:
    """
    Return True for Schedule of Activities / schedule-style tables.

    These tables are template-driven and should not receive ordinary
    data-table sentence-case or zero-value checks.
    """

    try:
        table_text = clean_text(
            table.Range.Text
        ).casefold()

    except Exception:
        return False

    schedule_markers = (
        "schedule of activities",
        "schedule of assessments",
        "visit window",
        "screening",
        "treatment period",
        "follow-up",
        "follow up",
        "cycle",
        "day",
        "week",
    )

    marker_count = sum(
        marker in table_text
        for marker in schedule_markers
    )

    return marker_count >= 2


def add_table_findings(
    doc,
    paragraph_records: list[ParagraphRecord],
) -> list[dict]:
    """
    Extract Word table cells and validate basic table formatting.
    """

    findings: list[dict] = []

    if doc.Tables.Count == 0:
        return findings

    sorted_records = sorted(
        paragraph_records,
        key=lambda record: record.range_start,
    )

    def record_for_position(
        position: int,
    ) -> ParagraphRecord | None:
        for record in sorted_records:
            if (
                record.range_start
                <= position
                <= record.range_end
            ):
                return record

        if not sorted_records:
            return None

        return min(
            sorted_records,
            key=lambda record: abs(
                record.range_start - position
            ),
        )

    cells: list[TableCellRecord] = []
    seen_cell_ranges: set[tuple[int, int]] = set()

    for table_index in range(
        1,
        doc.Tables.Count + 1,
    ):
        table = doc.Tables.Item(table_index)

        if is_schedule_table(table):
            print(
                f"Skipping schedule table {table_index} "
                "for ordinary data-table validation."
            )
            continue

        for row_index in range(
            1,
            table.Rows.Count + 1,
        ):
            try:
                row = table.Rows.Item(row_index)

            except Exception as table_row_error:
                print(
                    f"Skipping table {table_index} row traversal "
                    f"because of merged cells: {table_row_error}"
                )
                break

            try:
                cell_count = row.Cells.Count
            except Exception:
                continue

            for column_index in range(
                1,
                cell_count + 1,
            ):
                try:
                    word_cell = row.Cells.Item(
                        column_index
                    )

                    cell_text = clean_text(
                        word_cell.Range.Text
                    )

                    paragraph_record = record_for_position(
                        word_cell.Range.Start
                    )

                except Exception:
                    continue

                if (
                    not cell_text
                    or paragraph_record is None
                ):
                    continue

                range_start = word_cell.Range.Start

                range_end = max(
                    word_cell.Range.Start,
                    word_cell.Range.End - 1,
                )

                cell_key = (
                    range_start,
                    range_end,
                )

                if cell_key in seen_cell_ranges:
                    continue

                seen_cell_ranges.add(cell_key)

                cells.append(
                    TableCellRecord(
                        table_index=table_index,
                        row_index=row_index,
                        column_index=column_index,
                        text=cell_text,
                        paragraph=paragraph_record,
                        range_start=range_start,
                        range_end=range_end,
                    )
                )


    findings.extend(
        validate_table_cells(cells)
    )

    return findings


def add_caption_footnote_findings(
    doc,
    paragraph_records: list[ParagraphRecord],
) -> list[dict]:
    """
    Extract table captions and recognizable footnote text.

    Captions outside tables are detected from the closest paragraph
    immediately preceding each table. Captions inside tables and
    footnotes use exact cell ranges.
    """

    findings: list[dict] = []

    sorted_records = sorted(
        paragraph_records,
        key=lambda record: record.range_start,
    )

    def record_for_position(
        position: int,
    ) -> ParagraphRecord | None:
        for record in sorted_records:
            if (
                record.range_start
                <= position
                <= record.range_end
            ):
                return record

        if not sorted_records:
            return None

        return min(
            sorted_records,
            key=lambda record: abs(
                record.range_start - position
            ),
        )

    captions: list[CaptionRecord] = []
    footnotes: list[FootnoteRecord] = []
    seen_cell_ranges: set[tuple[int, int]] = set()

    for table_index in range(
        1,
        doc.Tables.Count + 1,
    ):
        table = doc.Tables.Item(table_index)

        if is_schedule_table(table):
            print(
                f"Skipping schedule table {table_index} "
                "for caption and footnote validation."
            )
            continue

        preceding_records = [
            record
            for record in sorted_records
            if record.range_end <= table.Range.Start
        ]


        if preceding_records:
            preceding_record = preceding_records[-1]

            if preceding_record.text.strip().lower().startswith(
                "table "
            ):
                captions.append(
                    CaptionRecord(
                        kind="Table",
                        text=preceding_record.text,
                        inside_table=False,
                        paragraph=preceding_record,
                        range_start=preceding_record.range_start,
                        range_end=preceding_record.range_end,
                    )
                )

        for row_index in range(
            1,
            table.Rows.Count + 1,
        ):
            try:
                row = table.Rows.Item(row_index)

            except Exception as table_row_error:
                print(
                    f"Skipping table {table_index} row traversal "
                    f"because of merged cells: {table_row_error}"
                )
                break

            try:
                cell_count = row.Cells.Count
            except Exception:
                continue

            for column_index in range(
                1,
                cell_count + 1,
            ):
                try:
                    word_cell = row.Cells.Item(
                        column_index
                    )


                    raw_cell_text = word_cell.Range.Text

                    cell_text = clean_text(
                        raw_cell_text
                    )

                    paragraph_record = record_for_position(
                        word_cell.Range.Start
                    )

                except Exception:
                    continue

                if (
                    not cell_text
                    or paragraph_record is None
                ):
                    continue

                range_start = word_cell.Range.Start

                range_end = max(
                    range_start,
                    word_cell.Range.End - 1,
                )

                cell_key = (
                    range_start,
                    range_end,
                )

                if cell_key in seen_cell_ranges:
                    continue

                seen_cell_ranges.add(cell_key)

                if cell_text.lower().startswith("table "):
                    captions.append(
                        CaptionRecord(
                            kind="Table",
                            text=cell_text,
                            inside_table=True,
                            paragraph=paragraph_record,
                            range_start=range_start,
                            range_end=range_end,
                        )
                    )

                for line_match in re.finditer(
                    r"[^\r\n\x07]+",
                    raw_cell_text,
                ):
                    footnote_text = clean_text(
                        line_match.group(0)
                    )

                    if not footnote_text:
                        continue

                    footnote_start = (
                        range_start
                        + line_match.start()
                    )

                    footnote_end = (
                        range_start
                        + line_match.end()
                    )

                    footnotes.append(
                        FootnoteRecord(
                            text=footnote_text,
                            paragraph=paragraph_record,
                            range_start=footnote_start,
                            range_end=footnote_end,
                        )
                    )

    findings.extend(
        validate_captions(captions)
    )

    findings.extend(
        validate_footnotes(footnotes)
    )

    return findings


def add_figure_findings(
    doc,
    paragraph_records: list[ParagraphRecord],
) -> list[dict]:
    """
    Extract figure anchors and nearby figure captions.
    """

    findings: list[dict] = []

    sorted_records = sorted(
        paragraph_records,
        key=lambda record: record.range_start,
    )

    def record_for_position(
        position: int,
    ) -> ParagraphRecord | None:
        for record in sorted_records:
            if (
                record.range_start
                <= position
                <= record.range_end
            ):
                return record

        if not sorted_records:
            return None

        return min(
            sorted_records,
            key=lambda record: abs(
                record.range_start - position
            ),
        )

    captions: list[CaptionRecord] = []
    seen_caption_ranges: set[
        tuple[int, int, str]
    ] = set()


    for record in sorted_records:
        if record.text.strip().lower().startswith(
            "figure "
        ):
            caption_key = (
                record.range_start,
                record.range_end,
                record.text.casefold(),
            )

            if caption_key in seen_caption_ranges:
                continue

            seen_caption_ranges.add(caption_key)

            captions.append(
                CaptionRecord(
                    kind="Figure",
                    text=record.text,
                    inside_table=False,
                    paragraph=record,
                    range_start=record.range_start,
                    range_end=record.range_end,
                )
            )

    figures: list[FigureRecord] = []
    seen_positions: set[int] = set()

    for inline_index in range(
        1,
        doc.InlineShapes.Count + 1,
    ):
        inline_shape = doc.InlineShapes.Item(
            inline_index
        )

        position = inline_shape.Range.Start

        if position in seen_positions:
            continue

        paragraph_record = record_for_position(
            position
        )

        if paragraph_record is None:
            continue

        seen_positions.add(position)

        figures.append(
            FigureRecord(
                figure_index=len(figures) + 1,
                position=position,
                paragraph=paragraph_record,
            )
        )

    for shape_index in range(
        1,
        doc.Shapes.Count + 1,
    ):
        shape = doc.Shapes.Item(shape_index)

        try:
            position = shape.Anchor.Start
        except Exception:
            continue

        if position in seen_positions:
            continue

        paragraph_record = record_for_position(
            position
        )

        if paragraph_record is None:
            continue

        seen_positions.add(position)

        figures.append(
            FigureRecord(
                figure_index=len(figures) + 1,
                position=position,
                paragraph=paragraph_record,
            )
        )

    findings.extend(
        validate_figures(
            captions=captions,
            figures=figures,
        )
    )

    return findings


def add_appendix_findings(
    doc,
    paragraph_records: list[ParagraphRecord],
) -> list[dict]:
    """
    Extract appendix table/figure labels from paragraphs and table cells.
    """

    findings: list[dict] = []

    appendix_context = find_appendix_context(
        paragraph_records
    )

    if not appendix_context:
        return findings

    sorted_records = sorted(
        paragraph_records,
        key=lambda record: record.range_start,
    )

    def record_for_position(
        position: int,
    ) -> ParagraphRecord | None:
        for record in sorted_records:
            if (
                record.range_start
                <= position
                <= record.range_end
            ):
                return record

        if not sorted_records:
            return None

        return min(
            sorted_records,
            key=lambda record: abs(
                record.range_start - position
            ),
        )

    elements: list[AppendixElementRecord] = []

    def add_element(
        text: str,
        paragraph_record: ParagraphRecord,
        range_start: int,
        range_end: int,
    ) -> None:
        label_match = ELEMENT_LABEL_PATTERN.match(
            text
        )

        if label_match is None:
            return

        appendix_letter = appendix_context.get(
            paragraph_record.index,
            "",
        )

        if not appendix_letter:
            return

        elements.append(
            AppendixElementRecord(
                kind=label_match.group("kind").title(),
                label=label_match.group("label"),
                text=text,
                appendix_letter=appendix_letter,
                paragraph=paragraph_record,
                range_start=range_start,
                range_end=range_end,
            )
        )

    for record in paragraph_records:
        add_element(
            text=record.text,
            paragraph_record=record,
            range_start=record.range_start,
            range_end=record.range_end,
        )

    seen_cell_ranges: set[tuple[int, int]] = set()

    for table_index in range(
        1,
        doc.Tables.Count + 1,
    ):
        table = doc.Tables.Item(table_index)

        if is_schedule_table(table):
            continue


        if is_schedule_table(table):
            print(
                f"Skipping schedule table {table_index} "
                "for caption and footnote validation."
            )
            continue

        for row_index in range(
            1,
            table.Rows.Count + 1,
        ):
            try:
                row = table.Rows.Item(row_index)

            except Exception as table_row_error:
                print(
                    f"Skipping table {table_index} row traversal "
                    f"because of merged cells: {table_row_error}"
                )
                break


            try:
                cell_count = row.Cells.Count
            except Exception:
                continue

            for column_index in range(
                1,
                cell_count + 1,
            ):
                try:
                    word_cell = row.Cells.Item(
                        column_index
                    )

                    cell_text = clean_text(
                        word_cell.Range.Text
                    )

                    paragraph_record = record_for_position(
                        word_cell.Range.Start
                    )

                except Exception:
                    continue

                if (
                    not cell_text
                    or paragraph_record is None
                ):
                    continue

                range_start = word_cell.Range.Start

                range_end = max(
                    word_cell.Range.Start,
                    word_cell.Range.End - 1,
                )

                cell_key = (
                    range_start,
                    range_end,
                )

                if cell_key in seen_cell_ranges:
                    continue

                seen_cell_ranges.add(cell_key)

                add_element(
                    text=cell_text,
                    paragraph_record=paragraph_record,
                    range_start=range_start,
                    range_end=range_end,
                )

    findings.extend(
        validate_appendix_elements(
            elements
        )
    )

    return findings


def add_structural_findings(
    doc,
    paragraph_records: list[ParagraphRecord],
) -> list[dict]:
    """
    Run all structural validators.

    Each validator is isolated so that one complex Word object, such as
    a vertically merged table or deleted hyperlink, cannot disable all
    other structural validation.
    """

    findings: list[dict] = []

    def safe_structural_check(
        check_name: str,
        callback,
    ) -> list[dict]:
        """
        Run one structural validator safely.

        If Word COM raises an error, log the failure and return no
        findings for only that validator.
        """

        try:
            result = callback()

            return result or []

        except Exception as structural_error:
            print(
                f"Structural check skipped: {check_name}: "
                f"{structural_error}"
            )

            print(traceback.format_exc())

            return []

    def run_abbreviation_checks() -> list[dict]:
        """
        Run abbreviation, List of Abbreviations, and deprecated-term
        checks as one controlled group.
        """

        policy = build_effective_policy(
            base_policy_path=ABBREVIATION_POLICY_PATH,
            database_path=ABBREVIATION_DATABASE_PATH,
        )

        list_heading = find_list_heading(
            paragraph_records
        )

        abbreviation_entries = (
            extract_abbreviation_entries_from_word(
                doc=doc,
                heading_record=list_heading,
                policy=policy,
            )
        )

        has_abbreviation_list = (
            list_heading is not None
        )

        abbreviation_findings = validate_first_use(
            paragraphs=paragraph_records,
            policy=policy,
            has_abbreviation_list=has_abbreviation_list,
            abbreviation_entries=abbreviation_entries,
            list_heading=list_heading,
        )

        abbreviation_findings.extend(
            validate_deprecated_terms(
                paragraphs=paragraph_records,
                deprecated_terms=policy.get(
                    "deprecated_terms",
                    {},
                ),
            )
        )

        return abbreviation_findings

    # A4: Abbreviations, List of Abbreviations, and deprecated terms.
    findings.extend(
        safe_structural_check(
            "abbreviation validation",
            run_abbreviation_checks,
        )
    )

    # A7.2: Word lists and manually typed bullet lists.
    findings.extend(
        safe_structural_check(
            "list validation",
            lambda: validate_list_structure(
                paragraphs=paragraph_records,
            ),
        )
    )

    # A8.1: Italics, roman Latin terms, and radiolabel formatting.
    findings.extend(
        safe_structural_check(
            "typography validation",
            lambda: add_typography_findings(
                doc=doc,
                paragraph_records=paragraph_records,
            ),
        )
    )

    # A8.2: Raw URLs and active external Word hyperlinks.
    findings.extend(
        safe_structural_check(
            "reference validation",
            lambda: add_reference_findings(
                doc=doc,
                paragraph_records=paragraph_records,
            ),
        )
    )

    # A9.1: Table heading case and table zero values.
    findings.extend(
        safe_structural_check(
            "table validation",
            lambda: add_table_findings(
                doc=doc,
                paragraph_records=paragraph_records,
            ),
        )
    )

    # A9.2: Table captions and table footnotes.
    findings.extend(
        safe_structural_check(
            "caption and footnote validation",
            lambda: add_caption_footnote_findings(
                doc=doc,
                paragraph_records=paragraph_records,
            ),
        )
    )

    # A9.3: Figure titles, labels, duplicate numbering, and visual review.
    findings.extend(
        safe_structural_check(
            "figure validation",
            lambda: add_figure_findings(
                doc=doc,
                paragraph_records=paragraph_records,
            ),
        )
    )

    # A9.4: Appendix table and figure prefix/sequence checks.
    findings.extend(
        safe_structural_check(
            "appendix validation",
            lambda: add_appendix_findings(
                doc=doc,
                paragraph_records=paragraph_records,
            ),
        )
    )

    return findings


# --- THE CORE ENGINE ---
def run_scan_thread(docx_path, output_path, status_var, progress_var, start_btn):
    """This runs in the background so the GUI doesn't freeze."""
    # 1. We MUST initialize COM for this specific background thread
    pythoncom.CoInitialize() 

    word = None
    doc = None
    audit_stage = "Starting audit"
    
    try:
        status_var.set("Running approved rule regression tests...")
        progress_var.set(0)

        audit_stage = "Running regression tests"
        run_regression_gate()

        status_var.set("Regression tests passed. Launching Word...")
        progress_var.set(5)

        abs_input = os.path.abspath(docx_path)
        abs_output = os.path.abspath(output_path)
        
        status_var.set("Launching Word in the background...")

        audit_stage = "Launching Microsoft Word"
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        
        try:
            audit_stage = "Opening source document"
            doc = word.Documents.Open(abs_input)
            audit_stage = "Extracting document paragraphs"
            (
                batch_payload,
                line_to_range,
                paragraph_records,
                total_paragraphs,
            ) = build_paragraph_records(doc)

            status_var.set(
                f"Step 1/3: Extracting {total_paragraphs} paragraphs..."
            )
            progress_var.set(33)

            audit_stage = "Running structural validators"
            try:
                structural_findings = add_structural_findings(
                    doc=doc,
                    paragraph_records=paragraph_records,
                )

            except Exception as structural_error:
                print(
                    "Structural validation was skipped because Word returned "
                    f"an error: {structural_error}"
                )

                print(traceback.format_exc())

                structural_findings = []


            try:
                candidate_records = [
                    TextRecord(
                        index=record.index,
                        text=record.text,
                    )
                    for record in paragraph_records
                ]

                candidate_summaries = discover_candidates(
                    database_path=ABBREVIATION_DATABASE_PATH,
                    records=candidate_records,
                )

                candidate_report_path = (
                    candidate_report_path_for_document(
                        Path(abs_output)
                    )
                )

                write_candidate_report(
                    summaries=candidate_summaries,
                    report_path=candidate_report_path,
                )

                print(
                    "Candidate review report updated: "
                    f"{candidate_report_path}"
                )

            except Exception as candidate_error:

                # Candidate reporting is useful but must not block the primary
                # Word audit if a noncritical reporting error occurs.
                print(
                    "Candidate review report was not generated: "
                    f"{candidate_error}"
                )

            status_var.set("Step 2/3: Executing Vale style scan...")
            process = subprocess.run(
                [
                "vale",
                "--no-global",
                f"--config={PROJECT_ROOT / '.vale.ini'}",
                "--ext=.md",
                "--output=JSON",
                ],
                input=batch_payload,
                text=True,
                capture_output=True,
                check=False,
                encoding='utf-8'
            )
            progress_var.set(66) # Scan complete, bump bar to 66%
            
            if process.stdout.strip():
                vale_results = json.loads(process.stdout)
                vale_errors = vale_results.get("stdin.md", [])
                
                merged_errors = merge_audit_findings(
                    vale_findings=vale_errors,
                    structural_findings=structural_findings,
                )

                context_filtered_errors, suppressed_findings = (
                    filter_findings_by_context(
                        findings=merged_errors,
                        paragraph_records=paragraph_records,
                    )
                )

                errors = deduplicate_findings(
                    context_filtered_errors
                )

                if suppressed_findings:
                    print(
                        "Context-suppressed findings: "
                        f"{sum(suppressed_findings.values())}"
                    )

                    for reason, count in sorted(
                        suppressed_findings.items()
                    ):
                        print(
                            f"  {count} suppressed: {reason}"
                        )

                deduplicated_count = (
                    len(context_filtered_errors) - len(errors)
                )

                if deduplicated_count > 0:
                    print(
                        "Duplicate findings removed: "
                        f"{deduplicated_count}"
                    )


                status_var.set(
                    f"Step 3/3: Injecting {len(errors)} comments..."
                )

                total_errors = len(errors)

                if total_errors > 0:
                    def finding_start_position(
                        finding: dict,
                    ) -> int:
                        """Return a stable position for descending comment insertion."""

                        range_start = finding.get("RangeStart")

                        if isinstance(range_start, int):
                            return range_start

                        line_number = finding.get("Line")

                        paragraph_range = line_to_range.get(
                            line_number
                        )

                        if paragraph_range:
                            return paragraph_range[0]

                        return 0

                    # Add comments from the end of the document toward the beginning.
                    # This minimizes the chance that Word updates positions before
                    # earlier comments are anchored.
                    ordered_errors = sorted(
                        errors,
                        key=finding_start_position,
                        reverse=True,
                    )

                    audit_stage = "Inserting Word comments"
                    for idx, error in enumerate(
                        ordered_errors,
                        start=1,
                    ):
                        range_start = error.get("RangeStart")
                        range_end = error.get("RangeEnd")

                        target_range = None

                        # Exact-range structural findings, such as table cells,
                        # captions, footnotes, figures, and hyperlinks.
                        if (
                            isinstance(range_start, int)
                            and isinstance(range_end, int)
                            and range_end > range_start
                        ):
                            document_end = doc.Content.End

                            safe_start = max(
                                0,
                                min(range_start, document_end - 1),
                            )

                            safe_end = max(
                                safe_start + 1,
                                min(range_end, document_end),
                            )

                            target_range = doc.Range(
                                safe_start,
                                safe_end,
                            )

                        # Vale and ordinary paragraph findings.
                        else:
                            line_number = error.get("Line")

                            paragraph_range = line_to_range.get(
                                line_number
                            )

                            if paragraph_range:
                                paragraph_start, paragraph_end = (
                                    paragraph_range
                                )

                                vale_span_range = vale_span_to_word_range(
                                    paragraph_start=paragraph_start,
                                    paragraph_end=paragraph_end,
                                    span=error.get("Span"),
                                )

                                if vale_span_range is not None:
                                    safe_start, safe_end = vale_span_range

                                else:
                                    document_end = doc.Content.End

                                    safe_start = max(
                                        0,
                                        min(paragraph_start, document_end - 1),
                                    )

                                    safe_end = max(
                                        safe_start + 1,
                                        min(paragraph_end, document_end),
                                    )

                                target_range = doc.Range(
                                    safe_start,
                                    safe_end,
                                )

                        if target_range:
                            severity = error.get(
                                "Severity",
                                "suggestion",
                            ).upper()

                            match_text = error.get("Match", "")
                            message = error.get("Message", "")

                            rule_id = error.get(
                                "Check",
                                "Clinical.UnknownRule",
                            )

                            comment_text = (
                                f"{rule_id} {severity} -> "
                                f"'{match_text}': {message}"
                            )

                            try:
                                doc.Comments.Add(
                                    Range=target_range,
                                    Text=comment_text,
                                )

                            except Exception as comment_error:
                                print(
                                    "Comment insertion skipped for "
                                    f"{rule_id}: {comment_error}"
                                )

                        # Update progress for the final 33% of the bar.
                        progress_var.set(
                            66 + ((idx / total_errors) * 34)
                        )

                        
            status_var.set("Saving audited document...")
            audit_stage = "Saving audited document"
            doc.SaveAs2(abs_output)
            status_var.set("Complete! Document is ready.")
            progress_var.set(100)
            messagebox.showinfo("Success", f"Scan complete.\nSaved to:\n{abs_output}")
            
        finally:
            if doc is not None:
                try:
                    doc.Close(SaveChanges=False)
                except Exception as cleanup_error:
                    print(
                        "Word document cleanup warning: "
                        f"{cleanup_error}"
                    )

            if word is not None:
                try:
                    word.Quit()
                except Exception as cleanup_error:
                    print(
                        "Word application cleanup warning: "
                        f"{cleanup_error}"
                    )
            
    except Exception as error:
        status_var.set(
            f"Error occurred during: {audit_stage}"
        )

        error_details = traceback.format_exc()

        print(
            f"AUDIT ERROR DURING {audit_stage}:"
        )

        print(error_details)

        messagebox.showerror(
            "Audit Error",
            (
                f"Audit failed during:\n"
                f"{audit_stage}\n\n"
                f"{error}\n\n"
                "Detailed traceback was printed to the PowerShell window."
            ),
        )

    finally:
        # 2. We MUST uninitialize COM before the thread dies
        pythoncom.CoUninitialize()
        # Re-enable the start button
        try:
            start_btn.config(state=tk.NORMAL)
        except Exception as button_error:
            print(
                "GUI cleanup warning: "
                f"{button_error}"
            )


# --- THE GUI BUILDER ---
def select_input(entry_widget, output_entry_widget):
    filepath = filedialog.askopenfilename(filetypes=[("Word Documents", "*.docx")])
    if filepath:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, filepath)
        
        # Auto-generate the output filepath
        directory, filename = os.path.split(filepath)
        name, ext = os.path.splitext(filename)
        out_filepath = os.path.join(directory, f"{name}_AUDITED{ext}")
        
        output_entry_widget.delete(0, tk.END)
        output_entry_widget.insert(0, out_filepath)

def select_output(entry_widget):
    filepath = filedialog.asksaveasfilename(defaultextension=".docx", filetypes=[("Word Documents", "*.docx")])
    if filepath:
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, filepath)

def start_process(input_entry, output_entry, status_var, progress_var, start_btn):
    in_path = input_entry.get()
    out_path = output_entry.get()
    
    if not in_path or not out_path:
        messagebox.showwarning("Missing Files", "Please select both input and output files.")
        return
        
    if not os.path.exists(in_path):
        messagebox.showerror("File Not Found", "The selected input file does not exist.")
        return

    # Disable button to prevent multiple clicks
    start_btn.config(state=tk.DISABLED)
    status_var.set("Starting...")
    progress_var.set(0)
    
    # Launch the background thread
    thread = threading.Thread(
        target=run_scan_thread, 
        args=(in_path, out_path, status_var, progress_var, start_btn),
        daemon=True
    )
    thread.start()


def open_review_for_selected_output(
    parent: tk.Misc,
    output_entry,
) -> None:
    """
    Open the candidate review window only for the selected audit output.

    The review window must never silently display a stale report from
    a different document.
    """

    output_value = output_entry.get().strip()

    if not output_value:
        messagebox.showinfo(
            "Abbreviation Review",
            (
                "Select a document and run an audit before opening "
                "the abbreviation review window."
            ),
            parent=parent,
        )
        return

    output_path = Path(output_value)

    report_path = candidate_report_path_for_document(
        output_path
    )

    if not report_path.is_file():
        messagebox.showinfo(
            "Abbreviation Review",
            (
                "No abbreviation candidate report exists for this "
                "audit output yet.\n\n"
                "Run the audit first, then open the review window."
            ),
            parent=parent,
        )
        return

    open_review_window(
        parent=parent,
        report_path=report_path,
        database_path=ABBREVIATION_DATABASE_PATH,
    )



def build_gui():
    root = tk.Tk()
    root.title("Medical Writer - Vale Auditor")
    root.geometry("600x350")
    root.resizable(False, False)
    
    # Padding and layout configuration
    frame = ttk.Frame(root, padding="20")
    frame.pack(fill=tk.BOTH, expand=True)
    
    # Input Row
    ttk.Label(frame, text="Target Protocol (.docx):").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
    input_entry = ttk.Entry(frame, width=50)
    input_entry.grid(row=0, column=1, padx=10, pady=(0, 5))
    ttk.Button(frame, text="Browse", command=lambda: select_input(input_entry, output_entry)).grid(row=0, column=2, pady=(0, 5))
    
    # Output Row
    ttk.Label(frame, text="Output Audited File:").grid(row=1, column=0, sticky=tk.W, pady=10)
    output_entry = ttk.Entry(frame, width=50)
    output_entry.grid(row=1, column=1, padx=10, pady=10)
    ttk.Button(frame, text="Browse", command=lambda: select_output(output_entry)).grid(row=1, column=2, pady=10)
    
    # Progress and Status
    status_var = tk.StringVar()
    status_var.set("Ready.")
    ttk.Label(frame, textvariable=status_var).grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(20, 5))
    
    progress_var = tk.DoubleVar()
    progress_bar = ttk.Progressbar(frame, variable=progress_var, maximum=100)
    progress_bar.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
    
    # Action Button
    start_btn = ttk.Button(
        frame, 
        text="Run Audit", 
        command=lambda: start_process(input_entry, output_entry, status_var, progress_var, start_btn)
    )
    start_btn.grid(row=4, column=0, columnspan=3, pady=20)

    review_btn = ttk.Button(
        frame,
        text="Review Abbreviations",
        command=lambda: open_review_for_selected_output(
            parent=root,
            output_entry=output_entry,
        ),
    )

    review_btn.grid(
        row=5,
        column=0,
        columnspan=3,
        pady=(0, 10),
    )

    root.mainloop()

if __name__ == "__main__":
    build_gui()