// Timetable Planner — data model, parsing, grouping, conflict detection.
// Data is static JSON under /data (emitted to Web/public/data, served same-origin).

export type Day = "Mon" | "Tue" | "Wed" | "Thu" | "Fri" | "Sat";
export const DAYS: Day[] = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
export const DAY_TH: Record<Day, string> = {
  Mon: "จันทร์",
  Tue: "อังคาร",
  Wed: "พุธ",
  Thu: "พฤหัส",
  Fri: "ศุกร์",
  Sat: "เสาร์"
};

export interface TermInfo {
  year: string;
  semester: string;
  label: string;
  file: string;
  count: number;
}

/** Faculty groups as emitted by Server/tools/scrape_timetable.py. */
export const GROUP_TH: Record<string, string> = {
  engineering: "วิศวกรรมศาสตร์",
  technology: "ไอทีและนวัตกรรม",
  business: "บริหารธุรกิจ · บัญชี · เศรษฐศาสตร์",
  communication_arts: "นิเทศศาสตร์",
  digital_media: "ดิจิทัลมีเดียและภาพยนตร์",
  architecture: "สถาปัตยกรรมศาสตร์",
  law: "นิติศาสตร์",
  hospitality: "การท่องเที่ยวและการโรงแรม",
  international: "หลักสูตรนานาชาติ (BUIC)",
  liberal_arts: "ศิลปศาสตร์ · ศิลปกรรม",
  health: "วิทยาศาสตร์สุขภาพ",
  service: "วิชาพื้นฐาน (GE / EN / MA …)"
};
export const GROUP_ORDER = Object.keys(GROUP_TH);
export function groupLabel(g: string): string {
  return GROUP_TH[g] ?? g;
}

interface RawSection {
  prefix: string;
  group: string; // faculty group key, see GROUP_TH
  course: string;
  course_name: string;
  section: string;
  status: string; // On | Freeze | Close
  type: string; // LECT | LAB | PRAC | RWS | R/W/C
  day: string;
  time: string; // "8:40-11:00"
  room: string | null;
  credits: number | null;
}

export interface Meeting {
  day: Day;
  start: number; // minutes from 00:00
  end: number;
  time: string;
  room: string | null;
  type: string;
}

export interface Section {
  id: string; // `${course}-${section}`
  course: string;
  courseName: string;
  prefix: string;
  group: string;
  section: string;
  credits: number | null;
  meetings: Meeting[];
}

/** Tidy a room code: "RB4409" → "B4-409" (drop leading R, dash before last 3). */
export function fmtRoom(room: string | null): string {
  if (!room) return "—";
  let s = room.trim();
  if (!s || /^(TBA|ONLINE|-)$/i.test(s)) return s || "—";
  s = s.replace(/^R(?=[A-Za-z]\d)/, ""); // drop the leading "R" room prefix
  if (s.length > 3 && /\d{3}$/.test(s)) return s.slice(0, -3) + "-" + s.slice(-3);
  return s;
}

export interface Course {
  code: string;
  name: string;
  prefix: string;
  group: string;
  credits: number | null;
  sections: Section[];
}

