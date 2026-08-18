# Agent Context

The project audits regulatory DOCX documents against Takeda style rules. It combines Vale, Word COM extraction, validators, context filtering, JSON reports, comment policy, and controlled Word execution.

Default mode is reports-only. Current Word execution is a controlled pilot, not a general production feature.

Read in order:
1. `../currentstate.md`
2. `../architecture.md`
3. `../rulecatalog.md`
4. active task in `../../tasks/`

Never assume an apparent text match is safe to edit. Word actions require verified ranges, source SHA match, protected-field checks, and policy eligibility.
