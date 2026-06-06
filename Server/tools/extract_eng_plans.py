"""
Extract engineering study-plan tables from BU degree-plan PDFs (position-based).

The study-plan section lists, per dept / year (ชั้นปีที่ N) / semester
(First, Second, Summer), a table whose six right-hand columns are:

    รุ่น 1/1 ปกติ | รุ่น 1/1 สหกิจ | รุ่น 1/2 ปกติ | รุ่น 1/2 สหกิจ | รุ่น 2 ปกติ | รุ่น 2 สหกิจ

A course belongs to a (cohort, plan) only where it carries a credit value in
that column. pdfplumber's extract_tables() returns inconsistent column counts
across pages, so we instead assign each credit digit to a column by its
x-coordinate, which is stable to <1pt.

Output schema (matches curriculum_database.json):
    dept -> plan_type -> cohort -> year -> semester -> [ {course_code, course_name, credits, prerequisite} ]
"""
import sys
import re
import json
import argparse

import pdfplumber


# Plan/cohort columns, left to right, with their digit x-centers.
# Centers are learned per page from the header, but these are the defaults/order.
COL_SPEC = [
    ("รุ่น 1/1", "ปกติ"),
    ("รุ่น 1/1", "สหกิจ"),
    ("รุ่น 1/2", "ปกติ"),
    ("รุ่น 1/2", "สหกิจ"),
    ("รุ่น 2", "ปกติ"),
    ("รุ่น 2", "สหกิจ"),
]

SEM_FIRST, SEM_SECOND, SEM_SUMMER = "1", "2", "3"

CODE_RE = re.compile(r"^([A-Z]{2,3})\s?(\d{3})$")
COL_TOL = 12.0  # max distance (pt) from a column center to count as that column


def norm_code(raw):
    raw = re.sub(r"\s+", " ", (raw or "").strip())
    m = CODE_RE.match(raw)
    return f"{m.group(1)} {m.group(2)}" if m else None


def group_rows(words, ytol=3.5):
    """Group extracted words into visual rows by their 'top' coordinate."""
    rows = []
    for w in sorted(words, key=lambda x: (x["top"], x["x0"])):
        placed = False
        for r in rows:
            if abs(r["top"] - w["top"]) <= ytol:
                r["words"].append(w)
                r["top"] = (r["top"] * r["n"] + w["top"]) / (r["n"] + 1)
                r["n"] += 1
                placed = True
                break
        if not placed:
            rows.append({"top": w["top"], "n": 1, "words": [w]})
    for r in rows:
        r["words"].sort(key=lambda x: x["x0"])
    rows.sort(key=lambda r: r["top"])
    return rows


def row_text(row):
    return " ".join(w["text"] for w in row["words"])


def find_column_centers(rows):
    """Locate the six credit-column x-centers from the 'ปกติ/สหกิจ' header row."""
    for r in rows:
        labels = [w for w in r["words"] if w["text"].startswith("ปกต") or w["text"] == "สหกิจ"]
        if len(labels) == 6:
            return [round((w["x0"] + w["x1"]) / 2, 1) for w in labels]
    return None


def assign_credits(row, centers):
    """Return list of 6 credit values (or None) for a data row, by x-position.

    Only single-digit (1-9) tokens are treated as credits; multi-digit tokens
    such as page numbers (36) or academic years (2568) are ignored.
    """
    creds = [None] * 6
    for w in row["words"]:
        if not re.fullmatch(r"\d", w["text"]):
            continue
        cx = (w["x0"] + w["x1"]) / 2
        # nearest column center within tolerance
        best, bestd = None, COL_TOL
        for i, c in enumerate(centers):
            d = abs(cx - c)
            if d < bestd:
                best, bestd = i, d
        if best is not None:
            creds[best] = int(w["text"])
    return creds


def course_parts(row, centers):
    """Split a (possibly merged) course block into (code, title).

    Words whose center sits within a credit column are excluded (they are
    credits). The course code may appear anywhere among the left-zone words
    (some PDFs print the code on the line BELOW the title), so we scan all
    left-zone tokens for a code pattern (single token, or an adjacent
    'XX'+'123' pair). 'XXxxx' / 'XXXX' is the elective placeholder -> code None.
    """
    left_bound = min(centers) - COL_TOL
    lz = [w["text"] for w in row["words"] if (w["x0"] + w["x1"]) / 2 < left_bound]

    code = None
    code_span = None  # (i) or (i, i+1) indices consumed as the code
    # elective placeholder?
    for i, t in enumerate(lz):
        if t == "XXxxx" or t.lower() in ("xxxxx", "xxxx") or re.fullmatch(r"[Xx]{2,}", t):
            code_span = (i,)
            break
    if code_span is None:
        # single-token code
        for i, t in enumerate(lz):
            c = norm_code(t)
            if c:
                code, code_span = c, (i,)
                break
    if code_span is None:
        # adjacent two-token code ('EE' '211')
        for i in range(len(lz) - 1):
            c = norm_code(lz[i] + " " + lz[i + 1])
            if c:
                code, code_span = c, (i, i + 1)
                break

    drop = set(code_span) if code_span else set()
    title_words = [t for i, t in enumerate(lz) if i not in drop]
    title = re.sub(r"\s+", " ", " ".join(title_words)).strip()
    return code, title


def row_first_x0(row):
    return row["words"][0]["x0"] if row["words"] else 9999


# A logical course may wrap across several visual rows. We classify each
# visual row to decide whether it starts a new course or continues the
# current one:
#   - START      : a left-margin code/elective row, OR an indented row that
#                  carries its own credits (an elective like "Major Elective").
#   - CONTINUATION: a credits-only row (no code/title text), or an indented
#                  title-wrap row with no credits.
LEFT_MARGIN_MAX = 95.0


