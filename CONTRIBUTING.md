# Contributing

## Branches
Create one branch per task:
```text
feature/<task>
fix/<task>
refactor/<task>
docs/<task>
```

## Change Rules
- Keep behavior changes separate from pure refactors.
- Add or update tests with every behavior change.
- Use JSON artifacts, not Word comments, to calibrate rules.
- Treat generated document artifacts as local evidence, not source code.

## Required Checks
```powershell
python -m py_compile main.py app/*.py runtime/*.py word/*.py validators/*.py
python -m unittest discover -s tests -p "test*.py"
python tests/runregressiontests.py
python scripts/verifyrepo.py
```

## Pull Request / Merge Checklist
- [ ] Task contract identifies goal and non-goals.
- [ ] Generated artifacts are not staged.
- [ ] Relevant docs are updated.
- [ ] Rule disposition is documented.
- [ ] Source DOCX safety is preserved.
- [ ] Reports-only behavior remains available.
