"""
Extract ALL-faculty degree study plans from curriculum_database.json
→ Web/public/data/all-plans.json (consumed by the timetable auto-fill).

The curriculum DB nests:
  curricula[acadyr].faculties[fkey]
    .departments[deptName].tracks[tkey]
      .plan_types[plan].cohorts[cohort]
        .year_levels[yl].semesters[sem] = [ {course_code, ...} ]

PDF extraction left noise in plan_type keys ("Title", "จ านวนหน่วยกิต …",
stray course names) and hyphenation breaks in Thai dept/track names. We:
  • whitelist-normalise plan types (ปกติ / สหกิจ / ฝึกงาน / เทียบโอน / เลือกฝึก),
    dropping anything containing "หน่วยกิต" or otherwise unrecognised,
  • clean Thai names (drop the "สาขาวิชา"/"หลักสูตร" prefix, remove PDF hyphens),
  • keep only programs with >= MIN_COURSES real course codes,
  • map each faculty to the timetable faculty `group` so auto-fill can also flip
    the course-list faculty filter.

Output schema (one flat programs[] like the old eng-plans.json, but all faculties):
  {
    "meta": { "faculties": [ {key, group, nameTh} ], "generated": "<acadyr list>" },
    "programs": [ {
        acadyr, faculty (fkey), group, facultyName,
        dept (cleaned name = id within acadyr+faculty), deptName,
        track, trackName, plan, cohort,
        years: { yl: { sem: [normCode, ...] } }
    } ]
  }
"""
from __future__ import annotations

import json
import pathlib
import re

MIN_COURSES = 6  # a real degree-plan term-by-term map has at least this many

# school-of-* slug → timetable faculty group (matches GROUP_TH in lib/timetable.ts)
FACULTY_GROUP = {
    "school-of-engineering": "engineering",
    "school-of-information-technology-and-innovation": "technology",
    "school-of-business-administration": "business",
    "school-of-accounting": "business",
    "school-of-economics-and-investment": "business",
    "school-of-entrepreneurship-and-management": "business",
    "school-of-communication-arts": "communication_arts",
    "school-of-digital-media-and-cinematic-arts": "digital_media",
    "school-of-architecture": "architecture",
    "school-of-law": "law",
    "school-of-humanities-and-tourism-management": "hospitality",
    "school-of-fine-and-applied-arts": "liberal_arts",
}


def norm_code(c: str) -> str:
    return re.sub(r"\s+", "", (c or "")).upper()


def clean_name(s: str) -> str:
    """Strip program-type prefix and PDF hyphenation noise from a Thai name."""
    s = (s or "").strip()
    s = re.sub(r"^(สาขาวิชา|หลักสูตร|คณะ)", "", s)
    s = s.replace("-", "").replace("​", "")   # PDF hyphen-breaks + ZWSP
    s = re.sub(r"\s+", " ", s).strip()
    return s or "—"


def norm_plan(plan: str) -> str | None:
    """Return a canonical plan label, or None if the key is parsing noise."""
    p = re.sub(r"\s+", " ", (plan or "").strip())
    if not p:
        return None
    # PDF table-header garbage and stray course names carry "หน่วยกิต" / Latin text
    if "หน่วยกิต" in p:
        return None
    if "เทียบโอน" in p:
        return "เทียบโอน"
    if "ฝึกงา" in p:                       # "ฝึกงาน" / "ฝึกงา น"
        return "ฝึกงาน"
    if "ไม่เลือกฝึก" in p:
        return "ปกติ (ไม่เลือกฝึก)"
    if "เลือกฝึก" in p:
        return "ปกติ (เลือกฝึก)"
    if "สหกิจ" in p and len(p) <= 16:      # "สหกิจ"; reject "/1 สหกิจ" noise
        return "สหกิจ"
    if "ปกติ" in p and len(p) <= 12:
        return "ปกติ"
    return None                            # "Title", English sentences, etc.


