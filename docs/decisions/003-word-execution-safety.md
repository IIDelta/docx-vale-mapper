# ADR 003 — Word Execution Safety

## Decision
No Word edit/comment occurs without source SHA validation, verified anchor, protected-field validation, and policy eligibility.

## Rationale
Word COM ranges can shift after edits and may overlap fields, comments, tables, or references. Safety is more important than automatic coverage.
