"""
Add the 2569 engineering faculty to curriculum_database.json.

Builds the full nested structure for academic year 2569, school-of-engineering,
mirroring the existing 2568 schema exactly:

  curricula.2569.faculties.school-of-engineering
    faculty_name_th / faculty_name_en
    departments[dept_th]
      department_name_th / department_name_en
      tracks.default
        track_name
        plan_types[plan]              # ปกติ / สหกิจ
          cohorts[cohort]             # รุ่น 1/1 / รุ่น 1/2 / รุ่น 2
            year_levels[ylvl]
              semesters[sem] -> [ {course_code, course_name, credits, prerequisite} ]
        course_index[code] -> {course_name, credits, prerequisite}

Sources:
  /tmp/eng2569.json       - study-plan extraction (dept -> plan -> cohort -> year -> sem -> [courses])
  /tmp/prereqs_2569.json  - course-list prerequisites (dept -> {code -> prereq})

course_index is built by unioning all courses seen in the study plan, taking
name/credits from the first occurrence, and prerequisite from the course-list.
"""
import json
import copy

DB_PATH = "curriculum_database.json"
PLAN_PATH = "/tmp/eng2569.json"
PREREQ_PATH = "/tmp/prereqs_2569.json"
YEAR = "2569"
ENG = "school-of-engineering"


def norm_code(code):
    return (code or "").replace(" ", "").upper()


def find_prereq_dept(prereqs, dept_th):
    """Match study-plan dept name to a prereq dept key (tolerant of สาขาวิชา/สาขา)."""
    def n(s):
        return (s or "").replace("สาขาวิชา", "สาขา").replace(" ", "")
    target = n(dept_th)
    for k in prereqs:
        if n(k) == target:
            return prereqs[k]
    return {}


def lookup_prereq(prereq_dept, code):
    """Look up prerequisite by course code (tolerant of spacing)."""
    if code is None:
        return "-"
    nc = norm_code(code)
    for k, v in prereq_dept.items():
        if norm_code(k) == nc:
            return v if v not in ("", None) else "-"
    return "-"


def main():
    db = json.load(open(DB_PATH))
    plan = json.load(open(PLAN_PATH))
    prereqs = json.load(open(PREREQ_PATH))

    # Pull dept display names from the existing 2568 faculty (same departments).
    base_eng = db["curricula"]["2568"]["faculties"][ENG]
    dept_meta = {
        dk: {
            "department_name_th": dv["department_name_th"],
            "department_name_en": dv["department_name_en"],
        }
        for dk, dv in base_eng["departments"].items()
    }

    if YEAR in db["curricula"]:
        print(f"WARNING: {YEAR} already exists in curricula; overwriting engineering faculty only.")
        year_node = db["curricula"][YEAR]
        year_node.setdefault("faculties", {})
    else:
        # Create the year. It will hold only the engineering faculty (per request).
        db["curricula"][YEAR] = {"faculties": {}}
        year_node = db["curricula"][YEAR]

    departments = {}
    for dept_th, plan_types in plan.items():
        # Resolve display names; fall back to dept_th if unknown.
        meta = dept_meta.get(dept_th, {
            "department_name_th": dept_th,
            "department_name_en": None,
        })
        prereq_dept = find_prereq_dept(prereqs, dept_th)

        # Build plan_types -> cohorts -> year_levels -> semesters
        out_plans = {}
        course_index = {}
        for plan_name, cohorts in plan_types.items():
            out_cohorts = {}
            for cohort_name, years in cohorts.items():
                out_years = {}
                for ylvl, sems in years.items():
                    out_sems = {}
                    for sem, courses in sems.items():
                        entries = []
                        for c in courses:
                            code = c["course_code"]
                            pr = lookup_prereq(prereq_dept, code)
                            entries.append({
                                "course_code": code,
                                "course_name": c["course_name"],
                                "credits": c["credits"],
                                "prerequisite": pr,
                            })
                            # populate course_index (first occurrence wins)
                            if code and code not in course_index:
                                course_index[code] = {
                                    "course_name": c["course_name"],
                                    "credits": c["credits"],
                                    "prerequisite": pr,
                                }
                        out_sems[sem] = entries
                    out_years[ylvl] = {"semesters": out_sems}
                out_cohorts[cohort_name] = {"year_levels": out_years}
            out_plans[plan_name] = {"cohorts": out_cohorts}

        departments[dept_th] = {
            "department_name_th": meta["department_name_th"],
            "department_name_en": meta["department_name_en"],
            "tracks": {
                "default": {
                    "track_name": "default",
                    "plan_types": out_plans,
                    "course_index": dict(sorted(course_index.items())),
                }
            },
        }

    year_node["faculties"][ENG] = {
        "faculty_name_th": base_eng["faculty_name_th"],
        "faculty_name_en": base_eng["faculty_name_en"],
        "departments": departments,
    }

    # Update metadata.academic_years (add 2569 if missing, keep order desc).
    meta = db.get("metadata", {})
    years = meta.get("academic_years", [])
    if YEAR not in years:
        years = sorted(set(years) | {YEAR}, reverse=True)
        meta["academic_years"] = years
    db["metadata"] = meta

    json.dump(db, open(DB_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # Report
    total_courses = 0
    total_prereq = 0
    for dept_th, dv in departments.items():
        for pn, pv in dv["tracks"]["default"]["plan_types"].items():
            for cn, cv in pv["cohorts"].items():
                for yl, yv in cv["year_levels"].items():
                    for sm, cs in yv["semesters"].items():
                        total_courses += len(cs)
                        total_prereq += sum(1 for c in cs if c["prerequisite"] not in ("-", "", None))
    print(f"Added {YEAR} engineering: {len(departments)} departments")
    for dept_th, dv in departments.items():
        ci = dv["tracks"]["default"]["course_index"]
        print(f"  {dept_th[:42]:42} | course_index={len(ci)}")
    print(f"Total semester course entries: {total_courses} ({total_prereq} with prerequisites)")
    print(f"metadata.academic_years -> {db['metadata']['academic_years']}")


if __name__ == "__main__":
    main()
