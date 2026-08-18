from __future__ import annotations

import json
import shutil
import traceback
from collections import defaultdict
import typing
from pathlib import Path
from typing import Any

from abbreviations.legacyimport import calculate_sha256
from validators.fieldprotection import protected_field_ranges, ranges_overlap

def replacement_operations(match: str, replacement: str) -> list[tuple[str, int, int, str]]:
    import difflib
    operations: list[tuple[str, int, int, str]] = []
    for tag, start, end, replacement_start, replacement_end in difflib.SequenceMatcher(None, match, replacement).get_opcodes():
        if tag != "equal":
            operations.append((str(tag), start, end, replacement[replacement_start:replacement_end]))
    return operations

def execute_operational_audit(
    source_path: Path,
    output_path: Path,
    manifest_path: Path,
    autofix_preflight_path: Path,
    comment_preflight_path: Path,
    output_base: Path,
    word_app: Any = None,
) -> dict[str, Path]:
    
    man = json.loads(manifest_path.read_text(encoding="utf-8"))
    af_pre = json.loads(autofix_preflight_path.read_text(encoding="utf-8"))
    com_pre = json.loads(comment_preflight_path.read_text(encoding="utf-8"))
    
    source_sha = calculate_sha256(source_path)
    if source_sha != man.get("source_sha256"):
        raise RuntimeError("Source SHA does not match audit manifest.")
        
    if not af_pre.get("source_sha256_matches") or af_pre.get("unverified_count") != 0:
        unverified_details = ""
        unverified_items = af_pre.get("unverified_auto_fixes", [])
        if unverified_items:
            first_fail = unverified_items[0]
            unverified_details = f" First failure: {first_fail.get('reason')} on '{first_fail.get('plan', {}).get('match')}'"
        raise RuntimeError(f"Auto-fix preflight is not fully verified.{unverified_details}")
        
    if not com_pre.get("source_sha256_matches") or com_pre.get("unverified_count") != 0:
        unverified_details = ""
        unverified_items = com_pre.get("unverified_comments", [])
        if unverified_items:
            first_fail = unverified_items[0]
            unverified_details = f" First failure: {first_fail.get('reason')} on '{first_fail.get('plan', {}).get('finding', {}).get('Match')}'"
        raise RuntimeError(f"Comment preflight is not fully verified.{unverified_details}")

    if output_path.exists():
        raise RuntimeError(f"Output already exists: {output_path}")

    shutil.copy2(source_path, output_path)

    import pythoncom
    import win32com.client

    own_word = False
    if word_app is None:
        pythoncom.CoInitialize()
        word = None
    else:
        word = word_app

    doc = None
    
    af_applied = []
    af_skipped = []
    af_summary_records = []
    
    com_inserted = []
    com_skipped = []
    skipped_reasons: typing.DefaultDict[str, int] = defaultdict(int)
    
    inserted_comment_count = 0
    aggregated_comment_count = 0
    autofix_summary_comment_count = 0
    
    try:
        if own_word or word is None:
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            own_word = True
        doc = word.Documents.Open(str(output_path.resolve()))
        protected = protected_field_ranges(doc)
        
        # ---------------------------
        # A & B. Auto-Fix Execution
        # ---------------------------
        verified_fixes = af_pre.get("verified_auto_fixes", [])
        
        # Select summary targets (lowest range per rule)
        summary_targets: dict[str, Any] = {}
        for item in verified_fixes:
            rule = item["rule_id"]
            if rule not in summary_targets or item["verified_range_start"] < summary_targets[rule]["verified_range_start"]:
                summary_targets[rule] = item
                
        # Insert summary comments
        for rule, item in summary_targets.items():
            start = item["verified_range_start"]
            end = item["verified_range_end"]
            summary_range = doc.Range(start, end)
            if summary_range.Text != item["match"]:
                af_skipped.append({"item": item, "reason": "summary_comment_anchor_unverified"})
                continue
            
            count = sum(1 for candidate in verified_fixes if candidate["rule_id"] == rule)
            comment_text = f"Automatically applied {count} verified {rule} fix(es) throughout this document. See autofix execution JSON for all locations."
            comment = doc.Comments.Add(Range=summary_range, Text=comment_text)
            try:
                comment.Author = "MVA"
                comment.Initial = "MVA"
            except Exception:
                pass
            
            autofix_summary_comment_count += 1
            af_summary_records.append({"rule_id": rule, "range_start": start, "range_end": end, "count": count})
            
        # Apply fixes in reverse Word-range order
        items = sorted(verified_fixes, key=lambda x: x["verified_range_start"], reverse=True)
        for item in items:
            start = item["verified_range_start"]
            end = item["verified_range_end"]
            rng = doc.Range(start, end)
            if rng.Text != item["match"]:
                af_skipped.append({"item": item, "reason": "range_text_mismatch"})
                continue
            if ranges_overlap(start, end, protected):
                af_skipped.append({"item": item, "reason": "protected_word_field"})
                continue
                
            for tag, a, b, repl in reversed(replacement_operations(item["match"], item["replacement"])):
                target = doc.Range(start + a, start + b)
                if tag == "delete":
                    target.Delete()
                else:
                    target.Text = repl
            af_applied.append(item)
            
        # ---------------------------
        # C & D. Comment Execution
        # ---------------------------
        verified_comments = com_pre.get("verified_comments", [])
        
        # Group by rule_id
        comments_by_rule = defaultdict(list)
        for item in verified_comments:
            comments_by_rule[item["plan"]["rule_id"]].append(item)
            
        for rule_id, items in comments_by_rule.items():
            # Filter report-only/disabled based on policy? Wait, if they are in commentpreflight, they are disposition "comment".
            # The comment preflight only processes `plan.get("comment_plan", [])`.
            # So report-only and disabled are already excluded.
            
            # The comment_plan might already contain 'aggregated' logic but we must follow:
            # "If occurrence count is 1-4, insert comments at all verified eligible locations.
            # If occurrence count is 5 or more, insert one comment at the first verified eligible body-narrative location."
            
            # Re-evaluating the rule from verified entries:
            # Sort by range_start ascending
            items = sorted(items, key=lambda x: x["verified_range_start"])
            
            count = len(items)
            # Actually, the original comment_plan may have fewer items if it aggregated them already!
            # Let's check the original occurrence count from the plan
            orig_occurrence_count = items[0]["plan"].get("occurrence_count", count)
            
            if orig_occurrence_count >= 5:
                # Find first body-narrative
                selected = None
                for item in items:
                    if item["plan"]["finding"].get("Context", {}).get("content_zone") == "body_narrative":
                        selected = item
                        break
                if not selected:
                    # fallback to first if no body narrative?
                    selected = items[0]
                    
                start = selected["verified_range_start"]
                end = selected["verified_range_end"]
                rng = doc.Range(start, end)
                
                finding = selected["plan"]["finding"]
                severity = finding.get("Severity", "suggestion").upper()
                match_text = finding.get("Match", "")
                message = finding.get("Message", "")
                
                comment_text = f"[{orig_occurrence_count} occurrences] {rule_id} {severity} -> '{match_text}': {message}"
                
                try:
                    comment = doc.Comments.Add(Range=rng, Text=comment_text)
                    try:
                        comment.Author = "MVA"
                        comment.Initial = "MVA"
                    except Exception: pass
                    com_inserted.append(selected)
                    aggregated_comment_count += 1
                except Exception as e:
                    com_skipped.append({"item": selected, "reason": str(e)})
                    skipped_reasons["word_insertion_error"] += 1
            else:
                for item in items:
                    start = item["verified_range_start"]
                    end = item["verified_range_end"]
                    rng = doc.Range(start, end)
                    
                    finding = item["plan"]["finding"]
                    severity = finding.get("Severity", "suggestion").upper()
                    match_text = finding.get("Match", "")
                    message = finding.get("Message", "")
                    
                    comment_text = f"{rule_id} {severity} -> '{match_text}': {message}"
                    
                    try:
                        comment = doc.Comments.Add(Range=rng, Text=comment_text)
                        try:
                            comment.Author = "MVA"
                            comment.Initial = "MVA"
                        except Exception: pass
                        com_inserted.append(item)
                        inserted_comment_count += 1
                    except Exception as e:
                        com_skipped.append({"item": item, "reason": str(e)})
                        skipped_reasons["word_insertion_error"] += 1
                        
        doc.Save()

    finally:
        if doc is not None:
            doc.Close(SaveChanges=False)
        if word is not None:
            word.Quit()
        pythoncom.CoUninitialize()
        
    # ---------------------------
    # E. Output Validation
    # ---------------------------
    validation_result = "passed"
    mva_comment_count = 0
    pythoncom.CoInitialize()
    try:
        word_val = win32com.client.DispatchEx("Word.Application")
        word_val.Visible = False
        doc_val = None
        try:
            doc_val = word_val.Documents.Open(str(output_path.resolve()), ReadOnly=True)
            for c in doc_val.Comments:
                if c.Author == "MVA" or c.Initial == "MVA":
                    mva_comment_count += 1
        except Exception as e:
            validation_result = f"failed_to_open: {str(e)}"
        finally:
            if doc_val is not None:
                doc_val.Close(SaveChanges=False)
            word_val.Quit()
    except Exception as e:
        validation_result = f"failed_to_launch_word: {str(e)}"
    finally:
        pythoncom.CoUninitialize()

    # ---------------------------
    # F. Execution Artifacts
    # ---------------------------
    output_sha = calculate_sha256(output_path)
    
    af_execution = {
        "source_sha256": source_sha,
        "output_sha256": output_sha,
        "applied_count": len(af_applied),
        "skipped_count": len(af_skipped),
        "summary_comment_count": autofix_summary_comment_count,
        "summary_comments": af_summary_records,
        "applied": af_applied,
        "skipped": af_skipped
    }
    
    com_execution = {
        "source_sha256": source_sha,
        "output_sha256": output_sha,
        "inserted_count": inserted_comment_count,
        "aggregated_count": aggregated_comment_count,
        "skipped_count": len(com_skipped),
        "skipped_reasons": dict(skipped_reasons),
        "inserted": com_inserted,
        "skipped": com_skipped
    }
    
    out_verification = {
        "source_sha256": source_sha,
        "output_sha256": output_sha,
        "applied_auto_fix_count": len(af_applied),
        "skipped_auto_fix_count": len(af_skipped),
        "inserted_comment_count": inserted_comment_count,
        "aggregated_comment_count": aggregated_comment_count,
        "auto_fix_summary_comment_count": autofix_summary_comment_count,
        "skipped_comment_reasons": dict(skipped_reasons),
        "mva_comment_count": mva_comment_count,
        "output_validation_result": validation_result
    }

    af_path = output_base.with_suffix(".autofixexecution.json")
    af_path.write_text(json.dumps(af_execution, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    
    com_path = output_base.with_suffix(".commentexecution.json")
    com_path.write_text(json.dumps(com_execution, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    
    val_path = output_base.with_suffix(".outputverification.json")
    val_path.write_text(json.dumps(out_verification, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    
    return {
        "autofixexecution": af_path,
        "commentexecution": com_path,
        "outputverification": val_path
    }

