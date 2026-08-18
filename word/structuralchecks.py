import re
import traceback
from collections import Counter

from abbreviations.auditbridge import (
    build_effective_policy,
)
from app.settings import (
    ABBREVIATION_DATABASE_PATH,
    ABBREVIATION_POLICY_PATH,
    HEADING_TERMS_PATH,
    SCIENTIFIC_TERMS_PATH,
    UNIT_STYLES_PATH,
)
from word.abbreviations import (
    extract_abbreviation_entries_from_word,
)
from validators.abbreviationvalidator import (
    ParagraphRecord,
    clean_text,
    find_list_heading,
    validate_deprecated_terms,
    validate_first_use,
)
from validators.appendixvalidator import (
    AppendixElementRecord,
    ELEMENT_LABEL_PATTERN,
    find_appendix_context,
    validate_appendix_elements,
)
from validators.auditprofile import (
    is_advanced_profile,
)
from validators.captionfootnotevalidator import (
    CaptionRecord,
    FootnoteRecord,
    validate_captions,
    validate_footnotes,
)
from validators.figurevalidator import (
    FigureRecord,
    validate_figures,
)
from validators.headingterms import (
    load_heading_terms,
)
from validators.headingvalidator import (
    validate_heading_paragraph,
)
from validators.listvalidator import (
    validate_list_structure,
)
from validators.referencevalidator import (
    validate_active_external_link,
    validate_reference_text,
)
from validators.scientificterms import (
    load_scientific_terms,
    validate_scientific_terms,
)
from validators.tablevalidator import (
    TableCellRecord,
    validate_table_cells,
)
from validators.typographyvalidator import (
    validate_typography_paragraph,
    validate_unit_nonbreaking_spaces,
)
from validators.unitstyles import (
    load_unit_style_exemptions,
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

    scientific_terms = load_scientific_terms(
        SCIENTIFIC_TERMS_PATH
    )
    heading_terms = load_heading_terms(HEADING_TERMS_PATH)
    unit_style_exemptions = load_unit_style_exemptions(UNIT_STYLES_PATH)
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
                "all_caps": (
                    matched_range.Font.AllCaps == -1
                ),
                "small_caps": (
                    matched_range.Font.SmallCaps == -1
                ),
            }

        findings.extend(
            validate_typography_paragraph(
                paragraph=record,
                offset_preserving_text=offset_preserving_text,
                get_format=get_format,
            )
        )
        findings.extend(
            validate_heading_paragraph(
                paragraph=record,
                text=offset_preserving_text,
                format_state=get_format(0, len(offset_preserving_text)),
                heading_terms=heading_terms,
            )
        )
        findings.extend(
            validate_unit_nonbreaking_spaces(
                paragraph=record,
                raw_text=raw_text,
                excluded_style_names=unit_style_exemptions,
            )
        )
        findings.extend(
            validate_scientific_terms(
                paragraph=record,
                text=offset_preserving_text,
                get_format=get_format,
                registry=scientific_terms,
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
                            container_key=f"table:{table_index}",
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
    audit_profile: str,
) -> list[dict]:
    """
    Run structural validators according to the audit profile.

    Standard Audit runs only trusted structural checks.
    Advanced Structural Review additionally runs experimental
    list/table/figure/appendix validators.
    """

    findings: list[dict] = []

    def safe_structural_check(
        check_name: str,
        callback,
    ) -> list[dict]:
        """Run one validator without disabling the full audit."""

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
        """Run abbreviation and List of Abbreviations checks."""

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

    # Trusted structural checks: enabled in all profiles.
    findings.extend(
        safe_structural_check(
            "abbreviation validation",
            run_abbreviation_checks,
        )
    )

    findings.extend(
        safe_structural_check(
            "typography validation",
            lambda: add_typography_findings(
                doc=doc,
                paragraph_records=paragraph_records,
            ),
        )
    )

    findings.extend(
        safe_structural_check(
            "reference validation",
            lambda: add_reference_findings(
                doc=doc,
                paragraph_records=paragraph_records,
            ),
        )
    )

    # Advanced checks: opt-in only.
    if is_advanced_profile(audit_profile):
        print(
            "Advanced Structural Review enabled."
        )

        findings.extend(
            safe_structural_check(
                "list validation",
                lambda: validate_list_structure(
                    paragraphs=paragraph_records,
                ),
            )
        )

        findings.extend(
            safe_structural_check(
                "table validation",
                lambda: add_table_findings(
                    doc=doc,
                    paragraph_records=paragraph_records,
                ),
            )
        )

        findings.extend(
            safe_structural_check(
                "caption and footnote validation",
                lambda: add_caption_footnote_findings(
                    doc=doc,
                    paragraph_records=paragraph_records,
                ),
            )
        )

        findings.extend(
            safe_structural_check(
                "figure validation",
                lambda: add_figure_findings(
                    doc=doc,
                    paragraph_records=paragraph_records,
                ),
            )
        )

        findings.extend(
            safe_structural_check(
                "appendix validation",
                lambda: add_appendix_findings(
                    doc=doc,
                    paragraph_records=paragraph_records,
                ),
            )
        )

    else:
        print(
            "Standard Audit enabled: list, table, figure, "
            "caption, footnote, and appendix checks are "
            "disabled."
        )

    return findings

