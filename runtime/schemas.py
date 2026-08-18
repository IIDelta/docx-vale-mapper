from typing import TypedDict, Any, List, Optional

class AutoFixPlanEntry(TypedDict):
    rule_id: str
    match: str
    replacement: str
    line: Optional[int]
    paragraph_index: Optional[int]
    range_start: Optional[int]
    range_end: Optional[int]
    span: Optional[List[int]]
    occurrence_index: int
    paragraph_text: str
    context: dict[str, Any]

class VerifiedAutoFix(AutoFixPlanEntry):
    verified_range_start: int
    verified_range_end: int

class UnverifiedAutoFix(TypedDict):
    plan: AutoFixPlanEntry
    reason: str

class CommentPlanEntry(TypedDict):
    rule_id: str
    occurrence_count: int
    aggregated: bool
    finding: dict[str, Any]

class VerifiedComment(CommentPlanEntry):
    verified_range_start: int
    verified_range_end: int

class UnverifiedComment(TypedDict):
    plan: CommentPlanEntry
    reason: str

class CommentPlan(TypedDict):
    profile_name: str
    candidate_finding_count: int
    auto_fix_count: int
    comment_count: int
    report_only_count: int
    disabled_count: int
    rule_dispositions: dict[str, int]
    auto_fix_plan: List[AutoFixPlanEntry]
    comment_plan: List[CommentPlanEntry]
    report_only_findings: List[dict[str, Any]]
    disabled_findings: List[dict[str, Any]]
