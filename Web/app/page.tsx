"use client";

import { useEffect, useRef, useState } from "react";
import { fetchDegreePlan } from "@/lib/api";
import { parsePrereqs, parsePrereqClauses, normalizeCode } from "@/lib/prereq";
import { buildEdges } from "@/lib/graph";
import type {
  DegreePlanLookupResponse,
  DegreePlan,
  DegreePlanQuery,
  DegreePlanOptions,
  CourseNode,
  PrereqEdge
} from "@/lib/types";
import TopBar from "./components/TopBar";
import Canvas from "./components/Canvas";
import Picker from "./components/Picker";

const EMPTY_QUERY: DegreePlanQuery = {
  academic_year: null,
  faculty_slug: null,
  department_slug: null,
  track_slug: null,
  plan_slug: null
};
const EMPTY_OPTIONS: DegreePlanOptions = {
  academic_years: [],
  faculties: [],
  departments: [],
  tracks: [],
  plans: []
};

type NextField = keyof DegreePlanQuery | "done";

export default function Page() {
  const [selected, setSelected] = useState<DegreePlanQuery>(EMPTY_QUERY);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [options, setOptions] = useState<DegreePlanOptions>(EMPTY_OPTIONS);
  const [nextField, setNextField] = useState<NextField>("academic_year");
  const [plan, setPlan] = useState<DegreePlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMsg, setLoadingMsg] = useState("กำลังสำรวจหลักสูตร…");

  // Selection lives in a guided Picker: full-screen "hero" until a plan is
  // drawn, then a "modal" over the map when the user wants to change it.
  const [pickerOpen, setPickerOpen] = useState(false);

  const [courses, setCourses] = useState<CourseNode[]>([]);
  const [edges, setEdges] = useState<PrereqEdge[]>([]);
  const byCodeRef = useRef<Map<string, CourseNode>>(new Map());

  const [withdrawn, setWithdrawn] = useState<Set<string>>(new Set());
  const [manualMoves, setManualMoves] = useState<
    Map<string, { yearIdx: number; semIdx: number }>
  >(new Map());

  async function refresh(partial: DegreePlanQuery) {
    setLoading(true);
    setLoadingMsg("กำลังสำรวจหลักสูตร…");
    try {
      let resp: DegreePlanLookupResponse = await fetchDegreePlan(partial);

      // Auto-skip uninformative steps: when the API only offers `default` as the
      // next track, silently pick it so users don't see a one-option dropdown.
      let working = { ...partial };
      let safety = 0;
      while (
        resp.next_query_field === "track_slug" &&
        resp.options.tracks.length === 1 &&
        resp.options.tracks[0].slug === "default" &&
        safety++ < 3
      ) {
        working = { ...working, track_slug: "default" };
        resp = await fetchDegreePlan(working);
      }
      // Reflect the auto-selection in app state so the UI stays consistent.
      if (working.track_slug && !partial.track_slug) {
        setSelected(working);
      }

      // Merge: keep cached lists for prior steps so re-opening a chip still
      // shows its options. The API only populates the *next* step's list.
      setOptions((prev) => {
        const incoming = resp.options ?? EMPTY_OPTIONS;
        return {
          academic_years:
            incoming.academic_years.length ? incoming.academic_years : prev.academic_years,
          faculties:
            incoming.faculties.length ? incoming.faculties : prev.faculties,
          departments:
            incoming.departments.length ? incoming.departments : prev.departments,
          tracks:
            incoming.tracks.length ? incoming.tracks : prev.tracks,
          plans:
            incoming.plans.length ? incoming.plans : prev.plans
        };
      });
      setNextField((resp.next_query_field as NextField) ?? "done");
      if (resp.degree_plan) {
        setPlan(resp.degree_plan);
        rebuildGraph(resp.degree_plan);
      } else {
        setPlan(null);
        setCourses([]);
        setEdges([]);
        byCodeRef.current = new Map();
      }
    } catch (e) {
      setLoadingMsg("เชื่อมต่อ API ไม่ได้ ลองอีกครั้ง");
      await new Promise((r) => setTimeout(r, 1200));
    } finally {
      setLoading(false);
    }
  }

  function rebuildGraph(p: DegreePlan) {
    const cohort = p.cohorts[0];
    if (!cohort) {
      setCourses([]);
      setEdges([]);
      byCodeRef.current = new Map();
      return;
    }
    // FLATTEN to a single row of semesters across all years.
    const nodes: CourseNode[] = [];
    let globalSemIdx = 0;
    cohort.years.forEach((y, yi) => {
      y.semesters.forEach((s, si) => {
        s.courses.forEach((c) => {
          const clauses = parsePrereqClauses(c.prerequisite ?? "");
          nodes.push({
            id: String(c.id),
            code: c.code ?? "",
            codeNorm: normalizeCode(c.code ?? "") ?? "",
            name: c.name,
            credits: c.credits ?? null,
            rawPre: c.prerequisite ?? "",
            preClauses: clauses,
            preCodes: parsePrereqs(c.prerequisite ?? ""),
            yearIdx: yi,
            semIdx: si,
            year: y.year,
            semester: s.semester
          });
        });
        globalSemIdx++;
      });
    });
    const { edges: e, byCode } = buildEdges(nodes);
    setCourses(nodes);
    setEdges(e);
    byCodeRef.current = byCode;
    setWithdrawn(new Set());
    setManualMoves(new Map());
  }

  useEffect(() => {
    refresh(EMPTY_QUERY);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Whenever the plan clears (e.g. user re-picks an upstream step), drop back
  // to the full-screen hero picker rather than the modal.
  useEffect(() => {
    if (!plan) setPickerOpen(false);
  }, [plan]);

  function pickField(
    field: keyof DegreePlanQuery,
    value: string,
    label: string
  ) {
    const FIELD_ORDER: (keyof DegreePlanQuery)[] = [
      "academic_year",
      "faculty_slug",
      "department_slug",
      "track_slug",
      "plan_slug"
    ];
    const idx = FIELD_ORDER.indexOf(field);
    const next: DegreePlanQuery = { ...selected };
    for (let i = idx; i < FIELD_ORDER.length; i++) next[FIELD_ORDER[i]] = null;
    next[field] = value;
    setSelected(next);
    setLabels((prev) => {
      const out = { ...prev };
      for (let i = idx; i < FIELD_ORDER.length; i++)
        delete out[FIELD_ORDER[i]];
      out[field] = label;
      return out;
    });
    refresh(next);
  }

  function toggleWithdrawn(id: string) {
    setWithdrawn((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }
  function moveCourse(id: string, yearIdx: number, semIdx: number) {
    setManualMoves((prev) => {
      const next = new Map(prev);
      next.set(id, { yearIdx, semIdx });
      return next;
    });
  }
  function resetUserState() {
    setWithdrawn(new Set());
    setManualMoves(new Map());
  }

  let activeCredits = 0;
  for (const c of courses) {
    if (!withdrawn.has(c.id)) activeCredits += c.credits || 0;
  }
  const activeCount = courses.length - withdrawn.size;

  const pickerMode: "hero" | "modal" | null = !plan
    ? "hero"
    : pickerOpen
    ? "modal"
    : null;

  return (
    <div className="shell">
      <TopBar
        selected={selected}
        labels={labels}
        plan={plan}
        activeCredits={activeCredits}
        activeCount={activeCount}
        totalCount={courses.length}
        withdrawnCount={withdrawn.size}
        onReset={resetUserState}
        onOpenPicker={() => setPickerOpen(true)}
      />

      {plan && (
        <Canvas
          plan={plan}
          courses={courses}
          edges={edges}
          withdrawn={withdrawn}
          manualMoves={manualMoves}
          onToggleWithdrawn={toggleWithdrawn}
          onMoveCourse={moveCourse}
        />
      )}

      {pickerMode && (
        <Picker
          mode={pickerMode}
          selected={selected}
          labels={labels}
          options={options}
          nextField={nextField}
          loading={loading}
          onPick={pickField}
          onClose={() => setPickerOpen(false)}
        />
      )}

      {loading && (
        <div className="loader">
          <div style={{ display: "grid", placeItems: "center" }}>
            <svg
              viewBox="0 0 100 100"
              width="56"
              height="56"
              aria-hidden="true"
            >
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke="currentColor"
                strokeWidth="1"
                strokeDasharray="4 6"
              />
              <circle
                cx="50"
                cy="50"
                r="40"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeDasharray="20 230"
                className="spin"
              />
            </svg>
            <div>{loadingMsg}</div>
          </div>
        </div>
      )}
    </div>
  );
}
