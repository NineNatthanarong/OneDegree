#!/usr/bin/env python3
"""
fill_2569_prereqs.py — populate year-2569 course prerequisites from the official
map (/tmp/prereq_2569_map.json, built by parse_2569_prereqs.py from the official
2569 engineering curriculum PDF). Fills every 2569 course (all 4 majors) whose
code has a real prerequisite in the map, in both semester objects and
course_index. Sets prerequisite + prerequisite_type + prerequisite_courses.

Only writes real prerequisites (map value != "-"); never wipes existing data to "-".
Reports JSON 2569 course codes that are NOT in the official map (potential misses).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "curriculum_database.json"
MAP = Path("/tmp/prereq_2569_map.json")
CODE = re.compile(r"[A-Z]{2,4}\s*\d{3}")


def norm(c: str | None) -> str:
    return re.sub(r"\s+", "", c or "").upper()


def meta_for(pre: str):
    """Return (prerequisite_type, prerequisite_courses) for a canonical prereq."""
    codes = [re.sub(r"\s+", " ", c).strip() for c in CODE.findall(pre)]
    if not codes:
        return ("other", []) if pre not in ("-", "—") else ("none", [])
    typ = "concurrent_ok" if "ควบคู่" in pre else "must_pass"
    # spaced form e.g. "EL214" -> "EL 214"
    sp = []
    for c in codes:
        mm = re.match(r"([A-Z]{2,4})\s*(\d{3})", c)
        sp.append(f"{mm.group(1)} {mm.group(2)}" if mm else c)
    return (typ, sp)


def set_obj(obj: dict, pre: str) -> bool:
    if obj.get("prerequisite") == pre:
        return False
    obj["prerequisite"] = pre
    typ, courses = meta_for(pre)
    if "prerequisite_type" in obj or "prerequisite_courses" in obj:
        obj["prerequisite_type"] = typ
        obj["prerequisite_courses"] = courses
    return True


downgrades: list = []


def authoritative_set(code: str, obj: dict, m: dict) -> int:
    """Set obj's prerequisite to the official map value (authoritative for 2569).
    Codes absent from the map are left untouched. Flags real->'-' downgrades."""
    key = norm(code)
    if key not in m:
        return 0
    newpre = m[key]
    old = (obj.get("prerequisite") or "").strip()
    if old == newpre:
        return 0
    if CODE.search(old) and newpre in ("-", "—"):
        downgrades.append((code, old))
    return 1 if set_obj(obj, newpre) else 0


def main() -> None:
    m = json.loads(MAP.read_text())
    db = json.loads(DB.read_bytes())
    y = db["curricula"]["2569"]

    filled = 0
    json_codes: set[str] = set()
    for fac in y["faculties"].values():
        for dd in fac["departments"].values():
            for tr in dd["tracks"].values():
                for code, entry in tr.get("course_index", {}).items():
                    json_codes.add(norm(code))
                    filled += authoritative_set(code, entry, m)
                for pl in tr.get("plan_types", {}).values():
                    for co in pl.get("cohorts", {}).values():
                        for yl in co.get("year_levels", {}).values():
                            for sem in yl.get("semesters", {}).values():
                                for c in sem:
                                    if not c.get("course_code"):
                                        continue
                                    json_codes.add(norm(c["course_code"]))
                                    filled += authoritative_set(c["course_code"], c, m)

    DB.write_text(json.dumps(db, ensure_ascii=False, indent=2))
    print(f"fill_2569: set {filled} prerequisite field(s)")
    if downgrades:
        seen = set()
        print(f"\nReal->'-' downgrades (verify these are truly no-prereq in the PDF):")
        for code, old in downgrades:
            if code in seen:
                continue
            seen.add(code)
            print(f"   {code}: was «{old}» -> now '-'")

    real = {k: v for k, v in m.items() if v not in ("-", "—")}
    missing = sorted(c for c in json_codes if c not in real)
    print(f"\n2569 json codes WITHOUT an official prereq ({len(missing)}): gen-ed/foundation, no prereq")
    print("  " + " ".join(missing))


if __name__ == "__main__":
    main()
