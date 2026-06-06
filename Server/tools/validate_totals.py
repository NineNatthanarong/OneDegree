"""
Validate extracted study-plan credits against the PDF's own printed semester
total rows.

Strategy:
  1. Run the (block-aware) extractor to get structured data; compute per
     dept/year/semester/column credit sums.
  2. Independently scan the PDF for printed total rows (all-numeric rows under
     each table) and read their six column values by x-position.
  3. Compare. Any column where extracted sum != printed total is a real
     attribution error to investigate.
"""
import os
import re
import sys
import argparse

import pdfplumber

sys.path.insert(0, os.path.dirname(__file__))
from extract_eng_plans import (  # noqa: E402
    extract, group_rows, row_text, find_column_centers, is_total_row,
    assign_credits, merge_block_rows, classify_row,
    COL_SPEC, COL_TOL, SEM_FIRST, SEM_SECOND, SEM_SUMMER,
)


def read_total_row(row, centers, tol=COL_TOL):
    vals = [None] * 6
    for w in row["words"]:
        if not re.fullmatch(r"\d+", w["text"]):
            continue
        cx = (w["x0"] + w["x1"]) / 2
        best, bestd = None, tol
        for i, c in enumerate(centers):
            d = abs(cx - c)
            if d < bestd:
                best, bestd = i, d
        if best is not None:
            vals[best] = int(w["text"])
    return vals


def collect_printed_totals(pdf_path):
    """Return dict (dept,year,sem) -> list[6] of summed printed totals.

    Mirrors the extractor's block tracking so that an all-digit row is only
    counted as a semester total when it is NOT supplying credits to a pending
    multi-line course."""
    pdf = pdfplumber.open(pdf_path)
    cur_dept = cur_year = cur_sem = None
    centers = None
    in_plan = False
    totals = {}

    for page in pdf.pages:
        rows = group_rows(page.extract_words(use_text_flow=False, keep_blank_chars=False))
        if not rows:
            continue
        header = " ".join(row_text(r) for r in rows[:2])
        if header.startswith("แผนการศึกษาตามหลักสูตร"):
            in_plan = True
        if not in_plan:
            continue
        if header.startswith("คำอธิบายรายวิชา"):
            break
        pc = find_column_centers(rows)
        if pc:
            centers = pc

        pending = []

        def block_has_cred():
            return bool(pending) and any(
                c is not None for c in assign_credits(merge_block_rows(pending, centers), centers)
            )

        for r in rows:
            txt = row_text(r).strip()
            if txt.startswith("สาขา"):
                pending.clear(); cur_dept, cur_year, cur_sem = txt, None, None; continue
            m = re.match(r"^ชั้นปีที่\s*(\d+)", txt)
            if m:
                pending.clear(); cur_year, cur_sem = m.group(1), None; continue
            if txt.startswith("First Semester"):
                pending.clear(); cur_sem = SEM_FIRST; continue
            if txt.startswith("Second Semester"):
                pending.clear(); cur_sem = SEM_SECOND; continue
            if txt.startswith("Summer"):
                pending.clear(); cur_sem = SEM_SUMMER; continue
            if "หน่วยกิต" in txt or txt.startswith("Course") or txt.startswith("รุ่น"):
                pending.clear(); continue
            if txt.startswith("ปกต") or txt == "สหกิจ":
                pending.clear(); continue
            if "หลักสูตรปริญญาตรี" in txt and "ปีการศึกษา" in txt:
                pending.clear(); continue
            if not (centers and cur_dept and cur_year and cur_sem):
                continue

            if is_total_row(r, centers):
                if pending and not block_has_cred():
                    pending.append(r)  # multi-line course credits, not a total
                else:
                    # genuine semester total
                    vals = read_total_row(r, centers)
                    key = (cur_dept, cur_year, cur_sem)
                    acc = totals.setdefault(key, [0, 0, 0, 0, 0, 0])
                    for i in range(6):
                        if vals[i] is not None:
                            acc[i] += vals[i]
                    pending.clear()
                continue

            if classify_row(r, centers) == "start" and pending:
                pending.clear()
            pending.append(r)
    return totals


def extracted_sums(data):
    sums = {}
    col_index = {cs: i for i, cs in enumerate(COL_SPEC)}
    for dept, plans in data.items():
        for plan, cohorts in plans.items():
            for cohort, years in cohorts.items():
                ci = col_index[(cohort, plan)]
                for ylvl, sems in years.items():
                    for sem, courses in sems.items():
                        key = (dept, ylvl, sem)
                        acc = sums.setdefault(key, [0, 0, 0, 0, 0, 0])
                        acc[ci] += sum(c["credits"] for c in courses)
    return sums


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    args = ap.parse_args()
    data = extract(args.pdf)
    esums = extracted_sums(data)
    ptot = collect_printed_totals(args.pdf)
    keys = sorted(set(esums) | set(ptot))
    problems = []
    for key in keys:
        e = esums.get(key, [0] * 6)
        p = ptot.get(key, [0] * 6)
        for i in range(6):
            if e[i] != p[i]:
                problems.append((key, COL_SPEC[i], e[i], p[i]))
    if not problems:
        print("OK: all printed semester totals match extracted per-column sums.")
        return
    print(f"{len(problems)} mismatches vs printed totals:")
    for (key, col, e, p) in problems:
        dept, yr, sem = key
        print(f"  {dept[:30]} yr{yr} sem{sem} | {col} | extracted={e} printed={p}")


if __name__ == "__main__":
    main()
