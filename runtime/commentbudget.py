from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_BUDGET = {
    "max_comments": 150,
    "max_comments_per_rule": 30,
    "severity_order": ["error", "warning", "suggestion"],
    "write_full_review_queue": True,
}


def load_comment_budget(config_path: Path) -> dict[str, Any]:
    """Load a validated comment budget, falling back to safe defaults."""
    budget = dict(DEFAULT_BUDGET)
    if config_path.is_file():
        with config_path.open(encoding="utf-8") as input_file:
            loaded = json.load(input_file)
        if isinstance(loaded, dict):
            budget.update(loaded)

    budget["max_comments"] = max(0, int(budget["max_comments"]))
    budget["max_comments_per_rule"] = max(
        0,
        int(budget["max_comments_per_rule"]),
    )
    budget["severity_order"] = [
        str(value).casefold()
        for value in budget["severity_order"]
    ]
    budget["write_full_review_queue"] = bool(
        budget["write_full_review_queue"]
    )
    return budget


def severity_rank(finding: dict[str, Any], budget: dict[str, Any]) -> int:
    """Return the configured severity rank; unknown levels sort last."""
    level = str(finding.get("Severity", "suggestion")).casefold()
    try:
        return budget["severity_order"].index(level)
    except ValueError:
        return len(budget["severity_order"])


def apply_comment_budget(
    findings: list[dict[str, Any]],
    budget: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Select comment candidates and retain deferred findings with reasons."""
    indexed = list(enumerate(findings))
    prioritized = sorted(
        indexed,
        key=lambda item: (
            severity_rank(item[1], budget),
            item[0],
        ),
    )
    selected: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    per_rule = Counter()

    for _, finding in prioritized:
        rule_id = str(finding.get("Check", "Clinical.UnknownRule"))
        if per_rule[rule_id] >= budget["max_comments_per_rule"]:
            deferred.append({**finding, "DeferredReason": "comment_budget_rule"})
            continue
        if len(selected) >= budget["max_comments"]:
            deferred.append({**finding, "DeferredReason": "comment_budget_total"})
            continue
        selected.append(finding)
        per_rule[rule_id] += 1

    return selected, deferred


def write_comment_queue(
    output_path: Path,
    all_findings: list[dict[str, Any]],
    selected_findings: list[dict[str, Any]],
    deferred_findings: list[dict[str, Any]],
    budget: dict[str, Any],
) -> Path:
    """Write all candidate findings and budget decisions for editorial review."""
    queue_path = output_path.with_suffix(".commentqueue.json")
    deferred_reasons = Counter(
        str(item.get("DeferredReason", "unknown"))
        for item in deferred_findings
    )
    payload = {
        "budget": budget,
        "candidate_finding_count": len(all_findings),
        "selected_comment_count": len(selected_findings),
        "deferred_comment_count": len(deferred_findings),
        "deferred_reason_counts": dict(sorted(deferred_reasons.items())),
        "selected_findings": selected_findings,
        "deferred_findings": deferred_findings,
    }
    with queue_path.open("w", encoding="utf-8") as output_file:
        json.dump(payload, output_file, indent=2, ensure_ascii=False)
        output_file.write("\n")
    return queue_path
