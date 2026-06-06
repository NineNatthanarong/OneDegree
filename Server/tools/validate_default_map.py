#!/usr/bin/env python3
"""
validate_default_map.py — find prerequisite-data errors by replaying the web
app's *default map* conflict detector against curriculum_database.json.

The web UI shows cohorts[0] of each degree plan with NO manual moves. The real
curriculum is internally consistent, so the default map must be conflict-free.
Any violation on the default map => the prerequisite data is wrong (wrong code,
wrong placement, or — most commonly — a must-pass-or-parallel co-requisite that
is mislabeled as plain must-pass).

This script mirrors EXACTLY:
  - Web/lib/prereq.ts   parsePrereqClauses / normalizeCode / extractCodes
  - Web/lib/graph.ts    computeViolations (manualMoves empty)
  - Web/app/page.tsx    rebuildGraph flatten (cohorts[0], sorted years/sems)
  - Server/app/api.py   cohort ordering (name asc), year/semester ordering

Usage:
  python3 tools/validate_default_map.py                 # years 2564-2569, default cohort
  python3 tools/validate_default_map.py --years 2567
  python3 tools/validate_default_map.py --all-cohorts   # also check non-default cohorts
  python3 tools/validate_default_map.py --json out.json # machine-readable dump
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Optional

HERE = Path(__file__).resolve().parent
DB_PATH = HERE.parent / "curriculum_database.json"

DEFAULT_YEARS = ["2564", "2565", "2566", "2567", "2568", "2569"]

# ----------------------------------------------------------------------------
# prereq.ts replication
# ----------------------------------------------------------------------------
_CODE_RE = re.compile(r"([A-Z](?:\s*[A-Z]){0,3})\s*(\d(?:\s*\d){2,3})")
_CONCURRENT_RE = re.compile(r"ควบ\s*คู่")
_STRIP_CONC_1 = re.compile(r"(หรือ\s*)?(เรียน\s*)?ควบ\s*คู่กัน?")
_STRIP_CONC_2 = re.compile(r"(หรือ\s*)?(เรียน\s*)?ควบ\s*คู่")
_STRIP_SOBDAI = re.compile(r"สอบได้")
_STRIP_LEAD_PHAN = re.compile(r"^\s*ผ่าน")
_SPLIT_AND = re.compile(r"และ")


def normalize_code(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    return re.sub(r"\s+", "", raw).upper()


def extract_codes(s: str) -> list[str]:
    upper = s.upper()
    out: list[str] = []
    for m in _CODE_RE.finditer(upper):
        letters = re.sub(r"\s+", "", m.group(1))
        digits = re.sub(r"\s+", "", m.group(2))
        out.append(letters + digits)
    return out


def parse_prereq_clauses(raw: Optional[str]) -> list[dict[str, Any]]:
    """Returns list of {codes: [str], kind: 'pass'|'concurrent'}."""
    if not raw:
        return []
    trimmed = raw.strip()
    if not trimmed or trimmed in ("-", "—"):
        return []

    has_concurrent = bool(_CONCURRENT_RE.search(trimmed))

    s = _STRIP_CONC_1.sub(" ", trimmed)
    s = _STRIP_CONC_2.sub(" ", s)
    s = _STRIP_SOBDAI.sub(" ", s)
    s = _STRIP_LEAD_PHAN.sub(" ", s).strip()

    and_parts = _SPLIT_AND.split(s)
    kind = "concurrent" if has_concurrent else "pass"

    clauses: list[dict[str, Any]] = []
    for part in and_parts:
        codes = extract_codes(part)
        if not codes:
            continue
        seen: set[str] = set()
        uniq: list[str] = []
        for c in codes:
            if c not in seen:
                seen.add(c)
                uniq.append(c)
        clauses.append({"codes": uniq, "kind": kind})
    return clauses


# ----------------------------------------------------------------------------
# page.tsx rebuildGraph flatten + graph.ts computeViolations replication
# ----------------------------------------------------------------------------
class Node:
    __slots__ = ("id", "code", "code_norm", "name", "pre_raw", "clauses",
                 "year_idx", "sem_idx", "year_level", "semester")

    def __init__(self, nid, code, name, pre_raw, year_idx, sem_idx, ylvl, sem):
        self.id = nid
        self.code = code or ""
        self.code_norm = normalize_code(code) or ""
        self.name = name
        self.pre_raw = pre_raw or ""
        self.clauses = parse_prereq_clauses(pre_raw)
        self.year_idx = year_idx
        self.sem_idx = sem_idx
        self.year_level = ylvl
        self.semester = sem


def flatten_cohort(cohort: dict[str, Any]) -> list[Node]:
    """Mirror api._build_degree_plan_years ordering + page.tsx flatten:
    years sorted by year_level asc; semesters sorted by semester asc;
    year_idx / sem_idx are the *positions* in those sorted lists."""
    year_levels = cohort.get("year_levels", {})
    nodes: list[Node] = []
    seq = 0
    for yi, ylvl_key in enumerate(sorted(year_levels, key=lambda k: int(k))):
        sems = year_levels[ylvl_key].get("semesters", {})
        for si, sem_key in enumerate(sorted(sems, key=lambda k: int(k))):
            for course in sems[sem_key]:
                nodes.append(Node(
                    nid=str(seq),
                    code=course.get("course_code"),
                    name=course.get("course_name") or "",
                    pre_raw=course.get("prerequisite"),
                    year_idx=yi,
                    sem_idx=si,
                    ylvl=int(ylvl_key),
                    sem=int(sem_key),
                ))
                seq += 1
    return nodes


def order_of(n: Node) -> int:
    return n.year_idx * 10 + n.sem_idx


def compute_violations(nodes: list[Node]) -> list[dict[str, Any]]:
    """Mirror graph.ts computeViolations with empty manualMoves.
    codeToId: last occurrence wins (exactly as the TS Map.set loop)."""
    code_to_node: dict[str, Node] = {}
    for n in nodes:
        if n.code_norm:
            code_to_node[n.code_norm] = n  # last wins

    violations: list[dict[str, Any]] = []
    for n in nodes:
        if not n.clauses:
            continue
        c_order = order_of(n)
        for ci, cl in enumerate(n.clauses):
            any_ok = False
            any_known = False
            alts_detail = []
            for code in cl["codes"]:
                alt = code_to_node.get(code)
                if alt is None:
                    alts_detail.append({"code": code, "in_plan": False})
                    continue
                any_known = True
                a_order = order_of(alt)
                ok = (a_order < c_order) if cl["kind"] == "pass" else (a_order <= c_order)
                rel = ("earlier" if a_order < c_order
                       else "same" if a_order == c_order else "later")
                alts_detail.append({
                    "code": code, "in_plan": True, "ok": ok, "rel": rel,
                    "alt_pos": f"Y{alt.year_level}S{alt.semester}",
                })
                if ok:
                    any_ok = True
                    break
            if any_known and not any_ok:
                violations.append({
                    "course_code": n.code,
                    "course_name": n.name,
                    "pos": f"Y{n.year_level}S{n.semester}",
                    "prerequisite": n.pre_raw,
                    "kind": cl["kind"],
                    "clause_idx": ci,
                    "clause_codes": cl["codes"],
                    "alts": alts_detail,
                })
                break  # one violation per course (mirror TS `break`)
    return violations


# ----------------------------------------------------------------------------
# walk the DB
# ----------------------------------------------------------------------------
def iter_cohorts(db: dict[str, Any], years: list[str]):
    curricula = db.get("curricula", {})
    for year in years:
        ydata = curricula.get(year)
        if not ydata:
            continue
        for fslug, fac in ydata.get("faculties", {}).items():
            for dkey, dept in fac.get("departments", {}).items():
                for tkey, track in dept.get("tracks", {}).items():
                    for pkey, plan in track.get("plan_types", {}).items():
                        cohorts = plan.get("cohorts", {})
                        # mirror api.py: order_by(Cohort.name.asc())
                        ordered = sorted(cohorts.items(), key=lambda kv: kv[0])
                        for idx, (cname, cohort) in enumerate(ordered):
                            yield {
                                "year": year, "faculty": fslug,
                                "faculty_th": fac.get("faculty_name_th"),
                                "department": dkey, "track": tkey,
                                "plan": pkey, "cohort": cname,
                                "is_default": idx == 0,
                                "cohort_obj": cohort,
                            }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", nargs="*", default=DEFAULT_YEARS)
    ap.add_argument("--all-cohorts", action="store_true",
                    help="check every cohort, not only the displayed default (cohorts[0])")
    ap.add_argument("--json", type=str, default=None)
    ap.add_argument("--db", type=str, default=str(DB_PATH))
    args = ap.parse_args()

    db = json.loads(Path(args.db).read_bytes())

    results = []
    total_default = 0
    total_default_bad = 0
    for ctx in iter_cohorts(db, list(args.years)):
        if not args.all_cohorts and not ctx["is_default"]:
            continue
        if ctx["is_default"]:
            total_default += 1
        nodes = flatten_cohort(ctx["cohort_obj"])
        viols = compute_violations(nodes)
        if viols:
            if ctx["is_default"]:
                total_default_bad += 1
            results.append({k: ctx[k] for k in
                            ("year", "faculty", "faculty_th", "department",
                             "track", "plan", "cohort", "is_default")}
                           | {"violations": viols})

    # ---- human report ----
    print("=" * 78)
    print("DEFAULT-MAP PREREQUISITE VALIDATION  (years: %s)" % ", ".join(args.years))
    print("=" * 78)
    bad_codes: dict[str, int] = {}
    for r in results:
        tag = "DEFAULT" if r["is_default"] else "alt"
        print(f"\n[{tag}] {r['year']} · {r['faculty']} · {r['department']} · "
              f"plan={r['plan']} · cohort={r['cohort']}")
        for v in r["violations"]:
            bad_codes[v["course_code"]] = bad_codes.get(v["course_code"], 0) + 1
            print(f"   ✗ {v['course_code']} ({v['pos']}) needs «{v['prerequisite']}»"
                  f"  [parsed kind={v['kind']}]")
            for a in v["alts"]:
                if not a["in_plan"]:
                    print(f"        - {a['code']}: not in this plan (ignored)")
                else:
                    flag = "OK" if a["ok"] else "BAD"
                    print(f"        - {a['code']}: {a['alt_pos']} ({a['rel']}) [{flag}]")
            # diagnosis hint
            in_plan = [a for a in v["alts"] if a["in_plan"]]
            same = [a for a in in_plan if a["rel"] == "same"]
            later = [a for a in in_plan if a["rel"] == "later"]
            if v["kind"] == "pass" and same and not later:
                print("        → likely CO-REQ: real rule is must-pass-OR-parallel "
                      "(append 'หรือเรียนควบคู่กัน'). VERIFY on degreeplan.bu.ac.th")
            elif later:
                print("        → prereq sits LATER than course: wrong code or wrong "
                      "placement. VERIFY on degreeplan.bu.ac.th")
            else:
                print("        → no satisfying alternative. VERIFY on degreeplan.bu.ac.th")

    print("\n" + "=" * 78)
    print(f"Default maps checked : {total_default}")
    print(f"Default maps w/ conflict : {total_default_bad}")
    print(f"Cohorts reported (incl alt) : {len(results)}")
    if bad_codes:
        print("Courses with conflicts (count):")
        for code, n in sorted(bad_codes.items(), key=lambda kv: -kv[1]):
            print(f"   {code}: {n}")
    print("=" * 78)

    if args.json:
        Path(args.json).write_text(
            json.dumps({"years": list(args.years),
                        "default_checked": total_default,
                        "default_bad": total_default_bad,
                        "results": results}, ensure_ascii=False, indent=2))
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
