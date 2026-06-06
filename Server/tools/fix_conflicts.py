#!/usr/bin/env python3
"""
fix_conflicts.py — apply data corrections for every default-map conflict found by
validate_default_map.py, using /tmp/conflicts.json as the targeting source.

Two fix classes:
  CO-REQ  (same-semester must-pass that should be must-pass-OR-parallel):
          append "หรือเรียนควบคู่กัน" so the web parser treats it as concurrent.
          Applied only within the (year, faculty, department) where it was flagged,
          across every plan/cohort/semester object AND the course_index.

  LATER   (prereq impossibly scheduled after the course = PDF-extraction corruption):
          replace the corrupted prerequisite with the correct value. Applied GLOBALLY
          wherever the corrupted pattern appears (it is wrong everywhere it occurs):
            MK 101  "...FI 212..."        -> "-"             (Y1S1 intro Marketing; no prereq)
            CE 437  "...IE 325..."        -> "สอบได้ IE 211"  (drop the later IE 325 + truncated text)
            MI 328  "...MI 481/MI 498..." -> "สอบได้ MI 317"  (drop merged later-course junk)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "curriculum_database.json"
CONF = Path("/tmp/conflicts_all.json")
CONCURRENT = " หรือเรียนควบคู่กัน"


def norm(c: str | None) -> str:
    return re.sub(r"\s+", "", c or "").upper()


# ----- classify every violation: same-sem CO-REQ vs LATER (placement) -----
conf = json.loads(CONF.read_text())
coreq: dict[tuple, set] = {}     # (year,faculty,dept) -> {normcode}  (same-sem co-reqs)
flagged: list = []               # LATER cases not covered by a global pattern fix
LATER_CODES = {"MK101", "CE437", "MI328"}

for r in conf["results"]:
    key = (r["year"], r["faculty"], r["department"])
    for v in r["violations"]:
        code = norm(v["course_code"])
        alts = [a for a in v["alts"] if a.get("in_plan")]
        has_later = any(a.get("rel") == "later" for a in alts)
        if has_later:
            if code not in LATER_CODES:
                flagged.append((r["year"], r["faculty"], r["department"],
                                v["course_code"], v["prerequisite"]))
            continue  # MK101/CE437/MI328 handled by global pattern fix
        coreq.setdefault(key, set()).add(code)  # same-sem -> make concurrent


# ----- global pattern fixes for the LATER (corruption) cases -----
def apply_later(code_n: str, obj: dict) -> bool:
    pre = obj.get("prerequisite") or ""
    pre_n = norm(pre)
    new = None
    if code_n == "MK101" and "FI212" in pre_n:
        new = ("-", "none", [])
    elif code_n == "CE437" and "IE325" in pre_n:
        new = ("สอบได้ IE 211", "must_pass", ["IE 211"])
    elif code_n == "MI328" and ("MI481" in pre_n or "MI498" in pre_n):
        new = ("สอบได้ MI 317", "must_pass", ["MI 317"])
    if new is None:
        return False
    pre_new, typ, courses = new
    if obj.get("prerequisite") == pre_new:
        return False
    obj["prerequisite"] = pre_new
    if "prerequisite_type" in obj:
        obj["prerequisite_type"] = typ
    if "prerequisite_courses" in obj:
        obj["prerequisite_courses"] = courses
    return True


def apply_coreq(code_n: str, obj: dict, key: tuple) -> bool:
    if code_n not in coreq.get(key, set()):
        return False
    pre = obj.get("prerequisite") or ""
    if not pre or pre.strip() in ("-", "—") or "ควบคู่" in pre:
        return False
    obj["prerequisite"] = pre + CONCURRENT
    if "prerequisite_type" in obj:
        obj["prerequisite_type"] = "concurrent_ok"
    return True


def fix_obj(code: str | None, obj: dict, year: str, fac: str, dept: str) -> int:
    code_n = norm(code)
    if code_n in LATER_CODES:
        return 1 if apply_later(code_n, obj) else 0
    return 1 if apply_coreq(code_n, obj, (year, fac, dept)) else 0


# ----- walk the DB -----
db = json.loads(DB.read_bytes())
changed = 0
for year, ydata in db.get("curricula", {}).items():
    for fac, facd in ydata.get("faculties", {}).items():
        for dept, deptd in facd.get("departments", {}).items():
            for track in deptd.get("tracks", {}).values():
                for ccode, entry in track.get("course_index", {}).items():
                    changed += fix_obj(ccode, entry, year, fac, dept)
                for plan in track.get("plan_types", {}).values():
                    for cohort in plan.get("cohorts", {}).values():
                        for yl in cohort.get("year_levels", {}).values():
                            for sem in yl.get("semesters", {}).values():
                                for course in sem:
                                    changed += fix_obj(course.get("course_code"), course, year, fac, dept)

DB.write_text(json.dumps(db, ensure_ascii=False, indent=2))
print(f"fix_conflicts: updated {changed} prerequisite field(s)")
if flagged:
    print(f"\nFLAGGED (alt-cohort placement issues — prereq kept as must-pass, not auto-changed; {len(flagged)}):")
    seen = set()
    for y, f, d, c, p in flagged:
        sig = (c, p)
        if sig in seen:
            continue
        seen.add(sig)
        print(f"   {y} {f} · {c}: «{p}» (prereq scheduled later in a non-default cohort)")
