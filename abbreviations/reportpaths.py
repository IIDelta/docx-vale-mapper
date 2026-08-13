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
