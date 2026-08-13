from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from abbreviations.legacyimport import clean_value, normalize_token
from abbreviations.registryapi import (
    RegistryResolution,
    list_registry_tokens,
    resolve_token,
)


GENERIC_CANDIDATE_PATTERN = re.compile(
    r"""
    (?<![A-Za-z0-9])
    (
        (?:
            [A-Z]{2,}[A-Z0-9]*(?:[-/][A-Za-z0-9]+)*
            |
            [A-Za-z]{1,5}\d+(?:[-/][A-Za-z0-9]+)*
        )
    )
    (?![A-Za-z0-9])
    """,
    flags=re.VERBOSE,
)


@dataclass(frozen=True)
class TextRecord:
    """One normalized text record supplied to candidate discovery."""

    index: int
    text: str


@dataclass(frozen=True)
class CandidateOccurrence:
    """One detected candidate occurrence."""

    token: str
    paragraph_index: int
    start: int
    end: int
    context: str
    inline_definition: bool


@dataclass
class CandidateSummary:
    """Aggregated candidate information and registry resolution."""

    token: str
    normalized_token: str
    count: int
    first_paragraph_index: int
    contexts: list[str] = field(default_factory=list)
    inline_definition_count: int = 0
    resolution: RegistryResolution | None = None

    @property
    def review_bucket(self) -> str:
        """Return the review bucket shown to a future user interface."""

        if self.resolution is None or not self.resolution.found:
            if self.inline_definition_count > 0 or self.count >= 2:
                return "likely_unknown"

            return "possible_unknown"

        if self.resolution.status == "approved_expand":
            return "known_expand"

        if self.resolution.status == "approved_no_expand":
            return "protected"

        if self.resolution.status == "approved_list_only":
            return "known_list_only"

        if self.resolution.status == "deprecated":
            return "deprecated"

        if self.resolution.status == "ambiguous":
            return "ambiguous"

        if self.resolution.status == "reviewed_candidate":
            return "reviewed_candidate"

        if self.resolution.status == "ignored":
            return "ignored"

        return "possible_unknown"

    @property
    def confidence(self) -> str:
        """Return a concise confidence category."""

        if self.resolution is not None and self.resolution.found:
            return "high"

        if self.inline_definition_count > 0 or self.count >= 2:
            return "likely"

        return "possible"

    def to_dict(self) -> dict:
        """Convert a candidate summary into JSON-safe output."""

        return {
            "token": self.token,
            "normalized_token": self.normalized_token,
            "count": self.count,
            "first_paragraph_index": self.first_paragraph_index,
            "contexts": self.contexts,
            "inline_definition_count": self.inline_definition_count,
            "review_bucket": self.review_bucket,
            "confidence": self.confidence,
            "resolution": (
                self.resolution.to_dict()
                if self.resolution is not None
                else None
            ),
        }


def build_context(
    text: str,
    start: int,
    end: int,
    radius: int = 55,
) -> str:
    """Return compact surrounding context for a candidate occurrence."""

    left = max(0, start - radius)
    right = min(len(text), end + radius)

    context = clean_value(text[left:right])

    if left > 0:
        context = f"...{context}"

    if right < len(text):
        context = f"{context}..."

    return context


def has_inline_definition(
    text: str,
    token: str,
) -> bool:
    """
    Identify a likely first-use construction.

    Examples:
        adverse event (AE)
        liver function test (LFT)
    """

    escaped_token = re.escape(token)

    pattern = re.compile(
        rf"""
        [A-Za-z]
        [A-Za-z ,;/\-]{{2,100}}
        \(\s*{escaped_token}\s*\)
        """,
        flags=re.VERBOSE,
    )

    return bool(pattern.search(text))


def find_known_token_occurrences(
    text_record: TextRecord,
    known_tokens: list[str],
) -> list[CandidateOccurrence]:
    """Find reviewed registry tokens, preserving mixed-case forms."""

    occurrences: list[CandidateOccurrence] = []

    for token in known_tokens:
        escaped_token = re.escape(token)

        pattern = re.compile(
            rf"(?<![A-Za-z0-9]){escaped_token}(?![A-Za-z0-9])",
            flags=re.IGNORECASE,
        )

        for match in pattern.finditer(text_record.text):
            matched_token = match.group(0)

            occurrences.append(
                CandidateOccurrence(
                    token=matched_token,
                    paragraph_index=text_record.index,
                    start=match.start(),
                    end=match.end(),
                    context=build_context(
                        text_record.text,
                        match.start(),
                        match.end(),
                    ),
                    inline_definition=has_inline_definition(
                        text_record.text,
                        matched_token,
                    ),
                )
            )

    return occurrences


def find_generic_occurrences(
    text_record: TextRecord,
) -> list[CandidateOccurrence]:
    """Find safe generic uppercase, numeric, and hyphenated candidates."""

    occurrences: list[CandidateOccurrence] = []

    for match in GENERIC_CANDIDATE_PATTERN.finditer(text_record.text):
        token = match.group(1)

        occurrences.append(
            CandidateOccurrence(
                token=token,
                paragraph_index=text_record.index,
                start=match.start(1),
                end=match.end(1),
                context=build_context(
                    text_record.text,
                    match.start(1),
                    match.end(1),
                ),
                inline_definition=has_inline_definition(
                    text_record.text,
                    token,
                ),
            )
        )

    return occurrences


