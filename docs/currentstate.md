# Current State

## Default Operational Mode
`reports_only` is the default audit mode. It writes findings, summary, manifest, abbreviation review, comment plan, and preflight artifacts without inserting Word comments or saving an output DOCX.

## Verified Documents
- KER050-MD-201 Protocol Amendment 7
- TAK-226-3001 Protocol Amendment 1

## Verified Components
- Vale regression suite
- structural validator tests
- reports-only acceptance contract
- audit provenance enrichment
- comment planning
- auto-fix anchor preflight
- controlled NBSP/math-spacing auto-fix pilot
- unified operational execution path
- phase 2 execution verification harness (fixtures + assertion scripts)

## Current Restrictions
- Broad auto terminology replacement is not enabled.
- Aggregated unresolved comments remain under controlled preflight/execution work.
- Figure visual-quality review is manual and should not be operational.
- Module 4/nonclinical document-family behavior remains deferred unless in scope.

## Current Operational Rule Disposition
See `rulecatalog.md` and `config/commentpolicy.json`.

## Required Update Rule
Update this file after every behavior, policy, architecture, or execution-safety change.
