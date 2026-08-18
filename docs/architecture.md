# Architecture

## Purpose
Medical Writer Vale Auditor audits DOCX clinical/regulatory documents against a controlled Takeda Style Guide ruleset. It is an editorial-support tool; findings require qualified human review.

## Data Flow
```text
DOCX source
  -> Word COM extraction
  -> ParagraphRecord / table / caption / figure records
  -> Vale rules + structural validators
  -> context and protected-field filtering
  -> final findings
  -> JSON reports
  -> comment policy
  -> auto-fix and comment plans
  -> read-only preflight
  -> optional copied-DOCX execution
```

## Layer Boundaries

### `app/`
Owns Tkinter UI, user input, workflow launch, and status/progress display. It must not resolve Word ranges or implement style rules.

### `runtime/`
Owns audit lifecycle, artifact creation, manifests, comment policy, plans, preflight, and execution logs. It must not build GUI widgets.

### `word/`
Owns Word COM extraction, range resolution, comments, copied-document auto-fixes, and output verification. It must not decide rule dispositions.

### `validators/`
Owns deterministic checks and finding creation. It must not open or save DOCX files.

### `abbreviations/`
Owns candidate discovery, SQLite registry, review windows, promotion, and abbreviation reports.

### `Styles/`
Owns Vale YAML rules and their messages/actions.

### `config/`
Owns controlled policy: rule coverage, comment policy, scientific terms, heading terms, and unit-style exclusions.

## Invariants
- Source DOCX is never overwritten.
- Reports-only mode does not create an audited DOCX.
- Auto-fix requires source SHA and verified range.
- Comments require verified anchors.
- Protected fields are not edited or commented.
- Generated audit artifacts are not committed.
