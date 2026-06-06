"""
Add structured prerequisite fields to every engineering semester course entry.

Each course entry keeps its original Thai `prerequisite` text and gains:
  - prerequisite_type:   "none" | "must_pass" | "concurrent_ok" | "other"
  - prerequisite_courses: list of normalized course codes ["PH 105", ...]

Classification rules (applied to the Thai prerequisite text):
  - "-" / empty                              -> none,          []
  - contains "ควบคู่" (เรียนควบคู่กัน)        -> concurrent_ok, [codes]   (pass OR take in parallel)
  - contains a course code, no "ควบคู่"      -> must_pass,     [codes]
  - no course code (year standing / approval)-> other,         []

Course codes are extracted robustly, repairing the PDF's split-digit damage
(e.g. "MA 10 5" -> "MA 105", "EE 3 12" -> "EE 312", "CE 3 3 1" -> "CE 331").
"""
import json
import re

DB_PATH = "curriculum_database.json"
ENG = "school-of-engineering"


def extract_codes(text):
    """Return normalized course codes found in a prerequisite string.

    Handles clean codes ('PH 105', 'AIE213') and PDF split-digit damage
    ('MA 10 5', 'EE 3 12', 'CE 3 3 1') by gluing a 2-3 letter dept prefix to
    the digits that follow until exactly 3 digits are collected.
    """
    codes = []
    # Token stream: letter-groups and digit-groups.
    tokens = re.findall(r"[A-Z]{2,3}|\d+", text)
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if re.fullmatch(r"[A-Z]{2,3}", t):
            # collect following digit tokens until we have 3 digits
            digits = ""
            j = i + 1
            while j < len(tokens) and re.fullmatch(r"\d+", tokens[j]) and len(digits) < 3:
                need = 3 - len(digits)
                digits += tokens[j][:need]
                # if this token had leftover digits beyond what we need, stop here
                if len(tokens[j]) > need:
                    break
                j += 1
            if len(digits) == 3:
                codes.append(f"{t} {digits}")
                i = j
                continue
        i += 1
    # de-dup preserving order
    seen = set()
    out = []
    for c in codes:
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def classify(text):
    if text is None:
        return "none", []
    t = text.strip()
    if t in ("-", "", "–", "—"):
        return "none", []
    # ignore stray header-bleed strings ("- วิชาบังคับก่อน ...", "MA 109 2568 31 ...")
    codes = extract_codes(t)
    concurrent = "ควบคู่" in t
    if concurrent:
        return "concurrent_ok", codes
    if codes:
        return "must_pass", codes
    return "other", []


def main():
    db = json.load(open(DB_PATH))
    stats = {"none": 0, "must_pass": 0, "concurrent_ok": 0, "other": 0}
    touched = 0
    for y, yd in db["curricula"].items():
        eng = yd["faculties"].get(ENG)
        if not eng:
            continue
        for dk, dv in eng["departments"].items():
            tr = dv["tracks"]["default"]
            # semester entries
            for pk, pv in tr["plan_types"].items():
                for ck, cv in pv["cohorts"].items():
                    for yl, ylv in cv["year_levels"].items():
                        for sm, cs in ylv["semesters"].items():
                            for c in cs:
                                ptype, pcourses = classify(c.get("prerequisite"))
                                c["prerequisite_type"] = ptype
                                c["prerequisite_courses"] = pcourses
                                stats[ptype] += 1
                                touched += 1
            # course_index entries too (same enrichment, for consistency)
            for code, entry in tr["course_index"].items():
                ptype, pcourses = classify(entry.get("prerequisite"))
                entry["prerequisite_type"] = ptype
                entry["prerequisite_courses"] = pcourses

    json.dump(db, open(DB_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Enriched {touched} semester course entries.")
    for k, v in stats.items():
        print(f"  {k:14}: {v}")


if __name__ == "__main__":
    main()
