from __future__ import annotations

from collections import defaultdict
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db_session
from app.db.models import AcademicYear, Cohort, CourseCatalogEntry, Department, Faculty, PlanType, SemesterCourse, Track
from app.db.seed import get_dataset_metadata
from app.schemas import (
    AcademicYearOption,
    CohortRef,
    DatabaseCounts,
    DegreePlanCohort,
    DegreePlanCourse,
    DegreePlanLookupResponse,
    DegreePlanOptions,
    DegreePlanQuery,
    DegreePlanResponse,
    DegreePlanSemester,
    DegreePlanYear,
    DepartmentRef,
    FacultyRef,
    HealthResponse,
    MetadataResponse,
    PlanTypeRef,
    SourceMetadata,
    TrackRef,
)

router = APIRouter()


def _faculty_ref(faculty: Faculty) -> FacultyRef:
    return FacultyRef(
        id=faculty.id,
        slug=faculty.source_slug,
        name_th=faculty.name_th,
        name_en=faculty.name_en,
    )


def _department_ref(department: Department) -> DepartmentRef:
    return DepartmentRef(
        id=department.id,
        slug=department.slug,
        name_th=department.name_th,
        name_en=department.name_en,
    )


def _track_ref(track: Track) -> TrackRef:
    return TrackRef(
        id=track.id,
        slug=track.slug,
        name=track.name,
    )


def _plan_type_ref(plan_type: PlanType) -> PlanTypeRef:
    return PlanTypeRef(
        id=plan_type.id,
        slug=plan_type.slug,
        name=plan_type.name,
    )


def _cohort_ref(cohort: Cohort) -> CohortRef:
    return CohortRef(
        id=cohort.id,
        slug=cohort.slug,
        name=cohort.name,
    )


def _get_academic_year(session: Session, academic_year: str) -> AcademicYear:
    row = session.scalar(select(AcademicYear).where(AcademicYear.year == academic_year))
    if row is None:
        raise HTTPException(status_code=404, detail="Academic year not found")
    return row


