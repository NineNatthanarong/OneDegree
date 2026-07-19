#!/usr/bin/env python3
"""Import undergraduate BUI/BUCI degree-plan PDFs published by BU.

The official files use visual tables, while their text layer consistently keeps
course code, title, academic year and semester on the same page.  This importer
uses that text layer to build the application's canonical curriculum schema.
It deliberately keeps an elective placeholder as a course without a code,
instead of inventing a course code.

Usage (PDFs must first be downloaded from degreeplan.bu.ac.th):

    python3 tools/import_official_colleges.py --pdf-dir /tmp/bu-pdfs

Expected names are ``bui-2568-<program>.pdf`` and ``buci-2568.pdf``.  BUI
documents are individual programmes; a BUCI document can contain several.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "Server" / "curriculum_database.json"
YEARS = {"2564", "2565", "2566", "2567", "2568", "2569"}
CODE = re.compile(r"^\s*([A-Z]{2,4}\s?(?:\d{3}|[Xx]{2,}\d?)|X{4,})\b\s*(.*)$")
YEAR = re.compile(r"ชั้นป.{0,4}ที่\s*(\d+)")
ENGLISH_YEAR = re.compile(r"^(First|Second|Third|Fourth) Year$", re.I)
WORD_YEAR = re.compile(r"\b(First|Second|Third|Fourth) Year\b", re.I)
NUMBERED_YEAR = re.compile(r"\bYear\s+([1-4])\b", re.I)
NUMBERED_SEMESTER = re.compile(r"\bSemester\s+([1-3])\b", re.I)
TRACK = re.compile(r"(?:Concentration\s+track|Track):\s*(.+?)\)?$", re.I)


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\ufeff", " ")).strip(" -–—")


def code_of(raw: str) -> str | None:
    value = re.sub(r"\s+", "", raw).upper()
    return value if re.fullmatch(r"[A-Z]{2,4}\d{3}", value) else None


def pdf_text(path: Path) -> str:
    # pdftotext is available in the development image and preserves table rows
    # much better than Python's generic PDF extractors for these BU documents.
    return subprocess.check_output(["pdftotext", "-layout", str(path), "-"], text=True)


def title_from(rest: str) -> tuple[str, int | None]:
    """Remove trailing table-credit columns while retaining a readable title."""
    rest = clean(rest)
    credits = re.findall(r"(?:^|\s)([1-9])(?=\s|$)", rest)
    if re.fullmatch(r"[1-9](?:\s+[1-9]){0,5}", rest):
        return "", int(credits[0]) if credits else None
    # Degree-plan rows end with one or more one-digit credit cells.  Remove the
    # complete trailing run, but never digits in course titles.
    rest = re.sub(r"(?:\s+[1-9]){1,6}\s*$", "", rest)
    return clean(rest) or "Elective", int(credits[0]) if credits else None


def program_name(line: str, fallback: str) -> str:
    line = clean(line)
    if "หลักสูตรสองภาษา" in line or "Bilingua" in line:
        return "หลักสูตรสองภาษา"
    if "ภาษาจีนธุรกิจ" in line:
        return "ภาษาจีนธุรกิจ"
    return fallback


def prerequisite_from(value: str, thai_value: str = "") -> str:
    """Turn an official prerequisite line into the app's canonical wording.

    BUI course descriptions are English, while BUCI prints a Thai line followed
    by its English translation.  The latter explicitly tells us whether the
    course must be passed (``สอบได้``), so retain that distinction rather than
    treating every referenced course as a co-requisite.
    """
    codes = [code_of(code) for code in re.findall(r"\b[A-Z]{2,4}\s?\d{3}\b", value.upper())]
    codes = [code for code in codes if code]
    if not codes:
        return "-"
    joined = " และ ".join(re.sub(r"([A-Z]+)(\d+)", r"\1 \2", code) for code in codes)
    lower = value.lower()
    if "concurrent" in lower or "co-requisite" in lower or "corequisite" in lower:
        result = f"{joined} หรือเรียนควบคู่กัน"
    elif "สอบได้" in thai_value:
        result = f"สอบได้ {joined}"
    else:
        # The BUI handbooks label these simply as "Prerequisite".  They do
        # not say concurrent enrollment, so they are a must-pass dependency.
        result = f"สอบได้ {joined}"
    if "dean" in lower and ("approval" in lower or "approve" in lower):
        result += " หรือได้รับอนุมัติจากคณบดี"
    return result


def course_catalog(text: str) -> dict[str, dict[str, str]]:
    """Read canonical names and prerequisites from course descriptions.

    The study-plan tables sometimes place a wrapped title *above* the code and
    credit cell.  The course-description section is linear and gives us a
    reliable code → name lookup to use for those placements.
    """
    marker_positions = [text.rfind("Course Description"), text.rfind("คำอธิบายรายวิชา")]
    start = max(marker_positions)
    if start < 0:
        return {}
    courses: dict[str, dict[str, str]] = {}
    current_code: str | None = None
    thai_prerequisite = ""
    for raw in text[start:].splitlines():
        line = clean(raw)
        thai_match = re.match(r"วิชาบังคับก่อน\s*:\s*(.+)$", line)
        if thai_match:
            thai_prerequisite = thai_match.group(1)
            continue
        prerequisite_match = re.match(r"Prerequisite\s*:\s*(.+)$", line, re.I)
        if prerequisite_match and current_code:
            courses.setdefault(current_code, {"name": "", "prerequisite": "-"})["prerequisite"] = prerequisite_from(
                prerequisite_match.group(1), thai_prerequisite
            )
            thai_prerequisite = ""
            continue
        match = CODE.match(line)
        if not match:
            continue
        code, rest = match.groups()
        # Course descriptions print credits as "3 (2-2-6)" after the title.
        title = re.sub(r"\s+\d+\s*\([^)]*\).*$", "", clean(rest))
        title = re.sub(r"(?:\s+[1-9]){1,6}\s*$", "", title).strip()
        normalized = code_of(code)
        if normalized:
            current_code = normalized
            if len(title) > 2 and re.search(r"[A-Za-z]", title) and not title.isdigit():
                courses.setdefault(normalized, {"name": "", "prerequisite": "-"})["name"] = title
    return courses


def codes_in_prerequisite_row(value: str, current: str) -> list[str]:
    """Extract codes, including compact table notation such as ``IEN106,107``."""
    found: list[str] = []
    for prefix, first, remainder in re.findall(r"\b([A-Z]{2,4})\s*(\d{3})((?:\s*,\s*\d{3})*)", value.upper()):
        for number in [first, *re.findall(r"\d{3}", remainder)]:
            code = f"{prefix}{number}"
            if code != current and code not in found:
                found.append(code)
    return found


def table_prerequisites(text: str) -> dict[str, str]:
    """Read prerequisites from older handbooks' degree-plan table.

    The 2564–2566 PDFs often have no course-description catalogue.  Their
    prerequisite column is still present in the text layer, sometimes wrapped
    across two lines, so scan each row up to the next course code.
    """
    values: dict[str, str] = {}
    for page in text.split("\f"):
        if "Course Description" in page or "คำอธิบายรายวิชา" in page:
            break
        # This avoids course-number/credit catalogues later in several older
        # BUI PDFs.  Only the actual degree-plan tables label this column.
        if not re.search(r"\bPrerequisite\b|วิชาบังคับก่อน", page, re.I):
            continue
        lines = [(clean(line), len(line) - len(line.lstrip())) for line in page.splitlines()]
        for index, (line, _indent) in enumerate(lines):
            # Prerequisite cells can themselves begin with a code.  Only the
            # left-hand course column starts a new table row.
            if _indent >= 20:
                continue
            match = CODE.match(line)
            if not match:
                continue
            current = code_of(match.group(1))
            if not current:
                continue
            row = [line]
            for following, indent in lines[index + 1:index + 5]:
                # A code at the left table column starts the next course.  A
                # code far to the right is the prerequisite cell of this row.
                if CODE.match(following) and indent < 20:
                    break
                row.append(following)
            row_text = " ".join(row)
            codes = codes_in_prerequisite_row(row_text, current)
            if not codes:
                continue
            joined = " และ ".join(re.sub(r"([A-Z]+)(\d+)", r"\1 \2", code) for code in codes)
            if "สอบได้" in row_text:
                prerequisite = f"สอบได้ {joined}"
            else:
                # The BUI tables leave out "passed" for type (b): students
                # must have taken the course previously, but an F is allowed.
                prerequisite = f"เคยเรียน {joined}"
            if re.search(r"dean.?s? approval|อนุมัติจากคณบดี", row_text, re.I):
                prerequisite += " หรือได้รับอนุมัติจากคณบดี"
            values.setdefault(current, prerequisite)
    return values


def extract(path: Path, fallback_name: str, mode: str) -> dict[str, dict[str, dict[str, list[dict]]]]:
    """Return programme -> year level -> semester -> courses.

    The parser only consumes pages after a degree-plan heading and before the
    course-description section.  That prevents the catalogue tables later in
    each PDF from being mistaken for semester placements.
    """
    text = pdf_text(path)
    catalog = course_catalog(text)
    table_prereqs = table_prerequisites(text)
    out: dict[str, dict[str, dict[str, list[dict]]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    current_program, current_year, current_sem = fallback_name, None, None
    in_plan = False
    ended = False
    last_heading = fallback_name
    pending: dict | None = None
    prelude: list[str] = []

    def is_title_text(line: str) -> bool:
        if not re.search(r"[A-Za-z]", line):
            return False
        return not any(token in line.lower() for token in (
            "course title", "course number", "credits", "regular track",
            "cooperative", "academic year", "program of study", "degree plan",
            "bangkok university", "page ", "track track",
        ))

    def flush_pending() -> None:
        nonlocal pending
        if pending is None:
            return
        code = pending["course_code"]
        metadata = catalog.get(code, {})
        pending["course_name"] = metadata.get("name") or clean(pending["course_name"])
        pending["prerequisite"] = metadata.get("prerequisite", "-")
        if pending["prerequisite"] == "-":
            pending["prerequisite"] = table_prereqs.get(code, "-")
        # A subject without a title is invalid data; skip it instead of showing
        # its credit value as its name.
        if pending["course_name"]:
            bucket = out[current_program][current_year][current_sem]
            key = (pending["course_code"], pending["course_name"])
            if key not in {(c["course_code"], c["course_name"]) for c in bucket}:
                bucket.append(pending)
        pending = None
    for page in text.split("\f"):
        lines = [clean(line) for line in page.splitlines()]
        page_joined = " ".join(lines)
        # BUI PDFs mention "Degree Plan" in their cover/table of contents and
        # can mention it again in prose.  It is a start marker only on a page
        # that also contains a real year/semester table.  Once the course
        # description section begins, never re-enter extraction.
        if in_plan and ("คำอธิบายรายวิชา" in page_joined or "Course Description" in page_joined):
            in_plan = False
            ended = True
            continue
        if ended:
            continue
        if mode == "bui":
            has_year_semester = bool(
                re.search(r"\bYear\s*[1-4]\b", page_joined, re.I)
                and re.search(r"\bSemester\s*[1-3]\b", page_joined, re.I)
            ) or ("First Year" in page_joined and "First Semester" in page_joined)
            if "Program of Study" in page_joined or has_year_semester:
                in_plan = True
        elif "แผนการศึกษาตามหลักสูตร" in page_joined:
            in_plan = True
        if not in_plan:
            continue
        for line_idx, line in enumerate(lines):
            if not line:
                continue
            next_line = next((v for v in lines[line_idx + 1:] if v), "")
            if "สาขา" in line or "หลักสูตรสองภาษา" in line or "Bilingua Program" in line:
                flush_pending()
                last_heading = line
                current_program = program_name(line, fallback_name)
            if mode == "bui":
                track_match = TRACK.search(line)
                if track_match:
                    current_program = f"{fallback_name} — {clean(track_match.group(1))}"
            year_match = YEAR.search(line)
            if year_match:
                flush_pending()
                current_year, current_sem = year_match.group(1), None
                continue
            english_year = ENGLISH_YEAR.match(line)
            if english_year:
                flush_pending()
                current_year = {"first": "1", "second": "2", "third": "3", "fourth": "4"}[english_year.group(1).lower()]
                current_sem = None
                continue
            word_year = WORD_YEAR.search(line)
            if word_year:
                current_year = {"first": "1", "second": "2", "third": "3", "fourth": "4"}[word_year.group(1).lower()]
            numbered_year = NUMBERED_YEAR.search(line)
            if numbered_year:
                current_year = numbered_year.group(1)
            numbered_semester = NUMBERED_SEMESTER.search(line)
            if numbered_semester:
                flush_pending()
                current_sem = numbered_semester.group(1)
                continue
            if "First Semester" in line:
                flush_pending()
                current_sem = "1"
                continue
            if "Second Semester" in line:
                flush_pending()
                current_sem = "2"
                continue
            if "Summer" in line:
                flush_pending()
                current_sem = "3"
                continue
            if not (current_year and current_sem):
                continue
            match = CODE.match(line)
            if not match:
                if is_title_text(line):
                    next_match = CODE.match(next_line)
                    if next_match and not title_from(next_match.group(2))[0]:
                        # In several BUI tables the first title line is printed
                        # above its code/credit line.
                        prelude = [line]
                    elif pending is not None:
                        pending["course_name"] += " " + line
                    else:
                        prelude = [line]
                continue
            raw_code, rest = match.groups()
            title, credits = title_from(rest)
            # Headers and printed totals do not begin with a genuine code, but
            # this guard also avoids accepting a malformed fragment as a course.
            normalized_code = code_of(raw_code)
            if ((not title and normalized_code not in catalog)
                    or title.lower().startswith("course title")):
                continue
            flush_pending()
            course = {
                "course_code": normalized_code,
                "course_name": clean(" ".join(prelude + ([title] if title else []))),
                "credits": credits or 3,
                "prerequisite": "-",
            }
            prelude = []
            pending = course
    flush_pending()
    return out


def add_programmes(db: dict, academic_year: str, faculty_key: str, faculty_th: str,
                   faculty_en: str, programmes: dict) -> int:
    faculty = db["curricula"].setdefault(academic_year, {"faculties": {}})["faculties"].setdefault(
        faculty_key, {"faculty_name_th": faculty_th, "faculty_name_en": faculty_en, "departments": {}}
    )
    faculty["faculty_name_th"], faculty["faculty_name_en"] = faculty_th, faculty_en
    added = 0
    for name, years in programmes.items():
        if not years:
            continue
        course_index = {}
        for sems in years.values():
            for courses in sems.values():
                for course in courses:
                    if course["course_code"]:
                        course_index.setdefault(course["course_code"], dict(course))
        faculty["departments"][name] = {
            "department_name_th": name,
            "department_name_en": name,
            "tracks": {"default": {"track_name": "default", "plan_types": {
                "ปกติ": {"cohorts": {"รุ่น 1/1": {"year_levels": {
                    year: {"semesters": dict(sems)} for year, sems in years.items()
                }}}}
            }, "course_index": course_index}},
        }
        added += 1
    return added


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir", type=Path, required=True)
    args = parser.parse_args()
    db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    # This importer is authoritative for BUI.  Clear its previous import before
    # rebuilding it, otherwise removed/invalid records survive a later run.
    for year in YEARS:
        faculty = db["curricula"].get(year, {}).get("faculties", {}).get("bangkok-university-international")
        if faculty:
            faculty["departments"] = {}
    counts = defaultdict(int)
    for path in sorted(args.pdf_dir.rglob("*.pdf")):
        match = re.match(r"(bui|buci)-(256[4-9])(?:-(.*))?\.pdf$", path.name)
        if not match:
            continue
        kind, year, name = match.groups()
        fallback = clean((name or "วิทยาลัยนานาชาติจีน").replace("-", " "))
        programmes = extract(path, fallback, kind)
        if kind == "bui":
            counts[year] += add_programmes(db, year, "bangkok-university-international",
                                            "วิทยาลัยนานาชาติ", "Bangkok University International", programmes)
        else:
            counts[year] += add_programmes(db, year, "bangkok-university-chinese-international-college",
                                            "วิทยาลัยนานาชาติจีน", "Bangkok University Chinese International College", programmes)
    db["metadata"]["academic_years"] = sorted(YEARS, reverse=True)
    db["metadata"]["faculty_count"] = len({
        faculty for year in YEARS for faculty in db["curricula"].get(year, {}).get("faculties", {})
    })
    DB_PATH.write_text(json.dumps(db, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for year in sorted(counts, reverse=True):
        print(f"{year}: imported {counts[year]} international programmes")


if __name__ == "__main__":
    main()
