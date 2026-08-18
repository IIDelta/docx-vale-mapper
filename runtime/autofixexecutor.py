from __future__ import annotations

import difflib
from typing import Any
import json
import shutil
from collections import defaultdict
from pathlib import Path

from abbreviations.legacyimport import calculate_sha256
from validators.fieldprotection import protected_field_ranges, ranges_overlap


def replacement_operations(match: str, replacement: str) -> list[tuple[str, int, int, str]]:
    operations: list[tuple[str, int, int, str]] = []
    for tag, start, end, replacement_start, replacement_end in difflib.SequenceMatcher(None, match, replacement).get_opcodes():
        if tag != "equal":
            operations.append((str(tag), start, end, replacement[replacement_start:replacement_end]))
    return operations


def select_summary_targets(items: list[dict]) -> dict[str, dict]:
    targets: dict[str, Any] = {}
    for item in items:
        rule = item["rule_id"]
        if rule not in targets or item["verified_range_start"] < targets[rule]["verified_range_start"]:
            targets[rule] = item
    return targets


def execute_autofix_pilot(source: Path, output: Path, manifest: Path, preflight: Path) -> Path:
    pre=json.loads(preflight.read_text(encoding="utf-8")); man=json.loads(manifest.read_text(encoding="utf-8"))
    if calculate_sha256(source)!=man.get("source_sha256"): raise RuntimeError("Source SHA does not match audit manifest.")
    if not pre.get("source_sha256_matches") or pre.get("unverified_count") != 0: raise RuntimeError("Auto-fix preflight is not fully verified.")
    if output.exists(): raise RuntimeError(f"Output already exists: {output}")
    shutil.copy2(source,output)
    import pythoncom, win32com.client
    pythoncom.CoInitialize(); word=None; doc=None; applied=[]; skipped=[]
    try:
        word=win32com.client.DispatchEx("Word.Application"); word.Visible=False
        doc=word.Documents.Open(str(output.resolve()))
        protected=protected_field_ranges(doc)
        summary_targets = select_summary_targets(pre["verified_auto_fixes"])
        summary_comment_records = []
        for rule, item in summary_targets.items():
            start = item["verified_range_start"]
            end = item["verified_range_end"]
            summary_range = doc.Range(start, end)
            if summary_range.Text != item["match"]:
                skipped.append({"item": item, "reason": "summary_comment_anchor_unverified"})
                continue
            count = sum(1 for candidate in pre["verified_auto_fixes"] if candidate["rule_id"] == rule)
            comment = doc.Comments.Add(Range=summary_range, Text=f"Automatically applied {count} verified {rule} fix(es) throughout this document. See autofix execution JSON for all locations.")
            comment.Author="MVA"; comment.Initial="MVA"
            summary_comment_records.append({"rule_id": rule, "range_start": start, "range_end": end, "count": count})
        items=sorted(pre["verified_auto_fixes"], key=lambda x:x["verified_range_start"], reverse=True)
        for item in items:
            start=item["verified_range_start"]; end=item["verified_range_end"]
            rng=doc.Range(start,end)
            if rng.Text != item["match"]: skipped.append({"item":item,"reason":"range_text_mismatch"}); continue
            if ranges_overlap(start,end,protected): skipped.append({"item":item,"reason":"protected_word_field"}); continue
            for tag,a,b,repl in reversed(replacement_operations(item["match"],item["replacement"])):
                target=doc.Range(start+a,start+b)
                if tag=="delete": target.Delete()
                else: target.Text=repl
            applied.append(item)
        doc.Save()
    finally:
        if doc is not None: doc.Close(SaveChanges=False)
        if word is not None: word.Quit()
        pythoncom.CoUninitialize()
    result={"source_sha256":calculate_sha256(source),"output_sha256":calculate_sha256(output),"applied_count":len(applied),"skipped_count":len(skipped),"summary_comment_count":len(summary_comment_records),"summary_comments":summary_comment_records,"applied":applied,"skipped":skipped}
    path=output.with_suffix(".autofixexecution.json"); path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return path
