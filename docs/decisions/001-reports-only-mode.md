# ADR 001 — Reports-Only Mode

## Decision
Reports-only is the default audit mode.

## Rationale
Word comment insertion is expensive and initially unreliable at high finding counts. JSON reports provide a safer calibration surface.

## Consequences
Reports-only writes JSON artifacts, inserts zero comments, and does not save an audited DOCX.
