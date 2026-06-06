from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ImportState(Base):
    __tablename__ = "import_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    dataset_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    source_generated_at: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_seeded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), default=func.now()
    )


class AcademicYear(Base):
    __tablename__ = "academic_years"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    year: Mapped[str] = mapped_column(String(16), unique=True, index=True, nullable=False)

    faculties: Mapped[list["Faculty"]] = relationship(
        back_populates="academic_year", cascade="all, delete-orphan"
    )


class Faculty(Base):
    __tablename__ = "faculties"
    __table_args__ = (UniqueConstraint("academic_year_id", "source_slug", name="uq_faculty_year_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_years.id", ondelete="CASCADE"), index=True)
    source_slug: Mapped[str] = mapped_column(String(255), nullable=False)
    name_th: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    academic_year: Mapped["AcademicYear"] = relationship(back_populates="faculties")
    departments: Mapped[list["Department"]] = relationship(
        back_populates="faculty", cascade="all, delete-orphan"
    )


class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("faculty_id", "slug", name="uq_department_faculty_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculties.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    name_th: Mapped[str] = mapped_column(String(255), nullable=False)
    name_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    faculty: Mapped["Faculty"] = relationship(back_populates="departments")
    tracks: Mapped[list["Track"]] = relationship(back_populates="department", cascade="all, delete-orphan")


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (UniqueConstraint("department_id", "slug", name="uq_track_department_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    department: Mapped["Department"] = relationship(back_populates="tracks")
    plan_types: Mapped[list["PlanType"]] = relationship(back_populates="track", cascade="all, delete-orphan")
    course_catalog_entries: Mapped[list["CourseCatalogEntry"]] = relationship(
        back_populates="track", cascade="all, delete-orphan"
    )


class PlanType(Base):
    __tablename__ = "plan_types"
    __table_args__ = (UniqueConstraint("track_id", "slug", name="uq_plan_type_track_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    track: Mapped["Track"] = relationship(back_populates="plan_types")
    cohorts: Mapped[list["Cohort"]] = relationship(back_populates="plan_type", cascade="all, delete-orphan")


class Cohort(Base):
    __tablename__ = "cohorts"
    __table_args__ = (UniqueConstraint("plan_type_id", "slug", name="uq_cohort_plan_slug"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_type_id: Mapped[int] = mapped_column(ForeignKey("plan_types.id", ondelete="CASCADE"), index=True)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    plan_type: Mapped["PlanType"] = relationship(back_populates="cohorts")
    semester_courses: Mapped[list["SemesterCourse"]] = relationship(
        back_populates="cohort", cascade="all, delete-orphan"
    )


class CourseCatalogEntry(Base):
    __tablename__ = "course_catalog_entries"
    __table_args__ = (
        UniqueConstraint("track_id", "code", name="uq_course_catalog_track_code"),
        Index("ix_course_catalog_entries_code", "code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    track_id: Mapped[int] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    credits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prerequisite: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    track: Mapped["Track"] = relationship(back_populates="course_catalog_entries")
    scheduled_occurrences: Mapped[list["SemesterCourse"]] = relationship(back_populates="course_catalog_entry")


class SemesterCourse(Base):
    __tablename__ = "semester_courses"
    __table_args__ = (
        Index("ix_semester_courses_course_code", "course_code"),
        Index("ix_semester_courses_curriculum_slot", "cohort_id", "year_level", "semester", "position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cohort_id: Mapped[int] = mapped_column(ForeignKey("cohorts.id", ondelete="CASCADE"), index=True)
    course_catalog_entry_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("course_catalog_entries.id", ondelete="SET NULL"), nullable=True, index=True
    )
    year_level: Mapped[int] = mapped_column(Integer, nullable=False)
    semester: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    course_code: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    course_name: Mapped[str] = mapped_column(Text, nullable=False)
    credits: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    prerequisite: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    cohort: Mapped["Cohort"] = relationship(back_populates="semester_courses")
    course_catalog_entry: Mapped[Optional["CourseCatalogEntry"]] = relationship(back_populates="scheduled_occurrences")
