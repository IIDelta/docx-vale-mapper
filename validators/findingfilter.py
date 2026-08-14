from __future__ import annotations

from collections import Counter

from validators.abbreviationvalidator import (
    ParagraphRecord,
    normalize_abbreviation,
)


BODY_NARRATIVE_RULES = {
    "Clinical.Participant",
    "Clinical.TrialIntervention",
    "Clinical.ScheduleOfActivities",
    "Clinical.BenefitRisk",
    "Clinical.PreferredWordChoices",
    "Clinical.LeanPhrases",
    "Clinical.Redundancy",
    "Clinical.CompriseUsage",
    "Clinical.ForwardSlashReview",
    "Clinical.PlainLanguageAbbreviations",
    "Clinical.NumeralApostrophes",
    "Clinical.EmailFormat",
    "Clinical.DashSpacing",
    "Clinical.CompoundFormatting",
    "Clinical.Eponyms",
    "Clinical.AmericanSpellingReview",
    "Clinical.DateMonthFirst",
    "Clinical.DateNumeric",
    "Clinical.DateMonthAbbreviation",
    "Clinical.TimeFormat",
    "Clinical.AgeExpressions",
    "Clinical.ProseRanges",
    "Clinical.NumericRatioFormat",
    "Clinical.PValueFormat",
    "Clinical.ConfidenceIntervals",
    "Clinical.MathOperatorSpacing",
    "Clinical.SymbolSpacing",
    "Clinical.TrademarkSymbols",
    "Clinical.Ampersand",
    "Clinical.LabelCapitalization",
    "Clinical.ReferenceLabels",
    "Clinical.CitationPlacement",
    "Clinical.TrialAliasFormat",
    "Clinical.ClinicalDescriptorCase",
    "Clinical.GenericReferenceCase",
    "Clinical.NumeralAtSentenceStart",
    "Clinical.NumberGrouping",
}


TABLE_DATA_RULES = {
    "Clinical.TableHeadingSentenceCase",
    "Clinical.TableZeroFormat",
}


ALWAYS_SUPPRESS_RULES = {
    "Clinical.MultiplePunctuationSpaces",
}


ABBREVIATION_HEADING_RULES = {
    "Clinical.AbbreviationMissingFromList",
    "Clinical.AbbreviationRedefinedInText",
}


SUPPRESSED_ZONES_FOR_BODY_RULES = {
    "title_page",
    "summary_of_changes",
    "protocol_summary",
    "heading",
    "table_cell",
    "list_item",
    "caption",
    "reference",
}


def filter_findings_by_context(
    findings: list[dict],
    paragraph_records: list[ParagraphRecord],
) -> tuple[list[dict], Counter]:
    """
    Remove findings that are not eligible for their document context.
    """

    record_by_line = {
        record.line: record
        for record in paragraph_records
    }

    retained: list[dict] = []
    suppressed = Counter()

    for finding in findings:
        rule_id = finding.get("Check", "")
        line_number = finding.get("Line")

        if rule_id in ALWAYS_SUPPRESS_RULES:
            suppressed[
                f"{rule_id}:production_safe"
            ] += 1
            continue

        record = record_by_line.get(line_number)

        if record is None:
            retained.append(finding)
            continue

        if (
            rule_id in BODY_NARRATIVE_RULES
            and record.content_zone
            in SUPPRESSED_ZONES_FOR_BODY_RULES
        ):
            suppressed[
                f"{rule_id}:{record.content_zone}"
            ] += 1
            continue

        if (
            rule_id in ABBREVIATION_HEADING_RULES
            and record.content_zone == "heading"
        ):
            suppressed[
                f"{rule_id}:heading"
            ] += 1
            continue

        if (
            rule_id in TABLE_DATA_RULES
            and record.content_zone != "table_cell"
        ):
            suppressed[
                f"{rule_id}:{record.content_zone}"
            ] += 1
            continue

        retained.append(finding)

    return retained, suppressed


def deduplicate_findings(
    findings: list[dict],
) -> list[dict]:
    """
    Remove duplicate findings that share rule, location, and match.
    """

    unique_findings: list[dict] = []
    seen_keys: set[tuple] = set()

    for finding in findings:
        range_start = finding.get("RangeStart")
        range_end = finding.get("RangeEnd")

        span = finding.get("Span")

        if isinstance(span, list):
            span_key = tuple(span)
        else:
            span_key = ()

        key = (
            finding.get("Check", ""),
            range_start,
            range_end,
            finding.get("Line"),
            span_key,
            normalize_abbreviation(
                str(finding.get("Match", ""))
            ),
        )

        if key in seen_keys:
            continue

        seen_keys.add(key)
        unique_findings.append(finding)

    return unique_findings
