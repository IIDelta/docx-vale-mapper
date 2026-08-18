# Contracts

## Source Safety Contract
Source DOCX files are never modified. Any Word execution starts by copying the source to an output DOCX.

## Finding Contract
Findings contain rule, severity, message, match, line/span/range where available, and provenance context.

## Plan Contract
Auto-fix and comment plans must carry enough identity to verify the source SHA, paragraph, match occurrence, range/span, and context before Word execution.

## Reports Contract
Reports-only runs must write findings, summary, and manifest JSON; insert zero comments; and set `output_document_created` to false.
