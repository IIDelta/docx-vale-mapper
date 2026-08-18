# Testing

## Full Gate
```powershell
python -m unittest discover -s tests -p "test*.py"
python tests/runregressiontests.py
python scripts/verifyrepo.py
```

## Compilation
```powershell
python -m py_compile main.py app/*.py runtime/*.py word/*.py validators/*.py
```

## Reports-Only Acceptance
```powershell
python tests/reportsonlyacceptance.py --source "<source.docx>" --output-base "<base.docx>"
```

## Planning
```powershell
python tests/buildcommentplan.py --findings "<findings.json>" --output-base "<base.docx>"
python tests/runautofixpreflight.py --source "<source.docx>" --plan "<plan.json>" --manifest "<manifest.json>" --output-base "<base.docx>"
python tests/runcommentpreflight.py --source "<source.docx>" --plan "<plan.json>" --manifest "<manifest.json>" --output-base "<base.docx>"
```

## Execution
```powershell
python tests/execute_operational_audit.py --source "<source.docx>" --output "<output.docx>" --manifest "<manifest.json>" --autofix-preflight "<autofixpreflight.json>" --comment-preflight "<commentpreflight.json>"
```

## Phase 2 Verification
```powershell
python tests/createphase2fixtures.py
python tests/runphase2executionverification.py
```