def has_any_credit(row, centers):
    for w in row["words"]:
        if not re.fullmatch(r"\d", w["text"]):
            continue
        cx = (w["x0"] + w["x1"]) / 2
        if any(abs(cx - c) < COL_TOL for c in centers):
            return True
    return False


def left_zone_words(row, centers):
    left_bound = min(centers) - COL_TOL
    return [w for w in row["words"] if (w["x0"] + w["x1"]) / 2 < left_bound]


def classify_row(row, centers):
    """Return 'start' or 'continuation' for a data row within a table."""
    lz = left_zone_words(row, centers)
    if not lz:
        return "continuation"  # credits-only row -> belongs to current course
    x0 = lz[0]["x0"]
    if x0 <= LEFT_MARGIN_MAX:
        return "start"  # code or elective placeholder at the margin
    # Indented left text: a new elective if it carries its own credits,
    # otherwise a wrapped title line.
    return "start" if has_any_credit(row, centers) else "continuation"


def merge_block_rows(rows, centers):
    """Merge a course's wrapped visual rows into one synthetic row (word list)."""
    words = []
    for r in rows:
        words.extend(r["words"])
    words.sort(key=lambda w: (w["top"], w["x0"]))
    return {"top": rows[0]["top"], "words": words}


def is_total_row(row, centers):
    """A printed semester total row: every token is a number or a '-' placeholder
    (older PDFs print '-' for "not offered"), and none sits in the code/title
    area (all are near or right of the first credit column)."""
    ws = row["words"]
    if not ws:
        return False
    if not all(re.fullmatch(r"\d+|[-–—]", w["text"]) for w in ws):
        return False
    # Must contain at least one digit (a row of only dashes is not a total).
    if not any(re.fullmatch(r"\d+", w["text"]) for w in ws):
        return False
    left_bound = min(centers) - COL_TOL
    # No token in the left (code/title) zone.
    return all((w["x0"] + w["x1"]) / 2 >= left_bound for w in ws)


def extract(pdf_path, verbose=False):
    pdf = pdfplumber.open(pdf_path)
    result = {}
    cur_dept = cur_year = cur_sem = None
    centers = None
    in_plan = False

    for idx, page in enumerate(pdf.pages):
        words = page.extract_words(use_text_flow=False, keep_blank_chars=False)
        rows = group_rows(words)
        if not rows:
            continue
        header = " ".join(row_text(r) for r in rows[:2])
        if header.startswith("แผนการศึกษาตามหลักสูตร"):
            in_plan = True
        if not in_plan:
            continue
        if header.startswith("คำอธิบายรายวิชา"):
            break

        page_centers = find_column_centers(rows)
        if page_centers:
            centers = page_centers

        # Pass 1: handle structural markers and collect data rows, grouping
        # wrapped course rows into blocks.
        pending = []  # list of visual rows forming the current course block

        def commit_block():
            if not pending or not (centers and cur_dept and cur_year and cur_sem):
                pending.clear()
                return
            block = merge_block_rows(pending, centers)
            pending.clear()
            creds = assign_credits(block, centers)
            code, title = course_parts(block, centers)
            has_cred = any(c is not None for c in creds)
            if not has_cred:
                return
            if code is None and not title:
                return  # totals row
            for (cohort, plan), cr in zip(COL_SPEC, creds):
                if cr is None:
                    continue
                lst = (result.setdefault(cur_dept, {}).setdefault(plan, {})
                       .setdefault(cohort, {}).setdefault(cur_year, {})
                       .setdefault(cur_sem, []))
                lst.append({
                    "course_code": code,
                    "course_name": title,
                    "credits": cr,
                    "prerequisite": "-",
                })

        for r in rows:
            txt = row_text(r).strip()
            # Structural markers close any open block first.
            if txt.startswith("สาขา"):
                commit_block(); cur_dept, cur_year, cur_sem = txt, None, None; continue
            m = re.match(r"^ชั้นปีที่\s*(\d+)", txt)
            if m:
                commit_block(); cur_year, cur_sem = m.group(1), None; continue
            if txt.startswith("First Semester"):
                commit_block(); cur_sem = SEM_FIRST; continue
            if txt.startswith("Second Semester"):
                commit_block(); cur_sem = SEM_SECOND; continue
            if txt.startswith("Summer"):
                commit_block(); cur_sem = SEM_SUMMER; continue
            if "หน่วยกิต" in txt or txt.startswith("Course") or txt.startswith("รุ่น"):
                commit_block(); continue
            if txt.startswith("ปกต") or txt == "สหกิจ" or txt.replace(" ", "").startswith("ปกติสหกิจ"):
                commit_block(); continue
            if "หลักสูตรปริญญาตรี" in txt and "ปีการศึกษา" in txt:
                commit_block(); continue
            if not (centers and cur_dept and cur_year and cur_sem):
                continue

            # A credits-only row (all digits, in the credit zone) is ambiguous:
            #   - if the open block still has no credits, these ARE that
            #     multi-line course's credits -> attach but keep the block open
            #     (its title may still wrap onto following rows).
            #   - otherwise it is the printed semester total -> close & skip.
            if is_total_row(r, centers):
                block_has_cred = bool(pending) and any(
                    c is not None for c in assign_credits(merge_block_rows(pending, centers), centers)
                )
                if pending and not block_has_cred:
                    pending.append(r)       # supplies credits; keep block open
                else:
                    commit_block()          # genuine total row -> just close
                continue

            # Data row: start a new course block or continue the current one.
            if classify_row(r, centers) == "start" and pending:
                commit_block()
            pending.append(r)

        commit_block()

    return result

    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--out", default=None)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    data = extract(args.pdf, verbose=args.verbose)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    if args.out:
        open(args.out, "w").write(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
