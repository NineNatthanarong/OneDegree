#!/usr/bin/env python3
"""
reshape_years.py — set the dataset year range to 2564-2569.

  1. Delete academic year 2563 entirely (curricula + metadata).
  2. Make 2569 a full year: keep its real (PDF-sourced) school-of-engineering,
     and add the other 11 faculties by carrying them forward from 2568 — the
     most recent full year, whose prerequisites are already corrected
     (default maps = 0 conflicts). Engineering 2569 is NOT overwritten.
  3. Update metadata.academic_years.

Idempotent: re-running only adds faculties that are missing from 2569.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE.parent / "curriculum_database.json"
ENG = "school-of-engineering"


def main() -> None:
    db = json.loads(DB.read_bytes())
    cur = db["curricula"]

    # 1. delete 2563
    removed_2563 = cur.pop("2563", None) is not None

    # 2. carry forward 2568's non-engineering faculties into 2569
    src = cur["2568"]["faculties"]
    dst = cur["2569"]["faculties"]
    added = []
    for fslug, fac in src.items():
        if fslug == ENG:
            continue  # keep the real 2569 engineering
        if fslug not in dst:
            dst[fslug] = copy.deepcopy(fac)
            added.append(fslug)

    # 3. metadata: keep 2564-2569, drop 2563
    keep = [y for y in db["metadata"].get("academic_years", []) if y != "2563"]
    if "2569" not in keep:
        keep = ["2569"] + keep
    db["metadata"]["academic_years"] = sorted(keep, reverse=True)
    db["metadata"]["faculty_count"] = len(dst)

    DB.write_text(json.dumps(db, ensure_ascii=False, indent=2))
    print(f"deleted 2563: {removed_2563}")
    print(f"2569 faculties added (carried from 2568): {len(added)}")
    for f in added:
        print(f"   + {f}")
    print(f"year keys now: {sorted(cur.keys())}")
    print(f"2569 faculty count now: {len(dst)}")
    print(f"metadata.academic_years: {db['metadata']['academic_years']}")


if __name__ == "__main__":
    main()
