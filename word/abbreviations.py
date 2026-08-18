import re

from validators.abbreviationvalidator import (
    AbbreviationEntry,
    ParagraphRecord,
    clean_text,
    normalize_abbreviation,
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

