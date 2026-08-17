from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_comment_policy(config_path: Path) -> dict[str, Any]:
    with config_path.open(encoding="utf-8") as input_file:
        policy = json.load(input_file)
    for key in ("auto_fix_rules", "comment_rules", "report_only_rules", "disabled_rules"):
        if not isinstance(policy.get(key), list):
            raise ValueError(f"{key} must be a list.")
    policy["aggregation_threshold"] = max(1, int(policy.get("aggregation_threshold", 5)))
    policy["max_total_comments"] = max(0, int(policy.get("max_total_comments", 50)))
    policy["max_comments_per_rule"] = max(1, int(policy.get("max_comments_per_rule", 5)))
    return policy


def disposition(finding: dict[str, Any], policy: dict[str, Any]) -> str:
    rule = finding.get("Check", "")
    if rule in policy["disabled_rules"]:
        return "disabled"
    if rule in policy["auto_fix_rules"]:
        action = finding.get("Action", {})
        context = finding.get("Context", {})
        if (
            action.get("Name") == "replace"
            and len(action.get("Params") or []) == 1
            and not context.get("has_protected_field", False)
            and context.get("content_zone") == "body_narrative"
        ):
            return "auto_fix"
        return "report_only"
    if rule in policy["comment_rules"]:
        return "comment"
    return "report_only"


def build_comment_plan(findings: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        buckets[disposition(finding, policy)].append(finding)

    auto_fix_plan = []
    occurrence_counts: dict[tuple[str, int | None, str], int] = {}
    for finding in buckets["auto_fix"]:
        rule_id = finding.get("Check", "")
        paragraph_index = finding.get("ParagraphIndex")
        match_text = finding.get("Match", "")
        occurrence_key = (rule_id, paragraph_index, match_text)
        occurrence_index = occurrence_counts.get(occurrence_key, 0)
        occurrence_counts[occurrence_key] = occurrence_index + 1
        context = finding.get("Context", {})
        auto_fix_plan.append({
            "rule_id": rule_id,
            "match": match_text,
            "replacement": finding.get("Action", {}).get("Params", [""])[0],
            "line": finding.get("Line"),
            "paragraph_index": paragraph_index,
            "range_start": finding.get("RangeStart"),
            "range_end": finding.get("RangeEnd"),
            "span": finding.get("Span"),
            "occurrence_index": occurrence_index,
            "paragraph_text": context.get("paragraph_text", ""),
            "context": context,
        })

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in buckets["comment"]:
        grouped[finding.get("Check", "")].append(finding)

    comment_plan = []
    for rule_id, group in sorted(grouped.items()):
        group = sorted(group, key=lambda item: (item.get("Line", 0), item.get("ParagraphIndex", 0)))
        count = len(group)
        if count < policy["aggregation_threshold"]:
            selected = group[:policy["max_comments_per_rule"]]
            for finding in selected:
                comment_plan.append({
                    "rule_id": rule_id,
                    "occurrence_count": count,
                    "aggregated": False,
                    "finding": finding,
                })
        else:
            comment_plan.append({
                "rule_id": rule_id,
                "occurrence_count": count,
                "aggregated": True,
                "finding": group[0],
            })

    comment_plan = comment_plan[:policy["max_total_comments"]]
    return {
        "profile_name": policy.get("profile_name", "Operational Audit"),
        "candidate_finding_count": len(findings),
        "auto_fix_count": len(auto_fix_plan),
        "comment_count": len(comment_plan),
        "report_only_count": len(buckets["report_only"]),
        "disabled_count": len(buckets["disabled"]),
        "rule_dispositions": dict(sorted(Counter(
            disposition(finding, policy) for finding in findings
        ).items())),
        "auto_fix_plan": auto_fix_plan,
        "comment_plan": comment_plan,
        "report_only_findings": buckets["report_only"],
        "disabled_findings": buckets["disabled"],
    }


def write_comment_plan(output_base: Path, plan: dict[str, Any]) -> Path:
    path = output_base.with_suffix(".commentplan.json")
    with path.open("w", encoding="utf-8") as output_file:
        json.dump(plan, output_file, indent=2, ensure_ascii=False)
        output_file.write("\n")
    return path