def clean_track(track_key: str, track_name: str | None) -> tuple[str, str]:
    """(canonical track id, display label). 'default' stays default."""
    if track_key == "default":
        return "default", "default"
    label = clean_name(track_name or track_key)
    # stable id from the cleaned label so the same track merges across years
    return label, label


def collect_courses(cohort: dict) -> dict:
    """year_levels → {yl: {sem: [normCode]}}, skipping null (elective) slots."""
    years: dict[str, dict[str, list[str]]] = {}
    for yl, ylv in cohort.get("year_levels", {}).items():
        sem_map: dict[str, list[str]] = {}
        for sk, sem in ylv.get("semesters", {}).items():
            codes = [norm_code(c["course_code"]) for c in sem if c.get("course_code")]
            if codes:
                sem_map[sk] = codes
        if sem_map:
            years[yl] = sem_map
    return years


def main() -> None:
    repo = pathlib.Path(__file__).resolve().parents[2]
    db = json.loads((repo / "Server" / "curriculum_database.json").read_text(encoding="utf-8"))

    programs: list[dict] = []
    faculties: dict[str, dict] = {}

    for acadyr, ydata in db["curricula"].items():
        for fkey, fac in ydata.get("faculties", {}).items():
            group = FACULTY_GROUP.get(fkey, "service")
            fac_name = fac.get("faculty_name_th") or fac.get("faculty_name_en") or fkey
            faculties.setdefault(fkey, {"key": fkey, "group": group, "nameTh": fac_name})

            for dept_name, dept in fac.get("departments", {}).items():
                dept_clean = clean_name(dept.get("department_name_th") or dept_name)
                for tkey, track in dept.get("tracks", {}).items():
                    track_id, track_label = clean_track(tkey, track.get("track_name"))
                    for pkey, pt in track.get("plan_types", {}).items():
                        plan = norm_plan(pkey)
                        if plan is None:
                            continue
                        for ckey, cohort in pt.get("cohorts", {}).items():
                            years = collect_courses(cohort)
                            total = sum(len(v) for sem in years.values() for v in sem.values())
                            if total < MIN_COURSES:
                                continue
                            programs.append({
                                "acadyr": acadyr,
                                "faculty": fkey,
                                "group": group,
                                "facultyName": fac_name,
                                "dept": dept_clean,
                                "deptName": dept_clean,
                                "track": track_id,
                                "trackName": track_label,
                                "plan": plan,
                                "cohort": ckey,
                                "years": years,
                            })

    # de-duplicate identical (acadyr, faculty, dept, track, plan, cohort) — keep the
    # richest (most course codes) when the PDF produced near-duplicate rows.
    best: dict[tuple, dict] = {}
    for p in programs:
        key = (p["acadyr"], p["faculty"], p["dept"], p["track"], p["plan"], p["cohort"])
        cur = best.get(key)
        size = sum(len(v) for sem in p["years"].values() for v in sem.values())
        if cur is None or size > sum(len(v) for sem in cur["years"].values() for v in sem.values()):
            best[key] = p
    programs = list(best.values())

    programs.sort(key=lambda p: (p["acadyr"], p["group"], p["dept"], p["track"], p["plan"], p["cohort"]))

    out = {
        "meta": {
            "faculties": sorted(faculties.values(), key=lambda f: f["group"]),
            "acadyrs": sorted({p["acadyr"] for p in programs}, reverse=True),
        },
        "programs": programs,
    }

    out_path = repo / "Web" / "public" / "data" / "all-plans.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    # summary
    from collections import Counter
    by_fac = Counter(p["group"] for p in programs)
    print(f"[saved] {out_path}")
    print(f"programs: {len(programs)}  faculties: {len(faculties)}  acadyrs: {out['meta']['acadyrs']}")
    for g, n in sorted(by_fac.items()):
        depts = len({p["dept"] for p in programs if p["group"] == g})
        print(f"  {g:<20} {n:>4} programs · {depts} depts")


if __name__ == "__main__":
    main()
