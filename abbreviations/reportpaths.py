from __future__ import annotations

from pathlib import Path


def candidate_report_path_for_document(
    document_path: Path,
) -> Path:
    """
    Return the sidecar candidate report path for one audited document.

    Example:
        protocol_AUDITED.docx
        → protocol_AUDITED.abbreviationreview.json
    """

    return document_path.with_suffix(
        ".abbreviationreview.json"
    )


def document_path_for_candidate_report(
    report_path: Path,
) -> Path:
    """
    Return the audited DOCX path associated with a candidate report.

    Example:
        protocol_AUDITED.abbreviationreview.json
        → protocol_AUDITED.docx
    """

    suffix = ".abbreviationreview.json"

    if not report_path.name.endswith(suffix):
        raise ValueError(
            "Candidate report filename does not use the expected "
            ".abbreviationreview.json suffix."
        )

    document_name = report_path.name.removesuffix(
        suffix
    ) + ".docx"

    return report_path.with_name(document_name)
