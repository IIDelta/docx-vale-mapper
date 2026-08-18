<<<<<<< HEAD
# Medical Writer Vale Auditor — Agent Rules

## Mission
This repository audits DOCX regulatory documents against a controlled Takeda Style Guide ruleset. It produces JSON audit evidence by default and supports controlled Word comments and auto-fixes only when ranges have been preflight-verified.

## Read Before Editing
1. `agent/context.md`
2. `currentstate.md`
3. `architecture.md`
4. `rulecatalog.md`
5. The active task file in `tasks/`

## Mandatory Start Gate
```powershell
git status --short
git rev-parse HEAD
python scripts/verifyrepo.py
```
Work only from a clean branch. Record the SHA in the task artifact.

## Mandatory Completion Gate
```powershell
python -m unittest discover -s tests -p "test*.py"
python tests/runregressiontests.py
python scripts/verifyrepo.py
```
Update `currentstate.md`, `rulecatalog.md`, and any affected decision record.

## High-Risk Modules
- `word/commentwriter.py`
- `word/autofixwriter.py`
- `runtime/commentpolicy.py`
- `runtime/autofixpreflight.py`
- `runtime/autofixexecutor.py`
- `validators/fieldprotection.py`
- `runtime/auditpipeline.py`

## Forbidden Actions
- Never overwrite a source DOCX.
- Never use an unverified Word range.
- Never use broad `Range.Text` replacement.
- Never edit protected fields, EndNote, bibliography, title-page, table, or footnote content unless the task explicitly permits it.
- Never commit generated audit artifacts.
- Never commit temporary `ApplyP*.py` files.
- Never change a rule disposition without updating `rulecatalog.md` and `config/commentpolicy.json`.

## Audit Modes
`reports_only` is the default and writes JSON artifacts only. `word_comments` is controlled execution and requires verified auto-fix/comment preflights.

## Commit Convention
Use conventional messages:
```text
feat(scope): description
fix(scope): description
refactor(scope): description
test(scope): description
docs(scope): description
chore(scope): description
```
=======
# Agent Instructions

Welcome to the Medical Writer Vale Auditor repository. This file serves as a guide for autonomous AI agents navigating, modifying, or testing the codebase.

## Overview
This is a Windows desktop application (and CLI) for auditing Microsoft Word documents against a controlled writing-style ruleset. It uses `python-docx` for parsing and `pywin32` for Word Interop (comment insertion/auto-fixing). It also integrates with Vale for rule-based text analysis.

## Repository Layout
- **`Styles/`**: Vale-based text rules and style guides.
- **`abbreviations/`**: Abbreviation discovery and local SQLite registry management.
- **`config/`**: Audit profiles and tool configurations.
- **`data/`**: Stores generated sqlite registry data and databases.
- **`registry/`**: Terminology APIs and data access.
- **`reports/`**: Output directory for generated audit summaries and manifests.
- **`runtime/`**: Core execution runtime (audit lifecycle, autofix execution, comment generation).
- **`validators/`**: Rules and logic for structural validation of Word documents (tables, figures, citations).
- **`tests/`**: Unit tests and regression test fixtures.
- **`docs/`**: Project documentation, architecture guides, and agent reviews.
- **`main.py`**: The main entry point orchestrator.

## Development Workflow
1. **Testing**: Run tests using standard Python `unittest`. Add new tests in `tests/` when modifying validation or runtime logic.
2. **Dependencies**: Update `requirements.txt` when introducing new dependencies. Note that `pywin32` requires a Windows environment.
3. **Documentation**: Keep `README.md` and files under `docs/` updated as the architecture evolves.

## Current Backlog
If you are tasked with picking up work without a specific assignment, prioritize the following in order:
1. **Architecture**: Refactor overlapping validation logic and abstract `win32com` vs `python-docx` interactions.
2. **Testing**: Implement test coverage reporting, CI test integrations for Vale, and clean up fixtures.
3. **Reports-only Mode**: Consolidate `.csv`, `.json`, and `.md` reports. Finalize clean audit manifests without document modification.
4. **Word Execution**: Improve offset mapping (`validators/valespan.py`) to target text precisely via Word Interop.
5. **Comment Execution**: Safely integrate comment budget and policy rules into the insertion pipeline without document corruption.
6. **Auto-fix Execution**: Safely apply automatic fixes to typography and abbreviation mappings.

## Rules
- Do not modify files in `tests/fixtures/` unless updating the baseline for a structural change.
- Protect fields and specific Word styles using `validators/fieldprotection.py` when implementing structural mutations.
- Prefer Python 3.11+ syntax and typing (`from __future__ import annotations`).
>>>>>>> 913a656 (architectural updates)
