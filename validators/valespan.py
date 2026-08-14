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
