from __future__ import annotations

from validators.abbreviationvalidator import (
    normalize_abbreviation,
)


def merge_audit_findings(
    vale_findings: list[dict],
    structural_findings: list[dict],
) -> list[dict]:
    """
    Merge Vale and structural findings while suppressing redundant
    deprecated-abbreviation warnings.

    If Vale already flags the same matched token, retain the Vale
    finding because it generally provides the stronger direct style
    correction. Keep all other structural findings.
    """

    vale_matches = {
        normalize_abbreviation(
            str(finding.get("Match", ""))
        )
        for finding in vale_findings
        if finding.get("Match")
    }

    merged_findings = list(vale_findings)

    for finding in structural_findings:
        check = finding.get("Check", "")
        match = normalize_abbreviation(
            str(finding.get("Match", ""))
        )

        is_duplicate_deprecated_warning = (
            check == "Clinical.AbbreviationDeprecated"
            and match
            and match in vale_matches
        )

        if is_duplicate_deprecated_warning:
            continue

        merged_findings.append(finding)

    return merged_findings
