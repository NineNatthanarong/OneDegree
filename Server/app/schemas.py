from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class AcademicYearOption(BaseModel):
    id: int
    year: str


class FacultyRef(BaseModel):
    id: int
    slug: str
    name_th: str
    name_en: Optional[str] = None


class DepartmentRef(BaseModel):
    id: int
    slug: str
    name_th: str
    name_en: Optional[str] = None


class TrackRef(BaseModel):
    id: int
    slug: str
    name: str


class PlanTypeRef(BaseModel):
    id: int
    slug: str
    name: str


class CohortRef(BaseModel):
    id: int
    slug: str
    name: str


class DegreePlanCourse(BaseModel):
    id: int
    sequence: int
    code: Optional[str] = None
    name: str
    credits: Optional[int] = None
    prerequisite: Optional[str] = None


class DegreePlanSemester(BaseModel):
    semester: int
    total_credits: int
    courses: list[DegreePlanCourse]


class DegreePlanYear(BaseModel):
    year: int
    total_credits: int
    semesters: list[DegreePlanSemester]


class DegreePlanCohort(BaseModel):
    cohort: CohortRef
    total_credits: int
    years: list[DegreePlanYear]


class DegreePlanResponse(BaseModel):
    academic_year: str
    faculty: FacultyRef
    department: DepartmentRef
    track: TrackRef
    plan: PlanTypeRef
    cohort_count: int
    cohorts: list[DegreePlanCohort]


class DegreePlanQuery(BaseModel):
    academic_year: Optional[str] = None
    faculty_slug: Optional[str] = None
    department_slug: Optional[str] = None
    track_slug: Optional[str] = None
    plan_slug: Optional[str] = None


class DegreePlanOptions(BaseModel):
    academic_years: list[AcademicYearOption] = Field(default_factory=list)
    faculties: list[FacultyRef] = Field(default_factory=list)
    departments: list[DepartmentRef] = Field(default_factory=list)
    tracks: list[TrackRef] = Field(default_factory=list)
    plans: list[PlanTypeRef] = Field(default_factory=list)


class DegreePlanLookupResponse(BaseModel):
    selected: DegreePlanQuery
    next_query_field: Optional[str] = None
    options: DegreePlanOptions
    degree_plan: Optional[DegreePlanResponse] = None


class SourceMetadata(BaseModel):
    generated_at: Optional[str] = None
    academic_years: list[str]
    faculty_count: Optional[int] = None


class DatabaseCounts(BaseModel):
    academic_years: int
    faculties: int
    departments: int
    tracks: int
    plan_types: int
    cohorts: int
    course_catalog_entries: int
    semester_courses: int


class MetadataResponse(BaseModel):
    source: SourceMetadata
    database_counts: DatabaseCounts


class HealthResponse(BaseModel):
    status: str
