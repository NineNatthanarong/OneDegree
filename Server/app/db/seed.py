from __future__ import annotations

import hashlib
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from slugify import slugify
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import Base, get_engine
from app.db.models import (
    AcademicYear,
    Cohort,
    CourseCatalogEntry,
    Department,
    Faculty,
    ImportState,
    PlanType,
    SemesterCourse,
    Track,
)

logger = logging.getLogger(__name__)


def _normalize_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_credits(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_slug(raw_value: Optional[str], fallback_prefix: str, seen: set[str]) -> str:
    source = raw_value or fallback_prefix
    base = slugify(source, separator="-", lowercase=True)
    if not base:
        digest = hashlib.sha1(source.encode("utf-8")).hexdigest()[:10]
        base = f"{fallback_prefix}-{digest}"

    candidate = base
    suffix = 2
    while candidate in seen:
        candidate = f"{base}-{suffix}"
        suffix += 1
    seen.add(candidate)
    return candidate


@lru_cache(maxsize=4)
def load_dataset(dataset_path: str) -> Tuple[Dict[str, Any], str]:
    path = Path(dataset_path)
    if not path.exists():
        raise FileNotFoundError(f"Seed data file not found: {path}")

    raw_bytes = path.read_bytes()
    payload = json.loads(raw_bytes)
    checksum = hashlib.sha256(raw_bytes).hexdigest()
    return payload, checksum


def get_dataset_metadata() -> dict[str, Any]:
    settings = get_settings()
    payload, _ = load_dataset(settings.seed_data_path)
    metadata = payload.get("metadata", {})
    return {
        "generated_at": metadata.get("generated_at"),
        "academic_years": metadata.get("academic_years", []),
        "faculty_count": metadata.get("faculty_count"),
    }


def initialize_database() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    sync_seed_data(engine)

def sync_seed_data(engine) -> None:
    settings = get_settings()
    payload, checksum = load_dataset(settings.seed_data_path)
    metadata = payload.get("metadata", {})
    with Session(bind=engine) as session:
        import_state = session.get(ImportState, 1)
        academic_year_count = session.scalar(select(func.count(AcademicYear.id))) or 0
        if import_state and import_state.dataset_checksum == checksum and academic_year_count > 0:
            logger.info("Seed data already up to date; skipping import.")
            return

    logger.info("Rebuilding schema and importing curriculum data...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with Session(bind=engine) as session:
        _seed_payload(session, payload, checksum, metadata.get("generated_at"))
        session.commit()
    logger.info("Curriculum import completed.")


def _seed_payload(
    session: Session,
    payload: Dict[str, Any],
    checksum: str,
    generated_at: Optional[str],
) -> None:
    for year_value, year_payload in payload.get("curricula", {}).items():
        academic_year = AcademicYear(year=str(year_value))
        session.add(academic_year)

        faculties_payload = year_payload.get("faculties", {})
        for faculty_slug, faculty_payload in faculties_payload.items():
            faculty = Faculty(
                academic_year=academic_year,
                source_slug=str(faculty_slug),
                name_th=_normalize_text(faculty_payload.get("faculty_name_th")) or str(faculty_slug),
                name_en=_normalize_text(faculty_payload.get("faculty_name_en")),
            )
            session.add(faculty)

            department_slug_seen: set[str] = set()
            for department_name, department_payload in faculty_payload.get("departments", {}).items():
                department = Department(
                    faculty=faculty,
                    slug=_build_slug(_normalize_text(department_name), "department", department_slug_seen),
                    name_th=_normalize_text(department_payload.get("department_name_th")) or str(department_name),
                    name_en=_normalize_text(department_payload.get("department_name_en")),
                )
                session.add(department)

                track_slug_seen: set[str] = set()
                for track_name, track_payload in department_payload.get("tracks", {}).items():
                    track = Track(
                        department=department,
                        slug=_build_slug(_normalize_text(track_name), "track", track_slug_seen),
                        name=_normalize_text(track_payload.get("track_name")) or str(track_name),
                    )
                    session.add(track)

                    session.flush()

                    catalog_entries: dict[str, CourseCatalogEntry] = {}
                    for course_code, course_payload in track_payload.get("course_index", {}).items():
                        normalized_code = _normalize_text(course_code)
                        if not normalized_code:
                            continue
                        entry = CourseCatalogEntry(
                            track=track,
                            code=normalized_code,
                            name=_normalize_text(course_payload.get("course_name")) or normalized_code,
                            credits=_normalize_credits(course_payload.get("credits")),
                            prerequisite=_normalize_text(course_payload.get("prerequisite")),
                        )
                        session.add(entry)
                        catalog_entries[normalized_code] = entry

                    plan_slug_seen: set[str] = set()
                    for plan_name, plan_payload in track_payload.get("plan_types", {}).items():
                        plan_type = PlanType(
                            track=track,
                            slug=_build_slug(_normalize_text(plan_name), "plan", plan_slug_seen),
                            name=_normalize_text(plan_name) or "default",
                        )
                        session.add(plan_type)

                        cohort_slug_seen: set[str] = set()
                        for cohort_name, cohort_payload in plan_payload.get("cohorts", {}).items():
                            cohort = Cohort(
                                plan_type=plan_type,
                                slug=_build_slug(_normalize_text(cohort_name), "cohort", cohort_slug_seen),
                                name=_normalize_text(cohort_name) or "default",
                            )
                            session.add(cohort)

                            for year_level, year_level_payload in cohort_payload.get("year_levels", {}).items():
                                normalized_year_level = int(year_level)
                                for semester, semester_courses in year_level_payload.get("semesters", {}).items():
                                    normalized_semester = int(semester)
                                    for position, course_payload in enumerate(semester_courses, start=1):
                                        course_code = _normalize_text(course_payload.get("course_code"))
                                        session.add(
                                            SemesterCourse(
                                                cohort=cohort,
                                                course_catalog_entry=catalog_entries.get(course_code) if course_code else None,
                                                year_level=normalized_year_level,
                                                semester=normalized_semester,
                                                position=position,
                                                course_code=course_code,
                                                course_name=_normalize_text(course_payload.get("course_name"))
                                                or "Unnamed course",
                                                credits=_normalize_credits(course_payload.get("credits")),
                                                prerequisite=_normalize_text(course_payload.get("prerequisite")),
                                            )
                                        )

    session.add(
        ImportState(
            id=1,
            dataset_checksum=checksum,
            source_generated_at=generated_at,
        )
    )
