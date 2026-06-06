"""
Restore prerequisites in curriculum_database.json semester entries.

When my patch rebuilt semester course lists from the PDF study-plan tables,
it hardcoded every `prerequisite: "-"`, wiping the 3,280 real prerequisites
that existed in the original data. This script restores them from two sources:

1. The backup (original semester entries before the patch)
2. The PDF course-list section (authoritative source; has some courses missing from backup)

Strategy:
- Build a (year, dept, course_code) -> prerequisite lookup from both sources
- For each semester course entry with prerequisite "-", look up the real value and restore it
"""
import json
import sys

def main():
    backup_path = "/tmp/curriculum_backup.json"
    pdf_prereqs_path = "/tmp/prereqs_2568.json"
    db_path = "curriculum_database.json"

    print("Loading backup...")
    backup = json.load(open(backup_path))

    print("Loading PDF prerequisites...")
    pdf_prereqs = json.load(open(pdf_prereqs_path))

    print("Loading current database...")
    db = json.load(open(db_path))

    # Build prerequisite lookup: (year, dept_key, course_code) -> prerequisite
    # dept_key is the full department name from the JSON structure
    prereq_map = {}

    # Source 1: backup semester entries
    print("Building prereq map from backup...")
    for year, year_data in backup["curricula"].items():
        eng = year_data["faculties"].get("school-of-engineering")
        if not eng:
            continue
        for dept_key, dept_data in eng["departments"].items():
            for plan_type, plan_data in dept_data["tracks"]["default"]["plan_types"].items():
                for cohort_key, cohort_data in plan_data["cohorts"].items():
                    for year_level, year_level_data in cohort_data["year_levels"].items():
                        for sem_key, courses in year_level_data["semesters"].items():
                            for course in courses:
                                code = course["course_code"]
                                prereq = course.get("prerequisite", "-")
                                if prereq and prereq not in ("-", "", None):
                                    key = (year, dept_key, code)
                                    if key not in prereq_map:
                                        prereq_map[key] = prereq

    print(f"  {len(prereq_map)} prerequisites from backup")

    # Source 2: PDF course-list extraction
    # Map PDF dept names to JSON dept keys
    print("Building prereq map from PDF...")
    pdf_added = 0
    for pdf_dept, courses in pdf_prereqs.items():
        # Find matching dept_key in DB (2568 only for now)
        year = "2568"
        eng = db["curricula"][year]["faculties"]["school-of-engineering"]
        matching_dept_key = None
        for dept_key in eng["departments"]:
            if pdf_dept in dept_key or dept_key in pdf_dept:
                matching_dept_key = dept_key
                break

        if not matching_dept_key:
            print(f"  WARNING: no matching dept for PDF dept '{pdf_dept}'")
            continue

        for code, prereq in courses.items():
            if prereq and prereq not in ("-", "", None):
                key = (year, matching_dept_key, code)
                if key not in prereq_map:
                    prereq_map[key] = prereq
                    pdf_added += 1

    print(f"  {pdf_added} prerequisites from PDF (not in backup)")

    # Apply prerequisites to semester entries
    print("Restoring prerequisites in semester entries...")
    restored_count = 0
    for year, year_data in db["curricula"].items():
        eng = year_data["faculties"].get("school-of-engineering")
        if not eng:
            continue
        for dept_key, dept_data in eng["departments"].items():
            for plan_type, plan_data in dept_data["tracks"]["default"]["plan_types"].items():
                for cohort_key, cohort_data in plan_data["cohorts"].items():
                    for year_level, year_level_data in cohort_data["year_levels"].items():
                        for sem_key, courses in year_level_data["semesters"].items():
                            for course in courses:
                                code = course["course_code"]
                                cur_prereq = course.get("prerequisite", "-")
                                if cur_prereq in ("-", "", None):
                                    key = (year, dept_key, code)
                                    if key in prereq_map:
                                        course["prerequisite"] = prereq_map[key]
                                        restored_count += 1

    print(f"  {restored_count} prerequisites restored")

    # Write updated database
    print(f"Writing {db_path}...")
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

    print("Done.")

if __name__ == "__main__":
    main()
