"""
Export degree plans for ALL faculties from curriculum_database.json
→ Web/public/data/plans.json  (consumed by the timetable auto-fill panel)

Output shape (extends the old eng-plans.json):
{
  "meta": {...},
  "faculties":   [ {key, name, group} ],            # group = timetable scraper group
  "departments": [ {key, faculty, prefix, name} ],  # key unique across the file
  "programs":    [ {acadyr, faculty, dept, deptName, track, plan, cohort,
                    years: {yearLevel: {sem: [normCode]}}} ]
}

Cleaning applied (PDF-extraction artifacts in the DB):
- Thai names: strip stray "-" line-break hyphens between Thai chars
- plan_types: normalise variants of ปกติ/สหกิจ, drop junk ("Title", ...)
- cohorts: "รุ่น ½" → "รุ่น 1/2"
- course codes: keep only real-looking codes (AB123 / ABC123A), strip spaces
- departments merged across years by (faculty, dominant course prefix)
"""
import json
import re
import pathlib
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "Server" / "curriculum_database.json"
OUT_PATH = ROOT / "Web" / "public" / "data" / "plans.json"

# faculty key → timetable group (matches scrape_timetable.py groups)
FACULTY_GROUP = {
    "school-of-engineering": "engineering",
    "school-of-accounting": "business",
    "school-of-business-administration": "business",
    "school-of-economics-and-investment": "business",
    "school-of-entrepreneurship-and-management": "business",
    "school-of-communication-arts": "communication_arts",
    "school-of-digital-media-and-cinematic-arts": "digital_media",
    "school-of-architecture": "architecture",
    "school-of-law": "law",
    "school-of-humanities-and-tourism-management": "hospitality",
    "school-of-fine-and-applied-arts": "liberal_arts",
    "school-of-information-technology-and-innovation": "technology",
}
# engineering first (pilot), then DB order
FACULTY_ORDER = ["school-of-engineering"]

JUNK_PLANS = {"Title", "Social English", "The Arts and Politics in Cinema"}

THAI = r"฀-๿"


def clean_thai(s: str) -> str:
    """Strip PDF line-break hyphens adjacent to Thai chars + collapse spaces."""
    if not s:
        return s
    s = re.sub(rf"(?<=[{THAI}])-|-(?=[{THAI}])", "", s)
    return re.sub(r"\s+", " ", s).strip()


def clean_plan(p: str) -> str | None:
    """Normalise a plan_type name; None = drop this plan type."""
    p = clean_thai(p)
    if p in JUNK_PLANS:
        return None
    # "จ านวนหน่วยกิต ปกติ" / "จ ำนวนหน่วยกิต" prefixes (broken "จำนวนหน่วยกิต")
    p = re.sub(r"^จ\s*[าำ]นวนหน่วยกิต\s*", "", p).strip()
    if not p:
        return "ปกติ"
    if re.fullmatch(r"/?1\s*สหกิจ", p):
        return "สหกิจ"
    if "สหกิจ" in p and len(p) > 10:  # "(สำหรับผู้ที่เลือกแผนการศึกษาแบบสหกิจศึกษา)"
        return "สหกิจ"
    if p.replace(" ", "") == "ฝึกงาน":
        return "ฝึกงาน"
    return p


def clean_cohort(c: str) -> str:
    c = clean_thai(c)
    return c.replace("รุ่น ½", "รุ่น 1/2")


CODE_RE = re.compile(r"^[A-Z]{2,4}\d{2,3}[A-Z]?$")


def norm_code(code: str | None) -> str | None:
    if not code:
        return None
    c = code.replace(" ", "").upper()
    return c if CODE_RE.match(c) else None


def track_label(track_key: str, track_name: str | None) -> str:
    """Prefer cleaned Thai key; for ASCII slugs use the human track_name."""
    if track_key == "default":
        return "default"
    if re.search(rf"[{THAI}]", track_key):
        return clean_thai(track_key)
    return clean_thai(track_name) if track_name else track_key


def main() -> None:
    db = json.loads(DB_PATH.read_text(encoding="utf-8"))

    # pass 1: collect every program occurrence + dept code stats
    raw_programs = []  # (acadyr, fac, dept_name_clean, track, plan, cohort, years)
    dept_codes: dict[tuple, Counter] = defaultdict(Counter)   # (fac, dept_name) → prefix counts
    dept_names: dict[tuple, Counter] = defaultdict(Counter)   # for picking representative name
    fac_names: dict[str, str] = {}

    for acadyr, ydata in db["curricula"].items():
        for fkey, fac in ydata.get("faculties", {}).items():
            fac_names.setdefault(fkey, clean_thai(fac.get("faculty_name_th") or fkey))
            for dname_raw, dept in fac.get("departments", {}).items():
                dname = clean_thai(dept.get("department_name_th") or dname_raw)
                for tkey, track in dept.get("tracks", {}).items():
                    tlabel = track_label(tkey, track.get("track_name"))
                    for pkey, pt in track.get("plan_types", {}).items():
                        plabel = clean_plan(pkey)
                        if plabel is None:
                            continue
                        for ckey, cohort in pt.get("cohorts", {}).items():
                            clabel = clean_cohort(ckey)
                            years: dict[str, dict[str, list[str]]] = {}
                            for yl, ydat in cohort.get("year_levels", {}).items():
                                for sem, lst in ydat.get("semesters", {}).items():
                                    codes = []
                                    for course in lst:
                                        c = norm_code(course.get("course_code"))
                                        if c and c not in codes:
                                            codes.append(c)
                                    if codes:
                                        years.setdefault(yl, {})[sem] = codes
                            if not years:
                                continue
                            all_codes = [c for y in years.values() for s in y.values() for c in s]
                            prefixes = [re.match(r"^[A-Z]+", c).group(0) for c in all_codes]
                            key = (fkey, dname)
                            dept_codes[key].update(prefixes)
                            dept_names[key][dname] += 1
                            raw_programs.append((acadyr, fkey, dname, tlabel, plabel, clabel, years))

    # pass 2: merge departments by (faculty, dominant prefix); resolve key collisions
    dept_group_of: dict[tuple, tuple] = {}     # (fac, dname) → (fac, prefix)
    merged: dict[tuple, dict] = {}             # (fac, prefix) → dept meta
    for (fkey, dname), prefix_counts in dept_codes.items():
        # dominant = most frequent prefix; deterministic tie-break by count desc, name asc
        prefix = sorted(prefix_counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]
        gkey = (fkey, prefix)
        dept_group_of[(fkey, dname)] = gkey
        if gkey not in merged:
            merged[gkey] = {"faculty": fkey, "prefix": prefix, "names": Counter()}
        merged[gkey]["names"][dname] += 1

    # unique dept key per merged group: prefix, suffixed when shared across faculties
    by_prefix: dict[str, list[tuple]] = defaultdict(list)
    for gkey in merged:
        by_prefix[gkey[1]].append(gkey)
    dept_key_of: dict[tuple, str] = {}
    for prefix, gkeys in by_prefix.items():
        if len(gkeys) == 1:
            dept_key_of[gkeys[0]] = prefix
        else:
            for fkey, _ in sorted(gkeys):
                short = "".join(w[0] for w in fkey.replace("school-of-", "").split("-"))[:3].upper()
                dept_key_of[(fkey, prefix)] = f"{prefix}@{short}"

    departments = []
    for gkey, meta in merged.items():
        # representative name = longest among the most common (truncated variants lose)
        best =