def _get_faculty(session: Session, academic_year: str, faculty_slug: str) -> Faculty:
    row = session.scalar(
        select(Faculty)
        .join(Faculty.academic_year)
        .where(
            AcademicYear.year == academic_year,
            Faculty.source_slug == faculty_slug,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return row


def _get_department(session: Session, academic_year: str, faculty_slug: str, department_slug: str) -> Department:
    row = session.scalar(
        select(Department)
        .join(Department.faculty)
        .join(Faculty.academic_year)
        .where(
            AcademicYear.year == academic_year,
            Faculty.source_slug == faculty_slug,
            Department.slug == department_slug,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Department not found")
    return row


def _get_track(
    session: Session,
    academic_year: str,
    faculty_slug: str,
    department_slug: str,
    track_slug: str,
) -> Track:
    row = session.scalar(
        select(Track)
        .join(Track.department)
        .join(Department.faculty)
        .join(Faculty.academic_year)
        .where(
            AcademicYear.year == academic_year,
            Faculty.source_slug == faculty_slug,
            Department.slug == department_slug,
            Track.slug == track_slug,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return row


def _get_plan(
    session: Session,
    academic_year: str,
    faculty_slug: str,
    department_slug: str,
    track_slug: str,
    plan_slug: str,
) -> PlanType:
    row = session.scalar(
        select(PlanType)
        .join(PlanType.track)
        .join(Track.department)
        .join(Department.faculty)
        .join(Faculty.academic_year)
        .where(
            AcademicYear.year == academic_year,
            Faculty.source_slug == faculty_slug,
            Department.slug == department_slug,
            Track.slug == track_slug,
            PlanType.slug == plan_slug,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return row


def _validate_query_order(
    academic_year: Optional[str],
    faculty_slug: Optional[str],
    department_slug: Optional[str],
    track_slug: Optional[str],
    plan_slug: Optional[str],
) -> None:
    if faculty_slug and not academic_year:
        raise HTTPException(status_code=400, detail="academic_year is required before faculty_slug")
    if department_slug and not faculty_slug:
        raise HTTPException(status_code=400, detail="faculty_slug is required before department_slug")
    if track_slug and not department_slug:
        raise HTTPException(status_code=400, detail="department_slug is required before track_slug")
    if plan_slug and not track_slug:
        raise HTTPException(status_code=400, detail="track_slug is required before plan_slug")


def _build_degree_plan_years(cohort: Cohort) -> tuple[list[DegreePlanYear], int]:
    schedule_tree: dict[int, dict[int, list[SemesterCourse]]] = defaultdict(lambda: defaultdict(list))
    total_credits = 0

    for scheduled_course in sorted(
        cohort.semester_courses,
        key=lambda item: (item.year_level, item.semester, item.position),
    ):
        schedule_tree[scheduled_course.year_level][scheduled_course.semester].append(scheduled_course)
        total_credits += scheduled_course.credits or 0

    years: list[DegreePlanYear] = []
    for year_level in sorted(schedule_tree):
        year_total = 0
        semesters: list[DegreePlanSemester] = []
        for semester_no in sorted(schedule_tree[year_level]):
            semester_courses = schedule_tree[year_level][semester_no]
            semester_total = sum(course.credits or 0 for course in semester_courses)
            year_total += semester_total
            semesters.append(
                DegreePlanSemester(
                    semester=semester_no,
                    total_credits=semester_total,
                    courses=[
                        DegreePlanCourse(
                            id=course.id,
                            sequence=course.position,
                            code=course.course_code,
                            name=course.course_name,
                            credits=course.credits,
                            prerequisite=course.prerequisite,
                        )
                        for course in semester_courses
                    ],
                )
            )
        years.append(
            DegreePlanYear(
                year=year_level,
                total_credits=year_total,
                semesters=semesters,
            )
        )

    return years, total_credits


def _build_degree_plan_result(
    session: Session,
    academic_year: str,
    faculty_slug: str,
    department_slug: str,
    track_slug: str,
    plan_slug: str,
) -> DegreePlanResponse:
    faculty = _get_faculty(session, academic_year, faculty_slug)
    department = _get_department(session, academic_year, faculty_slug, department_slug)
    track = _get_track(session, academic_year, faculty_slug, department_slug, track_slug)
    plan = _get_plan(session, academic_year, faculty_slug, department_slug, track_slug, plan_slug)

    cohorts = session.scalars(
        select(Cohort)
        .where(Cohort.plan_type_id == plan.id)
        .options(selectinload(Cohort.semester_courses))
        .order_by(Cohort.name.asc())
    ).all()
    if not cohorts:
        raise HTTPException(status_code=404, detail="Degree plan not found")

    cohort_rows: list[DegreePlanCohort] = []
    for cohort in cohorts:
        years, total_credits = _build_degree_plan_years(cohort)
        cohort_rows.append(
            DegreePlanCohort(
                cohort=_cohort_ref(cohort),
                total_credits=total_credits,
                years=years,
            )
        )

    return DegreePlanResponse(
        academic_year=academic_year,
        faculty=_faculty_ref(faculty),
        department=_department_ref(department),
        track=_track_ref(track),
        plan=_plan_type_ref(plan),
        cohort_count=len(cohort_rows),
        cohorts=cohort_rows,
    )


@router.get("/health", response_model=HealthResponse, tags=["system"])
def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/metadata", response_model=MetadataResponse, tags=["system"])
def metadata(session: Session = Depends(get_db_session)) -> MetadataResponse:
    source_metadata = get_dataset_metadata()
    counts = DatabaseCounts(
        academic_years=session.scalar(select(func.count(AcademicYear.id))) or 0,
        faculties=session.scalar(select(func.count(Faculty.id))) or 0,
        departments=session.scalar(select(func.count(Department.id))) or 0,
        tracks=session.scalar(select(func.count(Track.id))) or 0,
        plan_types=session.scalar(select(func.count(PlanType.id))) or 0,
        cohorts=session.scalar(select(func.count(Cohort.id))) or 0,
        course_catalog_entries=session.scalar(select(func.count(CourseCatalogEntry.id))) or 0,
        semester_courses=session.scalar(select(func.count(SemesterCourse.id))) or 0,
    )
    return MetadataResponse(
        source=SourceMetadata(**source_metadata),
        database_counts=counts,
    )


@router.get("/degree-plan", response_model=DegreePlanLookupResponse, tags=["degree-plan"])
def degree_plan_lookup(
    academic_year: Optional[str] = None,
    faculty_slug: Optional[str] = None,
    department_slug: Optional[str] = None,
    track_slug: Optional[str] = None,
    plan_slug: Optional[str] = None,
    session: Session = Depends(get_db_session),
) -> DegreePlanLookupResponse:
    _validate_query_order(
        academic_year=academic_year,
        faculty_slug=faculty_slug,
        department_slug=department_slug,
        track_slug=track_slug,
        plan_slug=plan_slug,
    )

    selected = DegreePlanQuery(
        academic_year=academic_year,
        faculty_slug=faculty_slug,
        department_slug=department_slug,
        track_slug=track_slug,
        plan_slug=plan_slug,
    )
    options = DegreePlanOptions()

    if academic_year is None:
        rows = session.scalars(select(AcademicYear).order_by(AcademicYear.year.desc())).all()
        options.academic_years = [AcademicYearOption(id=row.id, year=row.year) for row in rows]
        return DegreePlanLookupResponse(
            selected=selected,
            next_query_field="academic_year",
            options=options,
        )

    year_row = _get_academic_year(session, academic_year)

    if faculty_slug is None:
        rows = session.scalars(
            select(Faculty)
            .where(Faculty.academic_year_id == year_row.id)
            .order_by(Faculty.source_slug.asc())
        ).all()
        options.faculties = [_faculty_ref(row) for row in rows]
        return DegreePlanLookupResponse(
            selected=selected,
            next_query_field="faculty_slug",
            options=options,
        )

    faculty_row = _get_faculty(session, academic_year, faculty_slug)

    if department_slug is None:
        rows = session.scalars(
            select(Department)
            .where(Department.faculty_id == faculty_row.id)
            .order_by(Department.name_th.asc())
        ).all()
        options.departments = [_department_ref(row) for row in rows]
        return DegreePlanLookupResponse(
            selected=selected,
            next_query_field="department_slug",
            options=options,
        )

    department_row = _get_department(session, academic_year, faculty_slug, department_slug)

    if track_slug is None:
        rows = session.scalars(
            select(Track)
            .where(Track.department_id == department_row.id)
            .order_by(Track.name.asc())
        ).all()
        options.tracks = [_track_ref(row) for row in rows]
        return DegreePlanLookupResponse(
            selected=selected,
            next_query_field="track_slug",
            options=options,
        )

    track_row = _get_track(session, academic_year, faculty_slug, department_slug, track_slug)

    if plan_slug is None:
        rows = session.scalars(
            select(PlanType)
            .where(PlanType.track_id == track_row.id)
            .order_by(PlanType.name.asc())
        ).all()
        options.plans = [_plan_type_ref(row) for row in rows]
        return DegreePlanLookupResponse(
            selected=selected,
            next_query_field="plan_slug",
            options=options,
        )

    degree_plan = _build_degree_plan_result(
        session=session,
        academic_year=academic_year,
        faculty_slug=faculty_slug,
        department_slug=department_slug,
        track_slug=track_slug,
        plan_slug=plan_slug,
    )
    return DegreePlanLookupResponse(
        selected=selected,
        next_query_field=None,
        options=options,
        degree_plan=degree_plan,
    )
