from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(
    file_path: Path,
) -> str:
    """Return a SHA-256 hash for a file."""

    digest = hashlib.sha256()

    with file_path.open("rb") as input_file:
        for block in iter(
            lambda: input_file.read(1024 * 1024),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def build_audit_manifest(
    source_path: Path,
    output_path: Path,
    audit_profile: str,
    vale_version: str,
    final_findings: list[dict],
    suppressed_findings,
    comment_metrics: dict,
    content_zone_counts: dict,
    preflight_result: dict,
) -> dict[str, Any]:
    """
    Build a complete audit-run manifest.

    The manifest is local operational metadata. It should not be
    committed when based on a real document.
    """

    return {
        "tool_version": "0.2.0",
        "audit_profile": audit_profile,
        "audit_started_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_document": str(
            source_path.resolve()
        ),
        "output_document": str(
            output_path.resolve()
        ),
        "source_sha256": sha256_file(source_path),
        "vale_version": vale_version,
        "final_finding_count": len(
            final_findings
        ),
        "candidate_comment_count": comment_metrics[
            "candidate_comment_count"
        ],
        "inserted_comment_count": comment_metrics[
            "inserted_comment_count"
        ],
        "skipped_comment_count": sum(
            comment_metrics[
                "skipped_comment_reasons"
            ].values()
        ),
        "skipped_comment_reasons": dict(
            sorted(
                comment_metrics[
                    "skipped_comment_reasons"
                ].items()
            )
        ),
        "suppressed_rule_counts": dict(
            sorted(suppressed_findings.items())
        ),
        "content_zone_counts": dict(
            sorted(content_zone_counts.items())
        ),
        "preflight": preflight_result,
    }


def write_audit_manifest(
    manifest: dict[str, Any],
    output_path: Path,
) -> Path:
    """Write a manifest beside the audited document."""

    manifest_path = output_path.with_suffix(
        ".audit_manifest.json"
    )

    with manifest_path.open(
        "w",
        encoding="utf-8",
    ) as output_file:
        json.dump(
            manifest,
            output_file,
            indent=2,
            ensure_ascii=False,
        )
        output_file.write("\n")

    return manifest_path
