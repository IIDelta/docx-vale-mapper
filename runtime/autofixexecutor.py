from __future__ import annotations

import difflib
import json
import shutil
from collections import defaultdict
from pathlib import Path

from abbreviations.legacyimport import calculate_sha256
from validators.fieldprotection import protected_field_ranges, ranges_overlap


def replacement_operations(match: str, replacement: str) -> list[tuple[str, int, int, str]]:
    operations=[]
    for tag, start, end, replacement_start, replacement_end in difflib.SequenceMatcher(None, match, replacement).get_opcodes():
        if tag != "equal": operations.append((tag,start,end,replacement[replacement_start:replacement_end]))
    return operations


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
        items=sorted(pre["verified_auto_fixes"], key=lambda x:x["verified_range_start"], reverse=True)
        first_by_rule={}
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
            first_by_rule.setdefault(item["rule_id"], item)
        for rule,item in first_by_rule.items():
            count=sum(1 for x in applied if x["rule_id"]==rule)
            rng=doc.Range(item["verified_range_start"], item["verified_range_start"]+len(item["replacement"]))
            comment=doc.Comments.Add(Range=rng,Text=f"Automatically applied {count} verified {rule} fix(es) throughout this document. See autofix execution JSON for all locations.")
            comment.Author="MVA"; comment.Initial="MVA"
        doc.Save()
    finally:
        if doc is not None: doc.Close(SaveChanges=False)
        if word is not None: word.Quit()
        pythoncom.CoUninitialize()
    result={"source_sha256":calculate_sha256(source),"output_sha256":calculate_sha256(output),"applied_count":len(applied),"skipped_count":len(skipped),"summary_comment_count":len(first_by_rule),"applied":applied,"skipped":skipped}
    path=output.with_suffix(".autofixexecution.json"); path.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    return path
