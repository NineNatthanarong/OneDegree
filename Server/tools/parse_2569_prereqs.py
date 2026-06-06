#!/usr/bin/env python3
"""
parse_2569_prereqs.py — build {course_code -> canonical prerequisite} from the
official 2569 School of Engineering curriculum PDF text (/tmp/eng2569.txt).

The PDF has two sections per course: a clean course-list TABLE
(`CODE Name credits prereq` with English codes) and a verbose course-DESCRIPTION
(long Thai/English prose, Thai-abbrev codes). To avoid description bleed we do
NOT store raw matched text — we extract the English course codes + the
concurrent flag from the prerequisite column and REBUILD a canonical string:

    สอบได้ <A>                          (must-pass)
    สอบได้ <A> และ <B>                  (must-pass both)
    สอบได้ <A> หรือ <B>                 (must-pass either)
    สอบได้ <A> หรือเรียนควบคู่กัน        (must-pass-or-parallel)
    เคยเรียน <A>                        (must-pass, "have taken")
    -                                  (none)

Among the multiple table/description occurrences of a code, the cleanest
code-based value wins.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

SRC = Path("/tmp/eng2569.txt")
OUT = Path("/tmp/prereq_2569_map.json")

# A real row-start is a course code followed by an English NAME word. A line that
# is "MA 107 หรือเรียนควบคู่..." (code followed by Thai) is a prereq continuation,
# NOT a new row, so requiring an English name after the code stops AND/OR clauses
# from being split across rows.
ROW = re.compile(r"^([A-Z]{2,4})\s?(\d{3})\s+([A-Za-z(].*)$")
KW = re.compile(r"(สอบได้|เคยเรียน|ผ่าน|บุรพวิชา)")
CODE = re.compile(r"[A-Z]{2,4}\s*\d{3}")
# the canonical prereq run: keyword then codes/connectives/concurrent tokens only
RUN = re.compile(
    r"(สอบได้|เคยเรียน)((?:\s*(?:[A-Z]{2,4}\s*\d{3}|และ|หรือเรียนควบคู่กัน|"
    r"หรือ\s*เรียน\s*ควบคู่\s*กัน|ควบคู่\s*กัน|ควบคู่|หรือ|เรียน|กัน))+)"
)


def norm(c: str) -> str:
    return re.sub(r"\s+", "", c).upper()


def spaced(code_nospace: str) -> str:
    m = re.match(r"([A-Z]{2,4})(\d{3})", code_nospace)
    return f"{m.group(1)} {m.group(2)}" if m else code_nospace


def canonical(block: str) -> str | None:
    """Return a clean canonical prereq for this row block, or None if unknown."""
    m = RUN.search(block)
    if m:
        kw = m.group(1)
        run = m.group(2)
        codes = [norm(c) for c in CODE.findall(run)]
        # dedupe preserve order
        seen, uniq = set(), []
        for c in codes:
            if c not in seen:
                seen.add(c)
                uniq.append(c)
        concurrent = "ควบคู่" in run
        if not uniq:
            return None
        joiner = " และ " if "และ" in run else " หรือ "
        body = joiner.join(spaced(c) for c in uniq)
        out = f"{kw} {body}"
        if concurrent:
            out += " หรือเรียนควบคู่กัน"
        return out
    # Non-code requirements (approval / year-standing) only belong to specific
    # course types. Gate by THIS course's own name (before the credits column) to
    # avoid bleed-in from neighbouring rows contaminating e.g. ME 153.
    namepart = re.split(r"\s\d\s", block, 1)[0]
    if "Cooperative" in namepart and re.search(r"\bCO\s*301\b", block):
        return "สอบได้ CO 301"
    if ("Selected Topics" in namepart or "Special Problems" in namepart) and "อนุมัติ" in block:
        return "ผ่านรายวิชาที่กำหนดและได้รับอนุมัติจากหัวหน้าภาควิชา"
    if "Project" in namepart and re.search(r"นักศึกษาชั้นปีที่\s*\d", block):
        return "เป็นนักศึกษาชั้นปีที่ 4 และได้รับอนุมัติจากผู้สอน"
    return None


def score(pre: str) -> int:
    """Prefer clean code-based prereqs; concurrent/AND/OR are all fine."""
    if pre is None:
        return -1
    if CODE.search(pre):
        return 3
    if pre.startswith(("ผ่าน", "เป็นนักศึกษา")):
        return 1
    return 0


def main() -> None:
    lines = SRC.read_text().splitlines()
    rows: list[tuple[str, str]] = []
    cur, buf = None, []
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        m = ROW.match(line)
        if m and not KW.match(line):
            if cur:
                rows.append((cur, " ".join(buf)))
            cur = f"{m.group(1)} {m.group(2)}"
            buf = [m.group(3).strip()]
        elif cur:
            buf.append(line)
    if cur:
        rows.append((cur, " ".join(buf)))

    best: dict[str, str] = {}
    for code, block in rows:
        pre = canonical(block)
        key = norm(code)
        if pre is None:
            best.setdefault(key, "-")
            continue
        if key not in best or score(pre) > score(best[key]):
            best[key] = pre

    OUT.write_text(json.dumps(best, ensure_ascii=False, indent=2))
    real = {k: v for k, v in best.items() if v not in ("-", "—")}
    print(f"codes: {len(best)}   with real prereq: {len(real)}")
    print("\n--- verify previously-messy codes ---")
    for k in ["CE331", "CE334", "CE335", "EL253", "EL215", "MA109", "MA108",
              "AIE321", "EL454", "CE437", "PH106", "AIE412"]:
        print(f"  {k:7}: {best.get(k, '(absent)')}")
    print("\n--- all code-based prereqs (sorted) ---")
    for k in sorted(real):
        if CODE.search(real[k]):
            print(f"  {k:7}: {real[k]}")
    print(f"\n--- non-code requirements ---")
    for k in sorted(real):
        if not CODE.search(real[k]):
            print(f"  {k:7}: {real[k]}")


if __name__ == "__main__":
    main()
