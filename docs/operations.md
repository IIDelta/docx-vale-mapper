# Operations

## Reports-Only
Use reports-only as the normal calibration and review workflow. The output base is used to name JSON sidecars; no DOCX is saved.

## Word Execution
Use only on a copied output document after source SHA, auto-fix preflight, and comment preflight are all verified. Inspect the resulting output DOCX in Word and re-audit it in reports-only mode.

## Generated Artifacts
Generated audit JSON and DOCX files are local operational evidence. They must be ignored by Git.

## Recovery
If Word COM stalls, close the app and orphaned WINWORD processes only after preserving logs/artifacts. Never force-close a source document with unsaved human edits.