function toMinutes(hhmm: string): number {
  const [h, m] = hhmm.split(":").map(Number);
  return h * 60 + (m || 0);
}
export function fmtMinutes(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${h}:${String(m).padStart(2, "0")}`;
}
function parseTime(t: string): { start: number; end: number } | null {
  const m = t.match(/^(\d{1,2}:\d{2})-(\d{1,2}:\d{2})$/);
  if (!m) return null;
  return { start: toMinutes(m[1]), end: toMinutes(m[2]) };
}

const DAY_SET = new Set(DAYS);

/** Group raw meeting rows into Course → Section[] (sections bundle their meetings). */
export function groupCourses(rows: RawSection[]): Course[] {
  const courseMap = new Map<string, Course>();
  const sectionMap = new Map<string, Section>();

  for (const r of rows) {
    if (!courseMap.has(r.course)) {
      courseMap.set(r.course, {
        code: r.course,
        name: r.course_name,
        prefix: r.prefix,
        group: r.group,
        credits: r.credits,
        sections: []
      });
    }
    const course = courseMap.get(r.course)!;

    const sid = `${r.course}-${r.section}`;
    let section = sectionMap.get(sid);
    if (!section) {
      section = {
        id: sid,
        course: r.course,
        courseName: r.course_name,
        prefix: r.prefix,
        group: r.group,
        section: r.section,
        credits: r.credits,
        meetings: []
      };
      sectionMap.set(sid, section);
      course.sections.push(section);
    }
    const t = parseTime(r.time);
    if (t && DAY_SET.has(r.day as Day)) {
      section.meetings.push({
        day: r.day as Day,
        start: t.start,
        end: t.end,
        time: r.time,
        room: r.room,
        type: r.type
      });
    }
  }

  const courses = [...courseMap.values()];
  courses.sort((a, b) => a.code.localeCompare(b.code));
  for (const c of courses)
    c.sections.sort((a, b) => a.section.localeCompare(b.section));
  return courses;
}

function meetingsOverlap(a: Meeting, b: Meeting): boolean {
  return a.day === b.day && a.start < b.end && b.start < a.end;
}

/** Two sections conflict if any of their meetings overlap. */
export function sectionsConflict(a: Section, b: Section): boolean {
  for (const m of a.meetings) for (const n of b.meetings) if (meetingsOverlap(m, n)) return true;
  return false;
}

/** Returns the set of chosen section ids that clash with at least one other. */
export function conflictingIds(chosen: Section[]): Set<string> {
  const bad = new Set<string>();
  for (let i = 0; i < chosen.length; i++)
    for (let j = i + 1; j < chosen.length; j++)
      if (sectionsConflict(chosen[i], chosen[j])) {
        bad.add(chosen[i].id);
        bad.add(chosen[j].id);
      }
  return bad;
}

export async function fetchTerms(): Promise<TermInfo[]> {
  const res = await fetch("/data/terms.json");
  if (!res.ok) throw new Error("terms " + res.status);
  return (await res.json()).terms as TermInfo[];
}

export async function fetchTermCourses(file: string): Promise<Course[]> {
  const res = await fetch("/data/" + file);
  if (!res.ok) throw new Error("term " + res.status);
  const data = await res.json();
  return groupCourses(data.sections as RawSection[]);
}

/* ---------------- degree-plan auto-fill (all faculties) ---------------- */

// Engineering majors share the four-dept course-list filter (one major hides the
// others). Other faculties don't pre-filter by code prefix.
export const MAJOR_PREFIXES = new Set(["EE", "CE", "MI", "AIE"]);

export interface FacultyMeta { key: string; group: string; nameTh: string; }
export interface PlanProgram {
  acadyr: string;
  faculty: string;     // school-of-* slug
  group: string;       // timetable faculty group (engineering/business/…)
  facultyName: string; // Thai faculty name
  dept: string;        // cleaned Thai dept name — the dept id within acadyr+faculty
  deptName: string;
  track: string;
  trackName: string;
  plan: string;
  cohort: string;
  years: Record<string, Record<string, string[]>>; // yearLevel -> semester -> [codes]
}
export interface AllPlans { meta: { faculties: FacultyMeta[]; acadyrs: string[] }; programs: PlanProgram[]; }
// kept name for back-compat with existing imports
export type EngPlans = AllPlans;

export function normCode(c: string): string {
  return (c || "").replace(/\s+/g, "").toUpperCase();
}

export async function fetchPlans(): Promise<AllPlans> {
  const res = await fetch("/data/all-plans.json");
  if (!res.ok) throw new Error("plans " + res.status);
  return res.json();
}

/** A program variant key (track · plan · cohort) — unique within acadyr+faculty+dept. */
export function variantKey(p: PlanProgram): string {
  return `${p.track}|${p.plan}|${p.cohort}`;
}
export function variantLabel(p: PlanProgram): string {
  const t = p.track === "default" ? "" : p.trackName + " · ";
  return `${t}${p.plan} · ${p.cohort}`;
}

export interface MatchResult {
  chosenIds: string[];
  missing: string[]; // code not offered this term
}

/** Map plan target course codes → a section id each in the current term.
 *  Greedy + conflict-aware: prefer a section that doesn't clash with the ones
 *  already picked, so auto-fill lands a mostly-clean timetable. */
export function matchTargets(codes: string[], courses: Course[]): MatchResult {
  const byCode = new Map(courses.map((c) => [normCode(c.code), c]));
  const chosenIds: string[] = [];
  const picked: Section[] = [];
  const missing: string[] = [];
  for (const code of codes) {
    const c = byCode.get(normCode(code));
    if (!c) { missing.push(code); continue; }
    const pool = c.sections.filter((s) => s.meetings.length > 0);
    if (!pool.length) { missing.push(code); continue; }
    const pick = pool.find((s) => !picked.some((p) => sectionsConflict(s, p))) || pool[0];
    chosenIds.push(pick.id);
    picked.push(pick);
  }
  return { chosenIds, missing };
}

/** Sections of a course that actually have a meeting time. */
export function timedSections(c: Course): Section[] {
  return c.sections.filter((s) => s.meetings.length > 0);
}

/** A course can be drag-picked on the grid only if its sections are few enough
 *  AND don't overlap each other (overlapping footprints can't be distinguished
 *  by a drop). Otherwise the UI shows a chooser card instead. */
export function dragEligible(c: Course): boolean {
  const list = timedSections(c);
  if (list.length === 0 || list.length > 8) return false;
  for (let i = 0; i < list.length; i++)
    for (let j = i + 1; j < list.length; j++)
      if (sectionsConflict(list[i], list[j])) return false;
  return true;
}

/** Deterministic pleasant color per course code (HSL), for grid blocks. */
export function courseColor(code: string): string {
  let h = 0;
  for (let i = 0; i < code.length; i++) h = (h * 31 + code.charCodeAt(i)) % 360;
  return `hsl(${h} 55% 42%)`;
}
