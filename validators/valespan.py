from __future__ import annotations


def vale_span_to_word_range(
    paragraph_start: int,
    paragraph_end: int,
    span,
) -> tuple[int, int] | None:
    """
    Convert a Vale JSON span into a Word character range.

    Vale spans are one-based and end-exclusive for practical mapping
    against extracted paragraph text.
    """

    if (
        not isinstance(span, list)
        or len(span) != 2
        or not all(
            isinstance(value, int)
            for value in span
        )
    ):
        return None

    span_start, span_end = span

    if span_start < 1 or span_end <= span_start:
        return None

    word_start = paragraph_start + span_start - 1
    word_end = paragraph_start + span_end

    safe_start = max(
        paragraph_start,
        min(word_start, paragraph_end - 1),
    )

    safe_end = max(
        safe_start + 1,
        min(word_end, paragraph_end),
    )

    return safe_start, safe_end


def resolve_match_offsets(
    vale_text: str,
    match_text: str,
    span,
) -> tuple[int, int] | None:
    """
    Locate the Vale Match text in the exact Vale paragraph input.

    Vale spans can drift in complex Word content containing fields,
    nonbreaking spaces, hidden characters, or mixed formatting.
    This function finds all matching text instances and selects the
    occurrence nearest the reported Vale span.
    """

    if not vale_text or not match_text:
        return None

    normalized_text = vale_text.casefold()
    normalized_match = match_text.casefold()

    positions: list[int] = []

    start_position = 0

    while True:
        found_position = normalized_text.find(
            normalized_match,
            start_position,
        )

        if found_position < 0:
            break

        positions.append(found_position)

        start_position = (
            found_position
            + max(1, len(normalized_match))
        )

    if not positions:
        return None

    expected_position = 0

    if (
        isinstance(span, list)
        and len(span) == 2
        and isinstance(span[0], int)
    ):
        expected_position = max(
            0,
            span[0] - 1,
        )

    best_position = min(
        positions,
        key=lambda position: abs(
            position - expected_position
        ),
    )

    return (
        best_position,
        best_position + len(match_text),
    )


def vale_match_occurrence_index(
    vale_text: str,
    match_text: str,
    span,
) -> int:
    """
    Return the zero-based occurrence index of a Vale match.

    This lets Word Find select the correct repeated occurrence within
    a paragraph rather than always selecting the first one.
    """

    if not vale_text or not match_text:
        return 0

    normalized_text = vale_text.casefold()
    normalized_match = match_text.casefold()

    positions: list[int] = []

    start_position = 0

    while True:
        found_position = normalized_text.find(
            normalized_match,
            start_position,
        )

        if found_position < 0:
            break

        positions.append(found_position)

        start_position = (
            found_position
            + max(1, len(normalized_match))
        )

    if not positions:
        return 0

    expected_position = 0

    if (
        isinstance(span, list)
        and len(span) == 2
        and isinstance(span[0], int)
    ):
        expected_position = max(
            0,
            span[0] - 1,
        )

    best_index = min(
        range(len(positions)),
        key=lambda index: abs(
            positions[index] - expected_position
        ),
    )

    return best_index
