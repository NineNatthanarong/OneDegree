"""
Diff extracted PDF study-plan data against the current curriculum_database.json
for the engineering faculty of a given academic year.

Compares, per dept / plan / cohort / year / semester, the ordered list of
(course_code, course_name, credits). Reports:
  - courses present in JSON but missing from PDF extraction
  - courses present in PDF but missing from JSON
  - credit mismatches
  - name mismatches

Codes are normalized (spaces removed) for matching; elective placeholders
(course_code == null) are matched by course_name.
"""
import sys
import json
import argparse

ENG = "school-of-engineering"


def norm(code):
    return (code or "").replace(" ", "").upper()


def load_json_year(path, year):
    data = json.load(open(path))
    eng = data["curricula"][year]["faculties"][ENG]
    out = {}
    for dept, dv in eng["departments"].items():
        tr = dv["tracks"]["default"]
        for plan, pv in tr["plan_types"].items():
            for cohort, cv in pv["cohorts"].items():
                for ylvl, yv in cv["year_levels"].items():
                    for sem, courses in yv["semesters"].items():
                        out[(dept, plan, cohort, ylvl, sem)] = [
                            (norm(c.get("course_code")),
                             (c.get("course_name") or "").strip(),
                             c.get("credits"))
                            for c in courses
                        ]
    return out


def load_pdf(path):
    data = json.load(open(path))
    out = {}
    for dept, plans in data.items():
        for plan, cohorts in plans.items():
            for cohort, years in cohorts.items():
                for ylvl, sems in years.items():
                    for sem, courses in sems.items():
                        out[(dept, plan, cohort, ylvl, sem)] = [
                            (norm(c.get("course_code")),
                             (c.get("course_name") or "").strip(),
                             c.get("credits"))
                            for c in courses
                        ]
    return out


def key_of(entry):
    code, name, _ = entry
    return code if code else f"~{name.lower()}"


def diff_cell(json_list, pdf_list):
    """Return (only_json, only_pdf, cred_mismatch, name_mismatch)."""
    jmap = {key_of(e): e for e in json_list}
    pmap = {key_of(e): e for e in pdf_list}
    only_json = [jmap[k] for k in jmap if k not in pmap]
    only_pdf = [pmap[k] for k in pmap if k not in jmap]
    cred_mm, name_mm = [], []
    for k in jmap:
        if k in pmap:
            jc, jn, jcr = jmap[k]
            pc, pn, pcr = pmap[k]
            if jcr != pcr:
                cred_mm.append((k, jcr, pcr))
            if jn.lower() != pn.lower():
                name_mm.append((k, jn, pn))
    return only_json, only_pdf, cred_mm, name_mm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("--pdf", required=True, help="extracted PDF json")
    ap.add_argument("--year", required=True)
    ap.add_argument("--dept", default=None)
    args = ap.parse_args()

    jdata = load_json_year(args.json, args.year)
    pdata = load_pdf(args.pdf)

    all_keys = sorted(set(jdata) | set(pdata))
    totals = {"only_json": 0, "only_pdf": 0, "cred": 0, "name": 0}
    for key in all_keys:
        dept, plan, cohort, ylvl, sem = key
        if args.dept and dept != args.dept:
            continue
        jl = jdata.get(key, [])
        pl = pdata.get(key, [])
        oj, op, cm, nm = diff_cell(jl, pl)
        if oj or op or cm or nm:
            print(f"\n### {dept} | {plan} | {cohort} | yr{ylvl} sem{sem}")
            for e in oj:
                print(f"  - ONLY IN JSON : {e[0] or e[1]} | {e[2]} | {e[1]}")
            for e in op:
                print(f"  + ONLY IN PDF  : {e[0] or e[1]} | {e[2]} | {e[1]}")
            for k, jcr, pcr in cm:
                print(f"  ~ CREDIT       : {k} | json={jcr} pdf={pcr}")
            for k, jn, pn in nm:
                print(f"  ~ NAME         : {k}\n        json: {jn}\n        pdf : {pn}")
            totals["only_json"] += len(oj)
            totals["only_pdf"] += len(op)
            totals["cred"] += len(cm)
            totals["name"] += len(nm)

    print("\n==== SUMMARY ====")
    print(f"only_json={totals['only_json']} only_pdf={totals['only_pdf']} "
          f"credit_mismatch={totals['cred']} name_mismatch={totals['name']}")


if __name__ == "__main__":
    main()
