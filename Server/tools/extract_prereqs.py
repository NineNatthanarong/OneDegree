"""
Extract course prerequisites from the BU engineering course-list section
("รายชื่อวิชา ... วิชาบังคับก่อน หรือพื้นความรู้").

Layout per row (positions in points):
  code (~x81) | course title (~x127-300) | credits (~x374) | prerequisite (~x469+)

Prerequisite text wraps onto following indented rows (no code, no credit).
A value of "-" means no prerequisite.

Output: dict (dept_th -> {course_code -> prerequisite_string}).
Course codes are normalized to the "XX 123" spaced form used by the JSON.
"""
import os
import re
import sys
import json
import argparse

import pdfplumber

sys.path.insert(0, os.path.dirname(__file__))
from extract_eng_plans import group_rows, row_text, norm_code  # noqa: E402

# x-threshold separating the prerequisite column from title/credit columns.
PREREQ_X_MIN = 450.0
CODE_X_MAX = 120.0


def is_dept_header(txt):
    return txt.startswith("สาขาวิชา") or txt.startswith("สาขา")


def clean_prereq(s):
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_prereqs(pdf_path):
    pdf = pdfplumber.open(pdf_path)
    result = {}
    cur_dept = None
    cur = None                # (dept, code) currently accumulating prereq
    cur_prereq = []

    def flush():
        nonlocal cur, cur_prereq
        if cur is not None:
            dept, code = cur
            val = clean_prereq(" ".join(cur_prereq))
            if val and val not in ("-", "–", "—"):
                result.setdefault(dept, {})[code] = val
            else:
                result.setdefault(dept, {}).setdefault(code, "-")
        cur, cur_prereq = None, []

    for page in pdf.pages:
        rows = group_rows(page.extract_words(use_text_flow=False, keep_blank_chars=False))
        if not rows:
            continue
        # Only process course-list pages (table with "วิชาบังคับก่อน" column header).
        # Skip study-plan pages (semester schedule tables with "First Semester" / "รุ่น").
        # Skip course description pages ("วิชาบังคับก่อน :" as a field label).
        page_text = " ".join(row_text(r) for r in rows)
        if "วิชาบังคับก่อน" not in page_text:
            continue
        if "วิชาบังคับก่อน :" in page_text or "วิชาบังคับก่อน:" in page_text:
            continue  # description section, not course-list table
        if ("First Semester" in page_text and "รุ่น" in page_text) or ("Second Semester" in page_text and "รุ่น" in page_text):
            continue  # study-plan table (semester schedule)

        for r in rows:
            txt = row_text(r).strip()
            if is_dept_header(txt):
                flush()
                # capture dept name token(s)
                if "วิศวกรรม" in txt:
                    cur_dept = txt
                continue
            # detect a dept name that appears as the first line of a listing page
            if txt.startswith("รายชื่อวิชา") and "วิศวกรรม" in txt:
                continue

            ws = r["words"]
            if not ws:
                continue
            first = ws[0]
            code = norm_code(first["text"]) if first["x0"] <= CODE_X_MAX else None

            # Words in the prerequisite column on this row.
            pre_words = [w["text"] for w in ws if w["x0"] >= PREREQ_X_MIN]

            if code:
                # New course row: close previous, start new.
                flush()
                cur = (cur_dept, code)
                cur_prereq = pre_words[:]  # may be empty or '-'
            else:
                # Continuation: append prereq-column words (title wraps ignored).
                if cur is not None and pre_words:
                    cur_prereq.extend(pre_words)
        # page end keeps cur open (course may continue) — but dept rarely splits
    flush()
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out")
    args = ap.parse_args()
    data = extract_prereqs(args.pdf)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.out:
        open(args.out, "w").write(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
