# Decision Record: Phase 2 Execution Verification Harness

## Status
Accepted

## Context
Running real clinical documents through the operational Word execution pipeline (auto-fixes and comments via Word Interop) is extremely slow and difficult to verify safely without relying on production data. We need a way to prove that the runtime execution modules insert comments accurately, aggregate when policies dictate, respect ineligible contexts, skip auto-fixes where rules restrict them, and maintain document integrity.

## Decision
We will implement an automated, synthetic execution verification harness for Phase 2 validation.

1. **Fixture Generation**: We use `python-docx` to generate minimal DOCX files containing specific scenarios (e.g., repeating 5 mg instances, math spacing issues, repetitive comment targets).
2. **Harness Scripts**: We have built `executionverification.py` to assert expected artifact counts against generated `.json` output manifests.
3. **Output Inspection**: We have built `outputverification.py` which unzips the output DOCX and validates internal XML nodes to ensure MVA comments exist and formatting is preserved, bypassing the need for an active Word Interop instance for initial gate checks.

## Consequences
- We can validate the execution pipeline in headless environments (like Linux sandboxes) safely by verifying execution manifests and ZIP contents.
- Integration tests involving `pywin32` can still run on developer Windows machines but aren't blocking pipeline development.
- The fixtures must be kept minimal to ensure tests run fast.
