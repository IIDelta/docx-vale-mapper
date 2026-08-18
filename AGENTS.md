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
