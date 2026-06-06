"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  DAYS,
  DAY_TH,
  fmtMinutes,
  fmtRoom,
  fetchTerms,
  fetchTermCourses,
  fetchPlans,
  conflictingIds,
  sectionsConflict,
  courseColor,
  matchTargets,
  dragEligible,
  timedSections,
  variantKey,
  variantLabel,
  MAJOR_PREFIXES,
  type Course,
  type Section,
  type TermInfo,
  type EngPlans,
  type PlanProgram,
  type Day
} from "@/lib/timetable";

const GRID_START = 8 * 60;
const GRID_END = 21 * 60;
const HOUR_H = 56;

interface PlanSel {
  acadyr: string;
  dept: string;
  variant: string;
  studyYear: string;
  sem: string;
}

export default function TimetablePage() {
  const [terms, setTerms] = useState<TermInfo[]>([]);
  const [termIdx, setTermIdx] = useState(0);
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);

  const [plans, setPlans] = useState<EngPlans | null>(null);
  const [sel, setSel] = useState<PlanSel | null>(null);
  const [autoMsg, setAutoMsg] = useState("");

  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const [query, setQuery] = useState("");
  const [hovered, setHovered] = useState<Section | null>(null);
  const [dragCourse, setDragCourse] = useState<Course | null>(null);
  const [chooser, setChooser] = useState<Course | null>(null);
  const [toast, setToast] = useState("");

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 2800);
    return () => clearTimeout(t);
  }, [toast]);

  const term = terms[termIdx];
  const termKey = term ? `tt-chosen-${term.year}-${term.semester}` : "";

  useEffect(() => {
    fetchTerms().then(setTerms).catch(() => setTerms([]));
    fetchPlans().then(setPlans).catch(() => setPlans(null));
  }, []);

  useEffect(() => {
    if (!term) return;
    setLoading(true);
    fetchTermCourses(term.file)
      .then((c) => {
        setCourses(c);
        try {
          setChosen(new Set(JSON.parse(localStorage.getItem(termKey) || "[]")));
        } catch {
          setChosen(new Set());
        }
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [termIdx, term?.file]);

  useEffect(() => {
    if (term) localStorage.setItem(termKey, JSON.stringify([...chosen]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chosen, termKey]);

  const variantsOf = (acadyr: string, dept: string) => {
    if (!plans) return [] as { key: string; label: string; program: PlanProgram }[];
    const seen = new Set<string>();
    const out: { key: string; label: string; program: PlanProgram }[] = [];
    for (const p of plans.programs) {
      if (p.acadyr !== acadyr || p.dept !== dept) continue;
      const k = variantKey(p);
      if (seen.has(k)) continue;
      seen.add(k);
      out.push({ key: k, label: variantLabel(p), program: p });
    }
    return out;
  };
  const programOf = (s: PlanSel | null): PlanProgram | null => {
    if (!plans || !s) return null;
    return plans.programs.find(
      (p) => p.acadyr === s.acadyr && p.dept === s.dept && variantKey(p) === s.variant
    ) || null;
  };

  useEffect(() => {
    if (!plans || !term || sel) return;
    const acadyr = plans.programs.some((p) => p.acadyr === term.year)
      ? term.year
      : [...new Set(plans.programs.map((p) => p.acadyr))].sort().reverse()[0];
    const dept = plans.departments[0]?.prefix ?? "EE";
    const vs = variantsOf(acadyr, dept);
    const program = vs[0]?.program;
    const studyYear = program ? Object.keys(program.years).sort((a, b) => +a - +b)[0] : "1";
    const semOpts = program ? Object.keys(program.years[studyYear] || {}) : ["1"];
    const semv = semOpts.includes(term.semester) ? term.semester : semOpts[0];
    setSel({ acadyr, dept, variant: vs[0]?.key ?? "", studyYear, sem: semv });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plans, term]);

  const program = programOf(sel);
  const studyYears = program ? Object.keys(program.years).sort((a, b) => +a - +b) : [];
  const sems = program && sel ? Object.keys(program.years[sel.studyYear] || {}).sort() : [];

  function patchSel(patch: Partial<PlanSel>) {
    setSel((prev) => {
      if (!prev) return prev;
      const next = { ...prev, ...patch };
      if (patch.acadyr || patch.dept) {
        next.variant = variantsOf(next.acadyr, next.dept)[0]?.key ?? "";
      }
      if (patch.acadyr || patch.dept || patch.variant) {
        const prog = plans?.programs.find(
          (p) => p.acadyr === next.acadyr && p.dept === next.dept && variantKey(p) === next.variant
        );
        const ys = prog ? Object.keys(prog.years).sort((a, b) => +a - +b) : [];
        next.studyYear = ys.includes(next.studyYear) ? next.studyYear : ys[0] ?? "1";
        const ss = prog ? Object.keys(prog.years[next.studyYear] || {}) : [];
        next.sem = ss.includes(next.sem) ? next.sem : ss[0] ?? "1";
      }
      if (patch.studyYear) {
        const prog = programOf(next);
        const ss = prog ? Object.keys(prog.years[next.studyYear] || {}) : [];
        next.sem = ss.includes(next.sem) ? next.sem : ss[0] ?? "1";
      }
      return next;
    });
  }

  const byId = useMemo(() => {
    const m = new Map<string, Section>();
    for (const c of courses) for (const s of c.sections) m.set(s.id, s);
    return m;
  }, [courses]);
  const courseByCode = useMemo(() => {
    const m = new Map<string, Course>();
    for (const c of courses) m.set(c.code, c);
    return m;
  }, [courses]);
  const chosenSections = useMemo(
    () => [...chosen].map((id) => byId.get(id)).filter(Boolean) as Section[],
    [chosen, byId]
  );
  const conflicts = useMemo(() => conflictingIds(chosenSections), [chosenSections]);
  const totalCredits = useMemo(() => {
    const seen = new Map<string, number>();
    for (const s of chosenSections) if (s.credits != null) seen.set(s.course, s.credits);
    return [...seen.values()].reduce((a, b) => a + b, 0);
  }, [chosenSections]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const dept = sel?.dept;
    return courses.filter((c) => {
      if (dept && MAJOR_PREFIXES.has(c.prefix) && c.prefix !== dept) return false;
      if (!q) return true;
      return (
        c.code.toLowerCase().includes(q) ||
        c.name.toLowerCase().includes(q) ||
        c.prefix.toLowerCase().includes(q)
      );
    });
  }, [courses, query, sel?.dept]);

  // chosen courses float to the top so the timetable's subjects are easy to find
  const isChosenCourse = (c: Course) => c.sections.some((s) => chosen.has(s.id));
  const chosenCourses = useMemo(() => filtered.filter(isChosenCourse), [filtered, chosen]);
  const restCourses = useMemo(() => filtered.filter((c) => !isChosenCourse(c)), [filtered, chosen]);

  function pickSection(s: Section) {
    setAutoMsg("");
    setChosen((prev) => {
      const next = new Set(prev);
      if (next.has(s.id)) next.delete(s.id);
      else {
        for (const id of next) {
          const o = byId.get(id);
          if (o && o.course === s.course) next.delete(id);
        }
        next.add(s.id);
      }
      return next;
    });
  }
  // select-only (drag drops + chooser): add s, swap out same course, never toggle off
  function selectSection(s: Section) {
    setAutoMsg("");
    setChosen((prev) => {
      const next = new Set(prev);
      for (const id of next) {
        const o = byId.get(id);
        if (o && o.course === s.course) next.delete(id);
      }
      next.add(s.id);
      return next;
    });
  }
  function removeCourse(code: string) {
    setChosen((prev) => {
      const next = new Set(prev);
      for (const id of next) { const o = byId.get(id); if (o && o.course === code) next.delete(id); }
      return next;
    });
  }

  function autoFill() {
    if (!program || !sel) return;
    const codes = program.years[sel.studyYear]?.[sel.sem] || [];
    const res = matchTargets(codes, courses);
    setChosen(new Set(res.chosenIds));
    const parts = [`เติม ${res.chosenIds.length} วิชา`];
    if (res.missing.length) parts.push(`ไม่เปิดเทอมนี้ ${res.missing.length} (${res.missing.join(", ")})`);
    setAutoMsg(parts.join(" · "));
  }

  const deptName = plans?.departments.find((d) => d.prefix === sel?.dept)?.name ?? "";

  return (
    <div className={"tt-shell" + (dragCourse ? " tt-dragging" : "")}>
      <header className="topbar tt-topbar">
        <div className="brand">
          <div className="brand-mark">
            <svg viewBox="0 0 24 24" width={20} height={20} aria-hidden="true">
              <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="1.4" />
              <path d="M5 17 Q 12 3 19 17" fill="none" stroke="currentColor" strokeWidth="1.4" />
              <circle cx="5" cy="17" r="1.4" fill="currentColor" />
              <circle cx="19" cy="17" r="1.4" fill="currentColor" />
              <circle cx="12" cy="6.5" r="1.4" fill="currentColor" />
            </svg>
          </div>
          <div>
            <div className="brand-name">One<span className="deg">Degree</span></div>
            <div className="brand-tag">จัดตารางเรียน</div>
          </div>
          <nav className="mode-switch">
            <Link className="mode-pill" href="/">แผนที่หลักสูตร</Link>
            <span className="mode-pill active">จัดตารางเรียน</span>
          </nav>
        </div>
        <div />
        <div className="tt-term">
          <select value={termIdx} onChange={(e) => setTermIdx(Number(e.target.value))} aria-label="เลือกเทอม">
            {terms.map((t, i) => (<option key={t.file} value={i}>{t.label}</option>))}
          </select>
        </div>
      </header>

      <div className="tt-body">
        <aside className="tt-picker">
          <div className="tt-plan">
            <div className="tt-plan-title">เติมวิชาตามแผนการเรียน</div>
            {sel && plans ? (
              <>
                <div className="tt-plan-grid">
                  <label>
                    <span>หลักสูตรปี</span>
                    <select value={sel.acadyr} onChange={(e) => patchSel({ acadyr: e.target.value })}>
                      {[...new Set(plans.programs.map((p) => p.acadyr))].sort().reverse().map((y) => (
                        <option key={y} value={y}>{y}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>ภาควิชา</span>
                    <select value={sel.dept} onChange={(e) => patchSel({ dept: e.target.value })}>
                      {plans.departments.map((d) => (
                        <option key={d.prefix} value={d.prefix}>{d.prefix} · {shortDept(d.name)}</option>
                      ))}
                    </select>
                  </label>
                  <label className="wide">
                    <span>รูปแบบ</span>
                    <select value={sel.variant} onChange={(e) => patchSel({ variant: e.target.value })}>
                      {variantsOf(sel.acadyr, sel.dept).map((v) => (
                        <option key={v.key} value={v.key}>{v.label}</option>
                      ))}
                    </select>
                  </label>
                  <label>
                    <span>ชั้นปี</span>
                    <select value={sel.studyYear} onChange={(e) => patchSel({ studyYear: e.target.value })}>
                      {studyYears.map((y) => (<option key={y} value={y}>ปี {y}</option>))}
                    </select>
                  </label>
                  <label>
                    <span>ภาคเรียน</span>
                    <select value={sel.sem} onChange={(e) => patchSel({ sem: e.target.value })}>
                      {sems.map((s) => (<option key={s} value={s}>เทอม {s}</option>))}
                    </select>
                  </label>
                </div>
                <button className="tt-autofill" onClick={autoFill} disabled={!program}>⤓ เติมตารางอัตโนมัติ</button>
                {autoMsg && <div className="tt-plan-msg">{autoMsg}</div>}
              </>
            ) : (
              <div className="tt-empty">กำลังโหลดแผน…</div>
            )}
          </div>

          <div className="tt-picker-head">
            <input
              className="tt-search"
              placeholder={`ค้นหาวิชาใน ${deptName ? shortDept(deptName) + " + วิชาทั่วไป" : "รายการ"}…`}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="tt-hint-line">ลากวิชาไปวางบนตาราง · หรือกดเพื่อเลือก</div>
          </div>
          <div className="tt-course-list">
            {loading ? (
              <div className="tt-empty">กำลังโหลด…</div>
            ) : filtered.length === 0 ? (
              <div className="tt-empty">ไม่พบวิชา</div>
            ) : (
              <>
                {chosenCourses.length > 0 && (
                  <div className="tt-list-label">📌 วิชาในตาราง ({chosenCourses.length})</div>
                )}
                {chosenCourses.map((c) => (
                  <CourseItem key={c.code} course={c} chosen={chosen} conflicts={conflicts}
                    onToggle={pickSection} onHover={setHovered} onDragCourse={setDragCourse} onChooser={setChooser} onToast={setToast} />
                ))}
                {chosenCourses.length > 0 && restCourses.length > 0 && (
                  <div className="tt-list-label muted">วิชาทั้งหมด</div>
                )}
                {restCourses.map((c) => (
                  <CourseItem key={c.code} course={c} chosen={chosen} conflicts={conflicts}
                    onToggle={pickSection} onHover={setHovered} onDragCourse={setDragCourse} onChooser={setChooser} onToast={setToast} />
                ))}
              </>
            )}
          </div>
        </aside>

        <main className="tt-grid-wrap">
          <WeekGrid
            sections={chosenSections}
            conflicts={conflicts}
            ghost={hovered}
            dragCourse={dragCourse}
            onSelect={selectSection}
            onDragCourse={setDragCourse}
            onChooser={setChooser}
            onToast={setToast}
            courseByCode={courseByCode}
          />
        </main>
      </div>

      <footer className="tt-summary">
        <div className="tt-sum-item"><strong>{new Set(chosenSections.map((s) => s.course)).size}</strong> วิชา</div>
        <div className="tt-sum-item"><strong>{totalCredits}</strong> หน่วยกิต</div>
        <div className={"tt-sum-item" + (conflicts.size ? " bad" : " ok")}>
          {conflicts.size ? <><strong>{conflicts.size / 2}</strong> จุดที่ชนกัน</> : "ไม่มีวิชาชนกัน ✓"}
        </div>
        {chosenSections.length > 0 && (
          <button className="tt-clear" onClick={() => { setChosen(new Set()); setAutoMsg(""); }}>ล้างตาราง</button>
        )}
      </footer>

      {chooser && (
        <ChooserCard
          course={chooser}
          chosen={chosen}
          onPick={(s) => { selectSection(s); setChooser(null); }}
          onRemove={() => { removeCourse(chooser.code); setChooser(null); }}
          onClose={() => setChooser(null)}
        />
      )}

      {toast && <div className="tt-toast" role="status">{toast}</div>}
    </div>
  );
}

function shortDept(name: string): string {
  return name.replace(/^สาขาวิชา|^สาขา/, "");
}

/** Why a course can't be dragged → a short Thai toast telling the user to pick a section. */
function dragBlockMsg(course: Course): string {
  const n = timedSections(course).length;
  if (n > 8) return `${course.code} มี ${n} เซคชัน เยอะเกินกว่าจะลาก · กดเพื่อเลือกเซคชัน`;
  return `${course.code} มีเซคชันเวลาทับกัน ลากไม่ได้ · กดเพื่อเลือกเซคชัน`;
}

/* ============== course list item ============== */
function CourseItem({
  course, chosen, conflicts, onToggle, onHover, onDragCourse, onChooser, onToast
}: {
  course: Course; chosen: Set<string>; conflicts: Set<string>;
  onToggle: (s: Section) => void; onHover: (s: Section | null) => void;
  onDragCourse: (c: Course | null) => void; onChooser: (c: Course) => void;
  onToast: (m: string) => void;
}) {
  const anyChosen = course.sections.some((s) => chosen.has(s.id));
  const [open, setOpen] = useState(false);
  const expanded = open || anyChosen;
  const eligible = dragEligible(course);

  return (
    <div className={"tt-course" + (anyChosen ? " has-chosen" : "")}>
      <button
        className="tt-course-head"
        onClick={() => (eligible ? setOpen((o) => !o) : onChooser(course))}
        draggable
        onDragStart={(e) => {
          if (eligible) {
            onDragCourse(course);
            e.dataTransfer.effectAllowed = "copy";
            e.dataTransfer.setData("text/plain", course.code);
          } else {
            e.preventDefault();
            onToast(dragBlockMsg(course));
            onChooser(course);
          }
        }}
        onDragEnd={() => onDragCourse(null)}
        title={eligible ? "ลากไปวางบนตาราง" : "หลายเซคชัน ลากไม่ได้ · กดเพื่อเลือก"}
      >
        {eligible
          ? <span className="tt-drag-grip" aria-hidden="true">⠿</span>
          : <span className="tt-many" aria-hidden="true" title="หลายเซคชัน">▦</span>}
        <span className="tt-course-code">{course.code}</span>
        <span className="tt-course-name">{course.name}</span>
        <span className="tt-course-meta">
          {course.credits != null ? `${course.credits} นก.` : "—"}
          {eligible ? <span className="tt-course-arrow">{expanded ? "▾" : "▸"}</span> : <span className="tt-course-arrow">⤢</span>}
        </span>
      </button>
      {eligible && expanded && (
        <div className="tt-sections">
          {course.sections.map((s) => {
            const isChosen = chosen.has(s.id);
            const bad = conflicts.has(s.id);
            const cls = ["tt-section", isChosen ? "chosen" : "", bad ? "conflict" : ""].filter(Boolean).join(" ");
            return (
              <button
                key={s.id} className={cls} onClick={() => onToggle(s)}
                onMouseEnter={() => onHover(s)} onMouseLeave={() => onHover(null)}
                style={isChosen ? { ["--c" as never]: courseColor(s.course) } : undefined}
              >
                <span className="tt-sec-id">{s.section}</span>
                <span className="tt-sec-meet">
                  {s.meetings.length === 0 ? <em>ไม่มีเวลาเรียน</em> : s.meetings.map((m, i) => (
                    <span key={i} className="tt-sec-slot">
                      {DAY_TH[m.day]} {m.time} <span className="tt-sec-room">{fmtRoom(m.room)}</span> · {m.type}
                    </span>
                  ))}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ============== section chooser card (for many/overlapping sections) ============== */
function ChooserCard({
  course, chosen, onPick, onRemove, onClose
}: {
  course: Course; chosen: Set<string>;
  onPick: (s: Section) => void; onRemove: () => void; onClose: () => void;
}) {
  const [q, setQ] = useState("");
  useEffect(() => {
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [onClose]);
  const all = course.sections.filter((s) => s.meetings.length > 0);
  const ql = q.trim().toLowerCase();
  const qth = q.trim();
  const list = ql
    ? all.filter((s) =>
        s.section.toLowerCase().includes(ql) ||
        s.meetings.some((m) =>
          m.time.includes(ql) ||
          DAY_TH[m.day].includes(qth) ||
          m.type.toLowerCase().includes(ql) ||
          (m.room || "").toLowerCase().includes(ql) ||
          fmtRoom(m.room).toLowerCase().includes(ql)
        ))
    : all;
  const anyChosen = course.sections.some((s) => chosen.has(s.id));
  return (
    <div className="tt-chooser-overlay" onMouseDown={onClose}>
      <div className="tt-chooser-card" onMouseDown={(e) => e.stopPropagation()}>
        <button className="picker-close" onClick={onClose} aria-label="ปิด">✕</button>
        <div className="tt-chooser-head">
          <div className="tt-chooser-code">{course.code} <span className="tt-chooser-cr">{course.credits != null ? `${course.credits} นก.` : ""}</span></div>
          <div className="tt-chooser-name">{course.name}</div>
          <div className="tt-chooser-sub">เลือกเซคชัน · {ql ? `${list.length}/${all.length}` : all.length} เซคชัน</div>
        </div>
        {all.length > 6 && (
          <div className="tt-chooser-search-wrap">
            <input
              className="tt-chooser-search"
              placeholder="ค้นหาเซคชัน / เวลา / วัน / ห้อง…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              autoFocus
            />
          </div>
        )}
        <div className="tt-chooser-list">
          {list.length === 0 && <div className="tt-chooser-empty">ไม่พบเซคชันที่ค้นหา</div>}
          {list.map((s) => {
            const isChosen = chosen.has(s.id);
            return (
              <button key={s.id} className={"tt-chooser-sec" + (isChosen ? " chosen" : "")}
                onClick={() => onPick(s)} style={{ ["--c" as never]: courseColor(s.course) }}>
                <span className="tt-chooser-secid">{s.section}{isChosen && <span className="tt-chooser-tick">✓</span>}</span>
                <span className="tt-chooser-meet">
                  {s.meetings.map((m, i) => (
                    <span key={i} className="tt-sec-slot">
                      {DAY_TH[m.day]} {m.time} <span className="tt-sec-room">{fmtRoom(m.room)}</span> · {m.type}
                    </span>
                  ))}
                </span>
              </button>
            );
          })}
        </div>
        {anyChosen && (
          <button className="tt-chooser-remove" onClick={onRemove}>เอาออกจากตาราง</button>
        )}
      </div>
    </div>
  );
}

/* ============== weekly grid ============== */
function WeekGrid({
  sections, conflicts, ghost, dragCourse, onSelect, onDragCourse, onChooser, onToast, courseByCode
}: {
  sections: Section[]; conflicts: Set<string>; ghost: Section | null;
  dragCourse: Course | null; onSelect: (s: Section) => void;
  onDragCourse: (c: Course | null) => void; onChooser: (c: Course) => void;
  onToast: (m: string) => void;
  courseByCode: Map<string, Course>;
}) {
  const totalH = ((GRID_END - GRID_START) / 60) * HOUR_H;
  const hours: number[] = [];
  for (let h = GRID_START; h <= GRID_END; h += 60) hours.push(h);

  const [dragPreview, setDragPreview] = useState<Section | null>(null);
  useEffect(() => { if (!dragCourse) setDragPreview(null); }, [dragCourse]);

  const candidates = useMemo(() => {
    if (!dragCourse) return [] as Section[];
    const base = sections.filter((s) => s.course !== dragCourse.code);
    return dragCourse.sections
      .filter((s) => s.meetings.length > 0)
      .filter((s) => !base.some((b) => sectionsConflict(s, b)));
  }, [dragCourse, sections]);

  const hintByDay: Record<string, { s: Section; m: Section["meetings"][number] }[]> = {};
  for (const s of candidates) for (const m of s.meetings) (hintByDay[m.day] ||= []).push({ s, m });

  function allowDrop(e: React.DragEvent) { if (dragCourse) e.preventDefault(); }
  // clear drag state on ANY drop — the dragged block may unmount on select, so
  // its onDragEnd never fires; clear here so we don't get stuck in drag mode.
  function endDrag() { setDragPreview(null); onDragCourse(null); }

  const byDay: Record<Day, { s: Section; m: Section["meetings"][number] }[]> = {
    Mon: [], Tue: [], Wed: [], Thu: [], Fri: [], Sat: []
  };
  for (const s of sections) for (const m of s.meetings) byDay[m.day].push({ s, m });

  const hoverGhost: Record<string, Section["meetings"]> = {};
  if (ghost && !dragCourse && !sections.some((s) => s.id === ghost.id))
    for (const m of ghost.meetings) (hoverGhost[m.day] ||= []).push(m);

  return (
    <div className="tt-grid" style={{ height: totalH + 28 }}>
      <div className="tt-grid-corner" />
      <div className="tt-grid-days">
        {DAYS.map((d) => (<div key={d} className="tt-grid-day-h">{DAY_TH[d]}</div>))}
      </div>
      <div className="tt-grid-hours" style={{ height: totalH }}>
        {hours.map((h) => (
          <div key={h} className="tt-grid-hour" style={{ height: HOUR_H }}><span>{fmtMinutes(h)}</span></div>
        ))}
      </div>
      <div className="tt-grid-cols" style={{ height: totalH }}>
        {DAYS.map((d) => (
          <div key={d} className="tt-grid-col" onDragOver={allowDrop} onDrop={(e) => { e.preventDefault(); endDrag(); }}>
            {hours.slice(0, -1).map((h) => (<div key={h} className="tt-grid-cell" style={{ height: HOUR_H }} />))}

            {byDay[d].map(({ s, m }, i) => {
              const top = ((m.start - GRID_START) / 60) * HOUR_H;
              const height = Math.max(((m.end - m.start) / 60) * HOUR_H, 26);
              const bad = conflicts.has(s.id);
              const course = courseByCode.get(s.course);
              const eligible = course ? dragEligible(course) : false;
              return (
                <div key={i} className={"tt-block tt-block-live" + (bad ? " conflict" : "")}
                  style={{ top, height, ["--c" as never]: courseColor(s.course) }}
                  title={`${s.course} ${s.section} · ${m.time} · ${fmtRoom(m.room)} — ${eligible ? "ลากเพื่อเปลี่ยน หรือกดเพื่อเลือก" : "หลายเซคชัน · กดเพื่อเลือก"}`}
                  draggable
                  onClick={() => course && onChooser(course)}
                  onDragStart={(e) => {
                    if (course && eligible) {
                      onDragCourse(course); e.dataTransfer.effectAllowed = "move"; e.dataTransfer.setData("text/plain", s.course);
                    } else {
                      e.preventDefault();
                      if (course) { onToast(dragBlockMsg(course)); onChooser(course); }
                    }
                  }}
                  onDragEnd={() => onDragCourse(null)}>
                  {eligible && <span className="tt-block-grip" aria-hidden="true">⠿</span>}
                  <span className="tt-block-code">{s.course} <small>{s.section}</small></span>
                  <span className="tt-block-name">{s.courseName}</span>
                  <span className="tt-block-time">{m.time}</span>
                  <span className="tt-block-room">{fmtRoom(m.room)} · {m.type}</span>
                </div>
              );
            })}

            {(hintByDay[d] || []).map(({ s, m }, i) => {
              const top = ((m.start - GRID_START) / 60) * HOUR_H;
              const height = Math.max(((m.end - m.start) / 60) * HOUR_H, 26);
              const active = dragPreview?.id === s.id;
              return (
                <div key={"h" + i} className={"tt-block drop-hint" + (active ? " active" : "")}
                  style={{ top, height }}
                  onDragEnter={() => setDragPreview(s)}
                  onDragOver={(e) => { e.preventDefault(); if (dragPreview?.id !== s.id) setDragPreview(s); }}
                  onDrop={(e) => { e.preventDefault(); e.stopPropagation(); onSelect(s); endDrag(); }}>
                  <span className="tt-block-code">{s.course} <small>{s.section}</small></span>
                  <span className="tt-block-time">{m.time} · {fmtRoom(m.room)}</span>
                </div>
              );
            })}

            {(hoverGhost[d] || []).map((m, i) => {
              const top = ((m.start - GRID_START) / 60) * HOUR_H;
              const height = Math.max(((m.end - m.start) / 60) * HOUR_H, 26);
              return (
                <div key={"g" + i} className="tt-block ghost" style={{ top, height }}>
                  <span className="tt-block-code">{ghost!.course}</span>
                  <span className="tt-block-time">{m.time}</span>
                </div>
              );
            })}
          </div>
        ))}
      </div>
      {dragCourse && (
        <div className="tt-drag-banner">ลาก <b>{dragCourse.code}</b> ไปวางบนช่อง <span className="ok-dot" /> สีเขียว เพื่อเลือกเซคชัน</div>
      )}
    </div>
  );
}
