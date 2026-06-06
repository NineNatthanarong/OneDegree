#!/usr/bin/env python3
"""
apply_prereq_fixes.py — apply verified prerequisite corrections to
curriculum_database.json, editing BOTH the semester course objects and the
matching course_index entries, in-place, idempotently.

Fix file format (JSON):
{
  "fixes": [
    {
      "years": ["2568", "2569"],          // or "all"
      "faculty": "school-of-accounting",  // optional; matches faculty slug
      "course_code": "AC 205",            // matched space-insensitively
      "set_prerequisite": "สอบได้ AC 204 หรือเรียนควบคู่กัน",
      "reason": "co-req per degreeplan.bu.ac.th"
    }
  ]
}

Two prerequisite kinds (per the web parser Web/lib/prereq.ts):
  must-pass            -> "สอบได้ <CODE>"               (parsed kind: pass)
  must-pass-or-parallel-> "สอบได้ <CODE> หรือเรียนควบคู่กัน" (parsed kind: concurrent)

Run:
  python3 tools/apply_prereq_fixes.py fixes.json            # apply
  python3 tools/apply_prereq_fixes.py fixes.json --dry-run  # preview only
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DB_PATH = HERE.parent / "curriculum_database.json"


def norm(code: str | None) -> str:
    return re.sub(r"\s+", "", code or "").upper()


def years_match(fix_years, year: str) -> bool:
    if fix_years == "all" or fix_years is None:
        return True
    return year in fix_years


def apply_fixes(db: dict[str, Any], fixes: list[dict[str, Any]], dry: bool) -> int:
    curricula = db.get("curricula", {})
    changed = 0
    log: list[str] = []

    for fix in fixes:
        want_code = norm(fix["course_code"])
        new_pre = fix["set_prerequisite"]
        fac_filter = fix.get("faculty")
        fyears = fix.get("years", "all")
        hits = 0

        for year, ydata in curricula.items():
            if not years_match(fyears, year):
                continue
            for fslug, fac in ydata.get("faculties", {}).items():
                if fac_filter and fslug != fac_filter:
                    continue
                for dept in fac.get("departments", {}).values():
                    for track in dept.get("tracks", {}).values():
                        # course_index entries
                        ci = track.get("course_index", {})
                        for code, entry in ci.items():
                            if norm(code) == want_code and entry.get("prerequisite") != new_pre:
                                if not dry:
                                    entry["prerequisite"] = new_pre
                                hits += 1
                        # semester course objects
                        for plan in track.get("plan_types", {}).values():
                            for cohort in plan.get("cohorts", {}).values():
                                for ylvl in cohort.get("year_levels", {}).values():
                                    for sem in ylvl.get("semesters", {}).values():
                                        for course in sem:
                                            if norm(course.get("course_code")) == want_code \
                                               and course.get("prerequisite") != new_pre:
                                                if not dry:
                                                    course["prerequisite"] = new_pre
                                                    course.pop("prerequisite_type", None)
                                                    course.pop("prerequisite_courses", None)
                                                hits += 1
        changed += hits
        log.append(f"  {fix['course_code']:>10}  ({fyears}, fac={fac_filter or '*'})  "
                   f"-> {hits} field(s)   « {new_pre} »   [{fix.get('reason','')}]")

    print("FIX REPORT" + (" (dry-run)" if dry else ""))
    print("\n".join(log))
    print(f"total fields {'would change' if dry else 'changed'}: {changed}")
    return changed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("fixes")
    ap.add_argument("--db", default=str(DB_PATH))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    db = json.loads(Path(args.db).read_bytes())
    fixes = json.loads(Path(args.fixes).read_text())["fixes"]

    changed = apply_fixes(db, fixes, args.dry_run)

    if changed and not args.dry_run:
        Path(args.db).write_text(json.dumps(db, ensure_ascii=False, indent=2))
        print(f"wrote {args.db}")
    elif not changed:
        print("no changes needed (already up to date)")


if __name__ == "__main__":
    main()
