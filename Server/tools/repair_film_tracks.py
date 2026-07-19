#!/usr/bin/env python3
"""Repair Film degree plans whose PDF specializations were flattened together.

The official BU Film year-plan PDFs put one Year 3 specialization on each
page.  The original import lost those page headings and appended every page to
the department's ``default`` track, producing 60/76-course semesters.

This script replaces that corrupted track for every available academic year.
The 2564 curriculum has 10 official specialization tracks; the 2565-2569
curricula have 11.  Years 1-2 remain cohort-specific; Years 3-4 are rebuilt
from the official plan tables.

Official sources:
  2564 https://degreeplan.bu.ac.th/download/3378/
  2565 https://degreeplan.bu.ac.th/download/3585/
  2566 https://degreeplan.bu.ac.th/download/3727/
  2567 https://degreeplan.bu.ac.th/download/3859/
  2568 https://contents.bu.ac.th/contents/files/uploads/department-20240531120259.pdf
  2569 https://contents.bu.ac.th/contents/files/uploads/department-20250430072746.pdf

Usage:
    python3 tools/repair_film_tracks.py
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "Server" / "curriculum_database.json"
FACULTY = "school-of-digital-media-and-cinematic-arts"
DEPARTMENT_BY_YEAR = {
    "2564": "สาขาภาพยนตร์",
    "2565": "สาขาภาพยนตร์",
    "2566": "สาขาวิชาภาพยนตร์",
    "2567": "สาขาวิชาภาพยนตร์",
    "2568": "สาขาวิชาภาพยนตร์",
    "2569": "สาขาวิชาภาพยนตร์",
}
ACADEMIC_YEARS = tuple(DEPARTMENT_BY_YEAR)


def norm_code(value: str | None) -> str:
    return re.sub(r"\s+", "", value or "").upper()


def spaced_code(value: str) -> str:
    normalized = norm_code(value)
    match = re.fullmatch(r"([A-Z]+)(\d+[A-Z]?)", normalized)
    return f"{match.group(1)} {match.group(2)}" if match else normalized


# Exact Year 3 tables from the official 2568/2569 Film plans.  Shared minor
# and elective slots deliberately have no invented course code.
TRACKS: dict[str, dict[str, list[tuple[str | None, str]]]] = {
    "การผลิตภาพยนตร์กลุ่มการเขียนบท": {
        "1": [
            ("DCA006", "The Arts and Politics in Cinema"),
            ("FMS315", "Screenwriting Workshop"),
            ("FMS323", "Screenwriting for Specific Genres"),
            ("FMS433", "Film Production II"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("DCA007", "Cinema and Literature"),
            ("FMS309", "Film Analysis and Criticism"),
            ("FMS319", "Advanced Screenwriting Workshop"),
            ("FMS434", "Film Production III"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การผลิตภาพยนตร์กลุ่มการกำกับ": {
        "1": [
            ("DCA006", "The Arts and Politics in Cinema"),
            ("FMS310", "Directing Actors"),
            ("FMS325", "Film Authorship"),
            ("FMS433", "Film Production II"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("DCA007", "Cinema and Literature"),
            ("FMS309", "Film Analysis and Criticism"),
            ("FMS329", "Scene Directing"),
            ("FMS434", "Film Production III"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การผลิตภาพยนตร์กลุ่มการบริหารงานกองถ่าย": {
        "1": [
            ("DCA006", "The Arts and Politics in Cinema"),
            ("FMS330", "Production Planning"),
            ("FMS337", "Budgeting and Scheduling"),
            ("FMS433", "Film Production II"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("DCA007", "Cinema and Literature"),
            ("FMS309", "Film Analysis and Criticism"),
            ("FMS339", "Foreign Film Production Service"),
            ("FMS434", "Film Production III"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การผลิตภาพยนตร์กลุ่มการออกแบบงานสร้างภาพยนตร์": {
        "1": [
            ("DCA006", "The Arts and Politics in Cinema"),
            ("FMS345", "Production Design for Film"),
            ("FMS347", "Costume Design and Special Effects Makeup"),
            ("FMS433", "Film Production II"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("DCA007", "Cinema and Literature"),
            ("FMS309", "Film Analysis and Criticism"),
            ("FMS346", "Set Decoration and Props Making"),
            ("FMS434", "Film Production III"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การผลิตภาพยนตร์กลุ่มการถ่ายภาพภาพยนตร์": {
        "1": [
            ("DCA006", "The Arts and Politics in Cinema"),
            ("FMS350", "Advanced Cinematography"),
            ("FMS357", "Shot and Frame Design"),
            ("FMS433", "Film Production II"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("DCA007", "Cinema and Literature"),
            ("FMS309", "Film Analysis and Criticism"),
            ("FMS355", "Lighting for Film and Television"),
            ("FMS434", "Film Production III"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การผลิตภาพยนตร์กลุ่มการลำดับภาพ": {
        "1": [
            ("DCA006", "The Arts and Politics in Cinema"),
            ("FMS360", "Post Production Workshop"),
            ("FMS369", "Aesthetics of Editing"),
            ("FMS433", "Film Production II"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("DCA007", "Cinema and Literature"),
            ("FMS309", "Film Analysis and Criticism"),
            ("FMS367", "Film Editing"),
            ("FMS434", "Film Production III"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การผลิตภาพยนตร์กลุ่มการบันทึกและออกแบบเสียง": {
        "1": [
            ("DCA006", "The Arts and Politics in Cinema"),
            ("FMS370", "Sound Recording for Film"),
            ("FMS377", "Audio Post Production Workshop"),
            ("FMS433", "Film Production II"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("DCA007", "Cinema and Literature"),
            ("FMS309", "Film Analysis and Criticism"),
            ("FMS375", "Sound Design and Scoring for Film"),
            ("FMS434", "Film Production III"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "ธุรกิจภาพยนตร์และสื่อจอ": {
        "1": [
            ("DCA006", "The Arts and Politics in Cinema"),
            ("FMS380", "Marketing and Distribution"),
            ("FMS383", "Pitching and Financing"),
            ("FMS337", "Budgeting and Scheduling"),
            ("FMS381", "Film Curating and Exhibition"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("DCA007", "Cinema and Literature"),
            ("FMS309", "Film Analysis and Criticism"),
            ("FMS339", "Foreign Film Production Service"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "ภาพยนตร์ศึกษาและการผลิตภาพยนตร์ทางเลือก": {
        "1": [
            ("DCA006", "The Arts and Politics in Cinema"),
            ("FMS325", "Film Authorship"),
            ("FMS390", "Contemporary Themes in Film: Theory and Practice"),
            ("FMS493", "Alternative Filmmaking Workshop"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("DCA007", "Cinema and Literature"),
            ("FMS309", "Film Analysis and Criticism"),
            ("FMS327", "Space, Time, Sound and Moving Image"),
            ("FMS391", "Advanced Film Aesthetics"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การแสดงสำหรับภาพยนตร์": {
        "1": [
            ("DCA006", "The Arts and Politics in Cinema"),
            ("FMS411", "Advanced Acting for Screen"),
            ("FMS415", "Voice and Movement for the Screen Actor"),
            ("FMS419", "Casting and Audition Techniques"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("DCA007", "Cinema and Literature"),
            ("FMS309", "Film Analysis and Criticism"),
            ("FMS413", "Acting for Specific Genres"),
            ("FMS417", "Advanced Acting Techniques"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การผลิตซีรีส์ (Series Production)": {
        "1": [
            ("DCA006", "The Arts and Politics in Cinema"),
            ("FMS425", "Trend in Global and Regional Context for Series"),
            ("FMS421", "Audience and Series Analysis"),
            ("FMS423", "Screenwriting for Series"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("DCA007", "Cinema and Literature"),
            ("FMS309", "Film Analysis and Criticism"),
            ("FMS429", "Series Production"),
            ("FMS427", "Series Pitching and Development"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
}


# The 2564 plan belongs to the preceding curriculum and uses FM/CA codes.
TRACKS_2564: dict[str, dict[str, list[tuple[str | None, str]]]] = {
    "การผลิตภาพยนตร์กลุ่มการเขียนบท": {
        "1": [
            ("FM300", "Directing for the Screen"),
            ("FM310", "Directing Actors"),
            ("FM315", "Screenwriting Workshop"),
            ("CA006", "Marketing Communication in Digital Age"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("FM309", "Film Analysis and Criticism"),
            ("FM319", "Advanced Screenwriting Workshop"),
            ("FM433", "Film Production I"),
            ("FM431", "Creative Strategies for Entrepreneurship in Entertainment Business"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การผลิตภาพยนตร์กลุ่มการกำกับ": {
        "1": [
            ("FM300", "Directing for the Screen"),
            ("FM310", "Directing Actors"),
            ("FM325", "Film Authorship"),
            ("CA006", "Marketing Communication in Digital Age"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("FM309", "Film Analysis and Criticism"),
            ("FM329", "Character Studies"),
            ("FM433", "Film Production I"),
            ("FM431", "Creative Strategies for Entrepreneurship in Entertainment Business"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การผลิตภาพยนตร์กลุ่มการบริหารงานกองถ่าย": {
        "1": [
            ("FM300", "Directing for the Screen"),
            ("FM330", "Production Planning for Film"),
            ("FM337", "Budgeting and Scheduling"),
            ("CA006", "Marketing Communication in Digital Age"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("FM309", "Film Analysis and Criticism"),
            ("FM339", "Foreign Film Production Service"),
            ("FM433", "Film Production I"),
            ("FM431", "Creative Strategies for Entrepreneurship in Entertainment Business"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การผลิตภาพยนตร์กลุ่มการออกแบบงานสร้างภาพยนตร์": {
        "1": [
            ("FM300", "Directing for the Screen"),
            ("FM340", "Art Direction"),
            ("FM347", "Art Appreciation for Film"),
            ("CA006", "Marketing Communication in Digital Age"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("FM309", "Film Analysis and Criticism"),
            ("FM345", "Production Design for Film"),
            ("FM433", "Film Production I"),
            ("FM431", "Creative Strategies for Entrepreneurship in Entertainment Business"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การผลิตภาพยนตร์กลุ่มการถ่ายภาพภาพยนตร์": {
        "1": [
            ("FM300", "Directing for the Screen"),
            ("FM350", "Advanced Cinematography"),
            ("FM347", "Art Appreciation for Film"),
            ("CA006", "Marketing Communication in Digital Age"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("FM309", "Film Analysis and Criticism"),
            ("FM355", "Lighting for Film and Television"),
            ("FM433", "Film Production I"),
            ("FM431", "Creative Strategies for Entrepreneurship in Entertainment Business"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การผลิตภาพยนตร์กลุ่มการลำดับภาพ": {
        "1": [
            ("FM300", "Directing for the Screen"),
            ("FM360", "Post Production Workshop"),
            ("FM367", "Film Editing"),
            ("CA006", "Marketing Communication in Digital Age"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("FM309", "Film Analysis and Criticism"),
            ("FM365", "Visual Effects for Film"),
            ("FM433", "Film Production I"),
            ("FM431", "Creative Strategies for Entrepreneurship in Entertainment Business"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การผลิตภาพยนตร์กลุ่มการบันทึกและออกแบบเสียง": {
        "1": [
            ("FM300", "Directing for the Screen"),
            ("FM370", "Sound Recording for Film"),
            ("FM377", "Audio Post Production Workshop"),
            ("CA006", "Marketing Communication in Digital Age"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("FM309", "Film Analysis and Criticism"),
            ("FM375", "Sound Design for Film"),
            ("FM433", "Film Production I"),
            ("FM431", "Creative Strategies for Entrepreneurship in Entertainment Business"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "ธุรกิจภาพยนตร์และสื่อจอ": {
        "1": [
            ("FM380", "Marketing and Distribution"),
            ("FM383", "Pitching and Financing"),
            ("FM337", "Budgeting and Scheduling"),
            ("FM339", "Foreign Film Production Service"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("CA006", "Marketing Communication in Digital Age"),
            ("FM309", "Film Analysis and Criticism"),
            ("FM381", "Film Curating and Exhibition"),
            ("FM431", "Creative Strategies for Entrepreneurship in Entertainment Business"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "ภาพยนตร์ศึกษาและการผลิตภาพยนตร์ทางเลือก": {
        "1": [
            ("FM309", "Film Analysis and Criticism"),
            ("FM390", "Contemporary Themes in Film: Theory and Practice"),
            ("FM391", "Advanced Film Aesthetics"),
            ("CA006", "Marketing Communication in Digital Age"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("FM325", "Film Authorship"),
            ("FM327", "Space, Time, Sound and Moving Image"),
            ("FM393", "Film and Spectatorship"),
            ("FM431", "Creative Strategies for Entrepreneurship in Entertainment Business"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
    "การแสดงสำหรับภาพยนตร์": {
        "1": [
            ("FM409", "History of Screen Acting"),
            ("FM411", "Acting for Screen"),
            ("FM415", "Voice and Movement for the Screen Actor"),
            ("FM419", "Casting and Audition Techniques"),
            (None, "Minor I"),
            (None, "Minor II"),
        ],
        "2": [
            ("FM309", "Film Analysis and Criticism"),
            ("FM413", "Acting for Specific Genres"),
            ("FM431", "Creative Strategies for Entrepreneurship in Entertainment Business"),
            ("CA006", "Marketing Communication in Digital Age"),
            (None, "Minor III"),
            (None, "Minor IV"),
            (None, "Free Elective I"),
        ],
    },
}


YEAR_4 = {
    "1": [
        ("FMS435", "Degree Project Research and Development"),
        (None, "Minor V"),
        (None, "Free Elective II"),
    ],
    "2": [
        (
            None,
            "FMS 400 Career Preparation in Screen Media หรือ "
            "FMS 487 Internship in Film and Screen Media Business",
        ),
        ("FMS436", "Degree Project in Cinematic Arts"),
    ],
}


YEAR_4_2564_COMMON_SEMESTER_2 = [
    ("FM400", "Seminar in Film and Society"),
    ("FM436", "Degree Project in Cinematic Arts"),
]


YEAR_4_2564_BY_TRACK = {
    "production": {
        "1": [
            ("FM434", "Film Production II"),
            ("FM435", "Degree Project Research and Development"),
            (None, "Minor V"),
            (None, "Free Elective II"),
        ],
        "2": YEAR_4_2564_COMMON_SEMESTER_2,
    },
    "ธุรกิจภาพยนตร์และสื่อจอ": {
        "1": [
            ("FM435", "Degree Project Research and Development"),
            (None, "FM 487 Film Internship หรือ FM 489 Individual Project"),
            (None, "Minor V"),
            (None, "Free Elective II"),
        ],
        "2": YEAR_4_2564_COMMON_SEMESTER_2,
    },
    "ภาพยนตร์ศึกษาและการผลิตภาพยนตร์ทางเลือก": {
        "1": [
            ("FM493", "Alternative Filmmaking Workshop"),
            ("FM435", "Degree Project Research and Development"),
            (None, "Minor V"),
            (None, "Free Elective II"),
        ],
        "2": YEAR_4_2564_COMMON_SEMESTER_2,
    },
    "การแสดงสำหรับภาพยนตร์": {
        "1": [
            ("FM417", "Advanced Acting Techniques"),
            ("FM435", "Degree Project Research and Development"),
            (None, "Minor V"),
            (None, "Free Elective II"),
        ],
        "2": [
            ("FM400", "Seminar in Film and Society"),
            ("FM436", "Degree Project in Film"),
        ],
    },
}


def source_course_index(tracks: dict) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for track in tracks.values():
        for code, course in track.get("course_index", {}).items():
            normalized = norm_code(code)
            if normalized:
                index[normalized] = course
    return index


def make_course(
    code: str | None,
    name: str,
    source_index: dict[str, dict],
) -> dict:
    normalized = norm_code(code)
    source = source_index.get(normalized, {}) if normalized else {}
    return {
        "course_code": spaced_code(normalized) if normalized else None,
        "course_name": name,
        "credits": 3,
        "prerequisite": source.get("prerequisite") or "-",
    }


def make_semester(
    rows: list[tuple[str | None, str]],
    source_index: dict[str, dict],
) -> list[dict]:
    return [make_course(code, name, source_index) for code, name in rows]


def build_course_index(cohorts: dict) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for cohort in cohorts.values():
        for year in cohort["year_levels"].values():
            for semester in year["semesters"].values():
                for course in semester:
                    code = course.get("course_code")
                    if code and code not in index:
                        index[code] = copy.deepcopy(course)
    return index


def plan_coverage(department: dict) -> int:
    """Prefer the accidental department record that still has Years 1-2."""
    coverage = 0
    for track in department["tracks"].values():
        plan = track.get("plan_types", {}).get("ปกติ", {})
        for cohort in plan.get("cohorts", {}).values():
            coverage = max(coverage, len(cohort.get("year_levels", {})))
    return coverage


def year_4_for_track(
    academic_year: str,
    track_name: str,
) -> dict[str, list[tuple[str | None, str]]]:
    if academic_year != "2564":
        return YEAR_4
    if track_name.startswith("การผลิตภาพยนตร์"):
        return YEAR_4_2564_BY_TRACK["production"]
    return YEAR_4_2564_BY_TRACK[track_name]


def repair_year(db: dict, academic_year: str) -> None:
    departments = db["curricula"][academic_year]["faculties"][FACULTY]["departments"]
    film_names = set(DEPARTMENT_BY_YEAR.values())
    source_departments = [
        department
        for name, department in departments.items()
        if name in film_names
    ]
    assert source_departments, academic_year

    source_department = max(source_departments, key=plan_coverage)
    source_track = source_department["tracks"].get("default") or next(
        iter(source_department["tracks"].values())
    )
    source_plan = source_track["plan_types"]["ปกติ"]
    source_index: dict[str, dict] = {}
    for department in source_departments:
        source_index.update(source_course_index(department["tracks"]))

    track_tables = TRACKS_2564 if academic_year == "2564" else TRACKS

    repaired_tracks: dict[str, dict] = {}
    for track_name, year_3 in track_tables.items():
        cohorts: dict[str, dict] = {}
        for cohort_name, old_cohort in source_plan["cohorts"].items():
            old_years = old_cohort["year_levels"]
            years = {
                year: copy.deepcopy(old_years[year])
                for year in ("1", "2")
                if year in old_years
            }
            years["3"] = {
                "semesters": {
                    semester: make_semester(rows, source_index)
                    for semester, rows in year_3.items()
                }
            }
            years["4"] = {
                "semesters": {
                    semester: make_semester(rows, source_index)
                    for semester, rows in year_4_for_track(
                        academic_year, track_name
                    ).items()
                }
            }
            cohorts[cohort_name] = {"year_levels": years}

        repaired_tracks[track_name] = {
            "track_name": track_name,
            "course_index": build_course_index(cohorts),
            "plan_types": {"ปกติ": {"cohorts": cohorts}},
        }

    destination_name = DEPARTMENT_BY_YEAR[academic_year]
    destination = copy.deepcopy(departments.get(destination_name, source_department))
    destination["department_name_th"] = destination_name
    destination["tracks"] = repaired_tracks

    # 2565 was imported twice: a full corrupted department and a partial clean
    # Year-3 department.  Keep one official department after combining them.
    for name in film_names - {destination_name}:
        departments.pop(name, None)
    departments[destination_name] = destination


def validate(db: dict) -> None:
    for academic_year in ACADEMIC_YEARS:
        department_name = DEPARTMENT_BY_YEAR[academic_year]
        departments = db["curricula"][academic_year]["faculties"][FACULTY][
            "departments"
        ]
        unexpected_names = (
            set(DEPARTMENT_BY_YEAR.values()) - {department_name}
        ) & set(departments)
        assert not unexpected_names, (academic_year, unexpected_names)
        tracks = departments[department_name]["tracks"]
        expected_track_count = 10 if academic_year == "2564" else 11
        assert len(tracks) == expected_track_count, (academic_year, len(tracks))
        for track_name, track in tracks.items():
            cohorts = track["plan_types"]["ปกติ"]["cohorts"]
            for cohort_name, cohort in cohorts.items():
                years = cohort["year_levels"]
                semester_1 = years["3"]["semesters"]["1"]
                semester_2 = years["3"]["semesters"]["2"]
                expected = (
                    (7, 6)
                    if academic_year != "2564"
                    and track_name == "ธุรกิจภาพยนตร์และสื่อจอ"
                    else (6, 7)
                )
                actual = (len(semester_1), len(semester_2))
                assert actual == expected, (
                    academic_year,
                    track_name,
                    cohort_name,
                    actual,
                )
                assert sum(c["credits"] for c in semester_1) in (18, 21)
                assert sum(c["credits"] for c in semester_2) in (18, 21)
                expected_year_4_semester_1 = 12 if academic_year == "2564" else 9
                assert (
                    sum(c["credits"] for c in years["4"]["semesters"]["1"])
                    == expected_year_4_semester_1
                )
                assert sum(c["credits"] for c in years["4"]["semesters"]["2"]) == 6


def main() -> None:
    db = json.loads(DB_PATH.read_text(encoding="utf-8"))
    for academic_year in ACADEMIC_YEARS:
        repair_year(db, academic_year)
    validate(db)
    DB_PATH.write_text(
        json.dumps(db, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Repaired Film tracks for {', '.join(ACADEMIC_YEARS)}")
    print("Tracks per year: 10 (2564), 11 (2565-2569)")


if __name__ == "__main__":
    main()
