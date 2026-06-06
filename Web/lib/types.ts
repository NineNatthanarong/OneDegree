import type { PrereqClause } from "./prereq";

export interface AcademicYearOption { id: number; year: string; }
export interface FacultyRef { id: number; slug: string; name_th: string; name_en?: string | null; }
export interface DepartmentRef { id: number; slug: string; name_th: string; name_en?: string | null; }
export interface TrackRef { id: number; slug: string; name: string; }
export interface PlanTypeRef { id: number; slug: string; name: string; }

export interface DegreePlanCourse {
  id: number;
  sequence: number;
  code?: string | null;
  name: string;
  credits?: number | null;
  prerequisite?: string | null;
}
export interface DegreePlanSemester {
  semester: number;
  total_credits: number;
  courses: DegreePlanCourse[];
}
export interface DegreePlanYear {
  year: number;
  total_credits: number;
  semesters: DegreePlanSemester[];
}
export interface DegreePlanCohort {
  cohort: { id: number; slug: string; name: string };
  total_credits: number;
  years: DegreePlanYear[];
}
export interface DegreePlan {
  academic_year: string;
  faculty: FacultyRef;
  department: DepartmentRef;
  track: TrackRef;
  plan: PlanTypeRef;
  cohort_count: number;
  cohorts: DegreePlanCohort[];
}

export interface DegreePlanQuery {
  academic_year: string | null;
  faculty_slug: string | null;
  department_slug: string | null;
  track_slug: string | null;
  plan_slug: string | null;
}
export interface DegreePlanOptions {
  academic_years: AcademicYearOption[];
  faculties: FacultyRef[];
  departments: DepartmentRef[];
  tracks: TrackRef[];
  plans: PlanTypeRef[];
}
export interface DegreePlanLookupResponse {
  selected: DegreePlanQuery;
  next_query_field: keyof DegreePlanQuery | null | "done";
  options: DegreePlanOptions;
  degree_plan: DegreePlan | null;
}

/* ---- in-app, derived ---- */

export interface CourseNode {
  id: string;
  code: string;
  codeNorm: string;
  name: string;
  credits: number | null;
  rawPre: string;
  preClauses: PrereqClause[];     // structured (AND of OR-groups)
  preCodes: string[];             // flat list, kept for legacy + tooltip
  yearIdx: number;
  semIdx: number;
  year: number;
  semester: number;
  curYearIdx?: number;
  curSemIdx?: number;
}

export interface PrereqEdge {
  from: CourseNode;
  to: CourseNode;
  kind: "pass" | "concurrent";    // pass: must be earlier · concurrent: same-or-earlier
  clauseIdx: number;              // which clause of `to.preClauses`
  altCount: number;               // total alternatives in that clause
}
