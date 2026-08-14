from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path.cwd()
MAIN_PATH = ROOT / "main.py"
CONFIG_PATH = ROOT / "config" / "commentbudget.json"
MODULE_PATH = ROOT / "runtime" / "commentbudget.py"
TEST_PATH = ROOT / "tests" / "testcommentbudget.py"

CONFIG_SOURCE = {
    "max_comments": 150,
    "max_comments_per_rule": 30,
    "severity_order": ["error", "warning", "suggestion"],
    "write_full_review_queue": True,
}

MODULE_SOURCE = '''from __future__ import annotations

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
        output_file.write("\\n")
    return queue_path
'''

TEST_SOURCE = '''from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.commentbudget import (
    apply_comment_budget,
    load_comment_budget,
    write_comment_queue,
)


class CommentBudgetTests(unittest.TestCase):
    def test_errors_are_prioritized_and_rule_caps_apply(self) -> None:
        findings = [
            {"Check": "Clinical.A", "Severity": "warning"},
            {"Check": "Clinical.A", "Severity": "warning"},
            {"Check": "Clinical.B", "Severity": "error"},
            {"Check": "Clinical.C", "Severity": "suggestion"},
        ]
        budget = {
            "max_comments": 2,
            "max_comments_per_rule": 1,
            "severity_order": ["error", "warning", "suggestion"],
            "write_full_review_queue": True,
        }
        selected, deferred = apply_comment_budget(findings, budget)
        self.assertEqual([item["Check"] for item in selected], ["Clinical.B", "Clinical.A"])
        self.assertEqual(len(deferred), 2)
        self.assertEqual(deferred[0]["DeferredReason"], "comment_budget_rule")
        self.assertEqual(deferred[1]["DeferredReason"], "comment_budget_total")

    def test_queue_preserves_selected_and_deferred_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_path = Path(temporary_directory) / "audited.docx"
            queue_path = write_comment_queue(
                output_path=output_path,
                all_findings=[{"Check": "Clinical.A"}],
                selected_findings=[],
                deferred_findings=[
                    {"Check": "Clinical.A", "DeferredReason": "comment_budget_total"}
                ],
                budget=load_comment_budget(Path(temporary_directory) / "missing.json"),
            )
            payload = json.loads(queue_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["candidate_finding_count"], 1)
        self.assertEqual(payload["deferred_comment_count"], 1)
        self.assertEqual(payload["deferred_reason_counts"], {"comment_budget_total": 1})


if __name__ == "__main__":
    unittest.main()
'''


def newline_for(value: str) -> str:
    return "\r\n" if "\r\n" in value else "\n"


def normalize(value: str) -> str:
    return value.replace("\r\n", "\n")


def main() -> None:
    if not MAIN_PATH.is_file():
        raise RuntimeError("Run this script from the repository root.")
    if any(path.exists() for path in (CONFIG_PATH, MODULE_PATH, TEST_PATH)):
        raise RuntimeError(
            "Comment-budget files already exist. Refusing to overwrite committed work."
        )

    original_main = MAIN_PATH.read_text(encoding="utf-8")
    newline = newline_for(original_main)
    main_source = normalize(original_main)

    import_marker = "from runtime.preflight import (\n"
    import_block = (
        "from runtime.commentbudget import (\n"
        "    apply_comment_budget,\n"
        "    load_comment_budget,\n"
        "    write_comment_queue,\n"
        ")\n"
    )
    if import_marker not in main_source:
        raise RuntimeError("Could not locate the runtime preflight import marker.")
    main_source = main_source.replace(import_marker, import_block + import_marker, 1)

    loop_pattern = re.compile(
        r"^(?P<indent> {8})for idx, error in enumerate\(\n"
        r"(?P=indent)    ordered_errors,\n"
        r"(?P=indent)    start=1,\n"
        r"(?P=indent)\):",
        flags=re.MULTILINE,
    )
    match = loop_pattern.search(main_source)
    if match is None:
        raise RuntimeError("Could not locate the Word comment insertion loop.")

    indent = match.group("indent")
    budget_block = (
        f"{indent}comment_budget = load_comment_budget(\n"
        f"{indent}    PROJECT_ROOT / \"config\" / \"commentbudget.json\"\n"
        f"{indent})\n"
        f"{indent}selected_errors, deferred_findings = apply_comment_budget(\n"
        f"{indent}    findings=errors,\n"
        f"{indent}    budget=comment_budget,\n"
        f"{indent})\n"
        f"{indent}for deferred_finding in deferred_findings:\n"
        f"{indent}    deferred_reason = deferred_finding.get(\n"
        f"{indent}        \"DeferredReason\", \"comment_budget_unknown\"\n"
        f"{indent}    )\n"
        f"{indent}    comment_metrics[\"skipped_comment_reasons\"][\n"
        f"{indent}        deferred_reason\n"
        f"{indent}    ] += 1\n"
        f"{indent}if comment_budget[\"write_full_review_queue\"]:\n"
        f"{indent}    queue_path = write_comment_queue(\n"
        f"{indent}        output_path=audited_output_path,\n"
        f"{indent}        all_findings=errors,\n"
        f"{indent}        selected_findings=selected_errors,\n"
        f"{indent}        deferred_findings=deferred_findings,\n"
        f"{indent}        budget=comment_budget,\n"
        f"{indent}    )\n"
        f"{indent}    print(f\"Comment review queue written: {{queue_path}}\")\n"
        f"{indent}ordered_errors = sorted(\n"
        f"{indent}    selected_errors,\n"
        f"{indent}    key=finding_start_position,\n"
        f"{indent}    reverse=True,\n"
        f"{indent})\n"
        f"{indent}total_errors = len(ordered_errors)\n"
        f"{indent}print(\n"
        f"{indent}    f\"Comment budget: {{len(errors)}} candidates; \"\n"
        f"{indent}    f\"{{total_errors}} selected; \"\n"
        f"{indent}    f\"{{len(deferred_findings)}} deferred.\"\n"
        f"{indent})\n\n"
    )
    main_source = (
        main_source[:match.start()]
        + budget_block
        + main_source[match.start():]
    )

    CONFIG_PATH.write_text(
        json.dumps(CONFIG_SOURCE, indent=2) + "\n",
        encoding="utf-8",
    )
    MODULE_PATH.write_text(MODULE_SOURCE.replace("\n", newline), encoding="utf-8")
    TEST_PATH.write_text(TEST_SOURCE.replace("\n", newline), encoding="utf-8")
    MAIN_PATH.write_text(main_source.replace("\n", newline), encoding="utf-8")

    print("Patch 11 installed successfully.")
    print("Run: python -m unittest tests.testcommentbudget -v")
    print("Then: python tests/runregressiontests.py")


if __name__ == "__main__":
    main()
