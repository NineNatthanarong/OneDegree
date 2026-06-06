"""
Patch the engineering-faculty study-plan data in curriculum_database.json from
the PDF extraction, WITHOUT changing the schema.

Scope (only the engineering faculty, all academic years that have a matching
PDF):
  - For each dept / plan / cohort / year / semester, replace the semester
    course list with the PDF-extracted entries (clean course_name, correct
    course_code, correct credits).
  - prerequisite on semester entries is kept as "-" (matches existing schema;
    real prerequisites live in course_index, which is left untouched).

Everything else (course_index and its prerequisites, names_th/en, track_name,
all other faculties) is preserved byte-for-byte.

Matching of PDF dept -> JSON dept is by department_name_th (identical strings).
Cohort/plan/year/semester keys produced by the extractor already match the
JSON's keys ("รุ่น 1/1", "ปกติ"/"สหกิจ", "1".."4", "1"/"2"/"3").
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.dirname(__file__))
from extract_eng_plans import extract  # noqa: E402

ENG = "school-of-engineering"

# Map academic year -> PDF path.
PDF_DIR = "/Users/natthanarong/Documents/Proj"
PDF_TMPL = "ปีการศึกษา {year} - หลักสูตรปริญญาตรี คณะวิศวกรรมศาสตร์.pdf"


def norm_dept(name):
    """Normalize dept names so JSON 'สาขาวิศวกรรมไฟฟ้า' matches PDF
    'สาขาวิชาวิศวกรรมไฟฟ้า' (some JSON years drop the 'วิชา')."""
    n = (name or "").replace("สาขาวิชา", "สาขา")
    return n.replace(" ", "")


def norm_cohort(key):
    """Normalize cohort keys: JSON 'รุ่น ½' (fraction glyph) -> 'รุ่น 1/2'."""
    return (key or "").replace("½", "1/2").replace(" ", "")


def build_dept_lookup(pdf_data):
    return {norm_dept(k): v for k, v in pdf_data.items()}


def build_cohort_lookup(pdf_plan):
    return {norm_cohort(k): v for k, v in pdf_plan.items()}


def build_semester_entries(pdf_courses):
    """Map extracted course dicts to JSON semester-entry dicts (schema-exact)."""
    out = []
    for c in pdf_courses:
        out.append({
            "course_code": c["course_code"],   # may be None for elective slots
            "course_name": c["course_name"],
            "credits": c["credits"],
            "prerequisite": "-",
        })
    return out


def patch_year(data, year, pdf_data, report):
    eng = data["curricula"].get(year, {}).get("faculties", {}).get(ENG)
    if not eng:
        report.append(f"[{year}] no engineering faculty in JSON; skipped")
        return 0

    # Safety: never let an empty/failed extraction wipe existing data.
    if not pdf_data:
        report.append(f"[{year}] PDF extraction empty (unsupported layout); SKIPPED, JSON left unchanged")
        return 0

    dept_lookup = build_dept_lookup(pdf_data)
    changed_cells = 0
    for dept_th, dept_node in eng["departments"].items():
        pdf_dept = dept_lookup.get(norm_dept(dept_th))
        if pdf_dept is None:
            report.append(f"[{year}] PDF missing dept: {dept_th}")
            continue
        tr = dept_node["tracks"]["default"]
        for plan, plan_node in tr["plan_types"].items():
            pdf_plan = pdf_dept.get(plan)
            if pdf_plan is None:
                report.append(f"[{year}] {dept_th} | PDF missing plan: {plan}")
                continue
            cohort_lookup = build_cohort_lookup(pdf_plan)
            for cohort, cohort_node in plan_node["cohorts"].items():
                pdf_cohort = cohort_lookup.get(norm_cohort(cohort))
                if pdf_cohort is None:
                    report.append(f"[{year}] {dept_th} | {plan} | PDF missing cohort: {cohort}")
                    continue
                for ylvl, ynode in cohort_node["year_levels"].items():
                    pdf_year = pdf_cohort.get(ylvl, {})
                    for sem in list(ynode["semesters"].keys()):
                        pdf_courses = pdf_year.get(sem, [])
                        new_entries = build_semester_entries(pdf_courses)
                        old_entries = ynode["semesters"][sem]
                        if new_entries != old_entries:
                            ynode["semesters"][sem] = new_entries
                            changed_cells += 1
                    # add any semesters present in PDF but absent in JSON
                    for sem, pdf_courses in pdf_year.items():
                        if sem not in ynode["semesters"]:
                            ynode["semesters"][sem] = build_semester_entries(pdf_courses)
                            changed_cells += 1
    report.append(f"[{year}] semester cells updated: {changed_cells}")
    return changed_cells


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--years", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    data = json.load(open(args.json))
    report = []
    total = 0
    for year in args.years:
        pdf_path = os.path.join(PDF_DIR, PDF_TMPL.format(year=year))
        if not os.path.exists(pdf_path):
            report.append(f"[{year}] PDF not found: {pdf_path}")
            continue
        pdf_data = extract(pdf_path)
        total += patch_year(data, year, pdf_data, report)

    with open(args.out, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n".join(report))
    print(f"TOTAL semester cells updated: {total}")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