def discover_candidates(
    database_path: Path,
    records: list[TextRecord],
    maximum_contexts: int = 3,
) -> list[CandidateSummary]:
    """
    Discover abbreviation-like candidates and resolve them to registry data.

    Discovery uses two sources:
      1. exact matching against known registry tokens;
      2. conservative generic candidate patterns.

    Duplicate matches from both methods are deduplicated by location.
    """

    known_tokens = list_registry_tokens(database_path)

    deduplicated_occurrences: dict[
        tuple[int, int, int, str],
        CandidateOccurrence,
    ] = {}

    for text_record in records:
        occurrences = (
            find_known_token_occurrences(
                text_record=text_record,
                known_tokens=known_tokens,
            )
            + find_generic_occurrences(
                text_record=text_record,
            )
        )

        for occurrence in occurrences:
            key = (
                occurrence.paragraph_index,
                occurrence.start,
                occurrence.end,
                normalize_token(occurrence.token),
            )

            deduplicated_occurrences[key] = occurrence

    grouped_occurrences: dict[
        str,
        list[CandidateOccurrence],
    ] = {}

    for occurrence in deduplicated_occurrences.values():
        normalized = normalize_token(occurrence.token)

        grouped_occurrences.setdefault(
            normalized,
            [],
        ).append(occurrence)

    summaries: list[CandidateSummary] = []

    for normalized_token, occurrences in grouped_occurrences.items():
        ordered_occurrences = sorted(
            occurrences,
            key=lambda occurrence: (
                occurrence.paragraph_index,
                occurrence.start,
            ),
        )

        requested_token = ordered_occurrences[0].token

        resolution = resolve_token(
            database_path=database_path,
            token=requested_token,
        )

        contexts: list[str] = []

        for occurrence in ordered_occurrences:
            if occurrence.context not in contexts:
                contexts.append(occurrence.context)

            if len(contexts) >= maximum_contexts:
                break

        summaries.append(
            CandidateSummary(
                token=(
                    resolution.token
                    if resolution.found
                    else requested_token
                ),
                normalized_token=normalized_token,
                count=len(ordered_occurrences),
                first_paragraph_index=(
                    ordered_occurrences[0].paragraph_index
                ),
                contexts=contexts,
                inline_definition_count=sum(
                    occurrence.inline_definition
                    for occurrence in ordered_occurrences
                ),
                resolution=resolution,
            )
        )

    return sorted(
        summaries,
        key=lambda summary: (
            summary.review_bucket,
            summary.token.casefold(),
        ),
    )


def load_text_records(
    input_path: Path,
) -> list[TextRecord]:
    """
    Load a plain-text candidate fixture.

    Each nonblank line becomes one paragraph-style record.
    """

    records: list[TextRecord] = []

    with input_path.open(
        encoding="utf-8",
        errors="replace",
    ) as input_file:
        for line_number, line in enumerate(
            input_file,
            start=1,
        ):
            text = clean_value(line)

            if not text:
                continue

            records.append(
                TextRecord(
                    index=line_number,
                    text=text,
                )
            )

    return records


def write_report(
    summaries: list[CandidateSummary],
    report_path: Path,
) -> None:
    """Write candidate discovery results as JSON."""

    report_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "candidate_count": len(summaries),
        "candidates": [
            summary.to_dict()
            for summary in summaries
        ],
    }

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            report,
            output_file,
            indent=2,
            ensure_ascii=False,
        )
        output_file.write("\n")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line candidate discovery options."""

    parser = argparse.ArgumentParser(
        description=(
            "Discover abbreviation-like candidates and resolve them "
            "against the reviewed registry."
        )
    )

    parser.add_argument(
        "--database",
        type=Path,
        default=Path("data") / "abbreviations.sqlite",
        help=(
            "SQLite database path. "
            "Default: data/abbreviations.sqlite"
        ),
    )

    parser.add_argument(
        "--text-file",
        type=Path,
        required=True,
        help=(
            "UTF-8 text file. Each nonblank line is treated as "
            "a paragraph-style text record."
        ),
    )

    parser.add_argument(
        "--report",
        type=Path,
        default=Path("reports") / "candidatefinderreport.json",
        help=(
            "JSON report path. "
            "Default: reports/candidatefinderreport.json"
        ),
    )

    return parser.parse_args()


def main() -> int:
    """Run candidate discovery from the command line."""

    arguments = parse_arguments()

    try:
        records = load_text_records(arguments.text_file)

        summaries = discover_candidates(
            database_path=arguments.database,
            records=records,
        )

        write_report(
            summaries=summaries,
            report_path=arguments.report,
        )

    except (FileNotFoundError, OSError, ValueError) as error:
        print(f"CANDIDATE DISCOVERY FAILED: {error}")
        return 2

    print(
        f"Candidate summaries: {len(summaries)}"
    )

    print(
        f"Report: {arguments.report.resolve()}"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
