"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { CourseNode, DegreePlan, PrereqEdge } from "@/lib/types";
import {
  buildAdjacency,
  bfs,
  computeUnavailable,
  computeViolations
} from "@/lib/graph";

interface CanvasProps {
  plan: DegreePlan | null;
  courses: CourseNode[];
  edges: PrereqEdge[];
  withdrawn: Set<string>;
  manualMoves: Map<string, { yearIdx: number; semIdx: number }>;
  onToggleWithdrawn: (id: string) => void;
  onMoveCourse: (id: string, yearIdx: number, semIdx: number) => void;
}

interface ArcPath {
  d: string;
  fromId: string;
  toId: string;
  affected: boolean;
  violation: boolean;
  concurrent: boolean;
  ax: number;
  ay: number;
  bx: number;
  by: number;
}

const MIN_ZOOM = 0.35;
const MAX_ZOOM = 1.8;

export default function Canvas({
  plan,
  courses,
  edges,
  withdrawn,
  manualMoves,
  onToggleWithdrawn,
  onMoveCourse
}: CanvasProps) {
  const stageRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLDivElement | null>(null);

  // pan + zoom
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const panState = useRef<{
    panning: boolean;
    startX: number;
    startY: number;
    origX: number;
    origY: number;
  }>({
    panning: false,
    startX: 0,
    startY: 0,
    origX: 0,
    origY: 0
  });
  const [isPanning, setIsPanning] = useState(false);

  // arcs
  const [arcPaths, setArcPaths] = useState<ArcPath[]>([]);
  const [canvasSize, setCanvasSize] = useState({ w: 0, h: 0 });

  // drag-drop
  const [dragging, setDragging] = useState<CourseNode | null>(null);
  const [dropHint, setDropHint] = useState<{
    yearIdx: number;
    semIdx: number;
    violates: boolean;
  } | null>(null);

  // tooltip
  const [tip, setTip] = useState<{ x: number; y: number; html: string } | null>(
    null
  );

  // hover lineage
  const [focus, setFocus] = useState<{
    id: string;
    upstream: Set<string>;
    downstream: Set<string>;
  } | null>(null);

  const adjacency = useMemo(() => buildAdjacency(edges), [edges]);

  /* -------- placement grid -------- */
  const grid = useMemo(() => {
    if (!plan) return [] as CourseNode[][][];
    const cohort = plan.cohorts[0];
    if (!cohort) return [];
    const g: CourseNode[][][] = [];
    cohort.years.forEach((y, yi) => {
      g[yi] = [];
      y.semesters.forEach((_s, si) => {
        g[yi][si] = [];
      });
    });
    for (const c of courses) {
      const m = manualMoves.get(c.id);
      const yi = m ? m.yearIdx : c.yearIdx;
      const si = m ? m.semIdx : c.semIdx;
      if (!g[yi]) g[yi] = [];
      if (!g[yi][si]) g[yi][si] = [];
      g[yi][si].push(c);
      c.curYearIdx = yi;
      c.curSemIdx = si;
    }
    return g;
  }, [plan, courses, manualMoves]);

  /* -------- affected (cascade) / per-clause violations -------- */
  const affected = useMemo(
    () => computeUnavailable(courses, withdrawn),
    [courses, withdrawn]
  );
  const violations = useMemo(
    () => computeViolations(courses, manualMoves),
    [courses, manualMoves]
  );

  /* -------- per-edge violation: respects "concurrent" rule and OR alternatives -------- */
  const edgeStatus = useMemo(() => {
    // For each (toId, clauseIdx), is the clause itself satisfied?
    // (any alternative meets the temporal constraint)
    const order = (c: CourseNode) =>
      (c.curYearIdx ?? c.yearIdx) * 10 + (c.curSemIdx ?? c.semIdx);
    const courseById = new Map(courses.map((c) => [c.id, c]));
    const clauseSatisfied = new Map<string, boolean>(); // key = `${toId}#${clauseIdx}`

    for (const c of courses) {
      c.preClauses.forEach((cl, ci) => {
        let anyOk = false;
        let anyKnown = false;
        const cOrder = order(c);
        for (const code of cl.codes) {
          const alt = courses.find((x) => x.codeNorm === code);
          if (!alt) continue;
          anyKnown = true;
          const aOrder = order(alt);
          const ok = cl.kind === "pass" ? aOrder < cOrder : aOrder <= cOrder;
          if (ok) { anyOk = true; break; }
        }
        clauseSatisfied.set(`${c.id}#${ci}`, !anyKnown || anyOk);
      });
    }
    return { clauseSatisfied };
  }, [courses]);

  /* -------- recompute arcs whenever layout settles -------- */
  function recomputeArcs() {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const cRect = canvas.getBoundingClientRect();
    // canvas is scaled by `zoom`. We want arc coords in canvas-local space
    // (pre-transform), so divide by zoom.
    const w = canvas.scrollWidth;
    const h = canvas.scrollHeight;
    setCanvasSize({ w, h });

    const newPaths: ArcPath[] = [];
    const courseEls = canvas.querySelectorAll(".course");
    const courseMap = new Map<string, DOMRect>();
    courseEls.forEach((el) => {
      const id = (el as HTMLElement).dataset.courseId;
      if (id) courseMap.set(id, el.getBoundingClientRect());
    });

    for (const e of edges) {
      const ar = courseMap.get(e.from.id);
      const br = courseMap.get(e.to.id);
      if (!ar || !br) continue;

      // viewport-space → canvas-local space
      const x1 = (ar.right - cRect.left) / zoom;
      const y1 = (ar.top + ar.height / 2 - cRect.top) / zoom;
      const x2 = (br.left - cRect.left) / zoom;
      const y2 = (br.top + br.height / 2 - cRect.top) / zoom;

      // gentle horizontal bezier
      const dx = Math.max(40, Math.abs(x2 - x1) * 0.45);
      const cp1x = x1 + dx;
      const cp1y = y1;
      const cp2x = x2 - dx;
      const cp2y = y2;
      const d = `M ${x1} ${y1} C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${x2} ${y2}`;

      // an edge is "violation" only if its clause has no satisfied alternative
      const clauseKey = `${e.to.id}#${e.clauseIdx}`;
      const clauseOk = edgeStatus.clauseSatisfied.get(clauseKey) !== false;

      // an edge is "affected" if the FROM is unavailable AND removing it
      // breaks the clause for the TO (i.e. no other alternative survives)
      let isAffected = false;
      if (affected.has(e.from.id)) {
        // is there a sibling alternative still available?
        const cl = e.to.preClauses[e.clauseIdx];
        let siblingOk = false;
        if (cl) {
          for (const code of cl.codes) {
            const alt = courses.find((x) => x.codeNorm === code);
            if (!alt || alt.id === e.from.id) continue;
            if (!affected.has(alt.id)) { siblingOk = true; break; }
          }
        }
        if (!siblingOk) isAffected = true;
      }

      newPaths.push({
        d,
        fromId: e.from.id,
        toId: e.to.id,
        affected: isAffected,
        violation: !clauseOk,
        concurrent: e.kind === "concurrent",
        ax: x1,
        ay: y1,
        bx: x2,
        by: y2
      });
    }
    setArcPaths(newPaths);
  }

  // recompute when grid (positions) or edges or impact set change
  useLayoutEffect(() => {
    const id = requestAnimationFrame(recomputeArcs);
    return () => cancelAnimationFrame(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grid, edges, withdrawn, affected, violations]);

  // also recompute on zoom change (since DOMRects reflect scaled values)
  useLayoutEffect(() => {
    const id = requestAnimationFrame(recomputeArcs);
    return () => cancelAnimationFrame(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zoom]);

  // window resize
  useEffect(() => {
    let t: ReturnType<typeof setTimeout> | null = null;
    const onResize = () => {
      if (t) clearTimeout(t);
      t = setTimeout(recomputeArcs, 100);
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* -------- center on first plan load -------- */
  useEffect(() => {
    if (!plan) return;
    // Reset pan/zoom on plan change
    setZoom(1);
    requestAnimationFrame(() => {
      const stage = stageRef.current;
      const canvas = canvasRef.current;
      if (!stage || !canvas) return;
      // position canvas so its top-left starts a bit padded
      setPan({ x: 24, y: (stage.clientHeight - canvas.scrollHeight) / 2 });
    });
  }, [plan]);

  /* -------- pan handlers (mouse) -------- */
  function onStageMouseDown(e: React.MouseEvent) {
    // ignore if clicking on an interactive element
    const target = e.target as HTMLElement;
    if (target.closest(".course") || target.closest(".chip") || target.closest(".popover")) return;
    panState.current = {
      panning: true,
      startX: e.clientX,
      startY: e.clientY,
      origX: pan.x,
      origY: pan.y
    };
    setIsPanning(true);
  }
  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (!panState.current.panning) return;
      const dx = e.clientX - panState.current.startX;
      const dy = e.clientY - panState.current.startY;
      setPan({
        x: panState.current.origX + dx,
        y: panState.current.origY + dy
      });
    }
    function onUp() {
      panState.current.panning = false;
      setIsPanning(false);
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  /* -------- touch pan + pinch zoom (mobile / tablet) -------- */
  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;

    let mode: "idle" | "pan" | "pinch" = "idle";
    let startX = 0, startY = 0;
    let origPanX = 0, origPanY = 0;
    let pinchStartDist = 0;
    let pinchStartZoom = 1;
    let pinchAnchor = { x: 0, y: 0 };

    function dist(t1: Touch, t2: Touch) {
      return Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
    }
    function midpoint(t1: Touch, t2: Touch) {
      return { x: (t1.clientX + t2.clientX) / 2, y: (t1.clientY + t2.clientY) / 2 };
    }

    function onTouchStart(e: TouchEvent) {
      const target = e.target as HTMLElement;
      // ignore touches starting on a course card; the course handles its own
      // long-press drag (see touch-drag effect below).
      if (target.closest(".course")) return;
      if (e.touches.length === 1) {
        mode = "pan";
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
        setPan((p) => {
          origPanX = p.x;
          origPanY = p.y;
          return p;
        });
      } else if (e.touches.length === 2) {
        mode = "pinch";
        pinchStartDist = dist(e.touches[0], e.touches[1]);
        const rect = stage!.getBoundingClientRect();
        const mid = midpoint(e.touches[0], e.touches[1]);
        pinchAnchor = { x: mid.x - rect.left, y: mid.y - rect.top };
        setZoom((z) => { pinchStartZoom = z; return z; });
      }
    }
    function onTouchMove(e: TouchEvent) {
      if (mode === "pan" && e.touches.length === 1) {
        e.preventDefault();
        const dx = e.touches[0].clientX - startX;
        const dy = e.touches[0].clientY - startY;
        setPan({ x: origPanX + dx, y: origPanY + dy });
      } else if (mode === "pinch" && e.touches.length === 2) {
        e.preventDefault();
        const d = dist(e.touches[0], e.touches[1]);
        const factor = d / pinchStartDist;
        const next = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, pinchStartZoom * factor));
        // anchor zoom at the pinch midpoint
        setZoom((z) => {
          const realFactor = next / z;
          setPan((p) => ({
            x: pinchAnchor.x - (pinchAnchor.x - p.x) * realFactor,
            y: pinchAnchor.y - (pinchAnchor.y - p.y) * realFactor
          }));
          return next;
        });
      }
    }
    function onTouchEnd(e: TouchEvent) {
      if (e.touches.length === 0) mode = "idle";
      else if (e.touches.length === 1) {
        // drop from pinch back to pan
        mode = "pan";
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
        setPan((p) => { origPanX = p.x; origPanY = p.y; return p; });
      }
    }

    stage.addEventListener("touchstart", onTouchStart, { passive: true });
    stage.addEventListener("touchmove", onTouchMove, { passive: false });
    stage.addEventListener("touchend", onTouchEnd);
    stage.addEventListener("touchcancel", onTouchEnd);
    return () => {
      stage.removeEventListener("touchstart", onTouchStart);
      stage.removeEventListener("touchmove", onTouchMove);
      stage.removeEventListener("touchend", onTouchEnd);
      stage.removeEventListener("touchcancel", onTouchEnd);
    };
  }, []);

  /* -------- wheel zoom (anchor at cursor) -------- */
  function onStageWheel(e: React.WheelEvent) {
    if (!e.ctrlKey && !e.metaKey && Math.abs(e.deltaX) > 0) {
      // touchpad horizontal pan
      setPan((p) => ({ x: p.x - e.deltaX, y: p.y - e.deltaY }));
      e.preventDefault();
      return;
    }
    if (e.ctrlKey || e.metaKey || e.altKey) {
      e.preventDefault();
      const stage = stageRef.current!;
      const rect = stage.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      const factor = e.deltaY > 0 ? 0.9 : 1.1;
      zoomAt(mouseX, mouseY, factor);
      return;
    }
    // plain wheel = vertical pan
    setPan((p) => ({ x: p.x - e.deltaX, y: p.y - e.deltaY }));
  }
  function zoomAt(stageX: number, stageY: number, factor: number) {
    setZoom((z) => {
      const next = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, z * factor));
      const realFactor = next / z;
      setPan((p) => ({
        x: stageX - (stageX - p.x) * realFactor,
        y: stageY - (stageY - p.y) * realFactor
      }));
      return next;
    });
  }
  function zoomIn() {
    const stage = stageRef.current;
    if (!stage) return;
    zoomAt(stage.clientWidth / 2, stage.clientHeight / 2, 1.15);
  }
  function zoomOut() {
    const stage = stageRef.current;
    if (!stage) return;
    zoomAt(stage.clientWidth / 2, stage.clientHeight / 2, 1 / 1.15);
  }
  function resetView() {
    setZoom(1);
    const stage = stageRef.current;
    const canvas = canvasRef.current;
    if (!stage || !canvas) return;
    setPan({ x: 24, y: (stage.clientHeight - canvas.scrollHeight) / 2 });
  }
  function fitView() {
    const stage = stageRef.current;
    const canvas = canvasRef.current;
    if (!stage || !canvas) return;
    const padding = 60;
    const sx = (stage.clientWidth - padding * 2) / canvas.scrollWidth;
    const sy = (stage.clientHeight - padding * 2) / canvas.scrollHeight;
    const z = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.min(sx, sy)));
    setZoom(z);
    setPan({
      x: (stage.clientWidth - canvas.scrollWidth * z) / 2,
      y: (stage.clientHeight - canvas.scrollHeight * z) / 2
    });
  }

  /* -------- drop helpers -------- */
  function wouldViolate(c: CourseNode, newYi: number, newSi: number) {
    const newOrder = newYi * 10 + newSi;
    // For every clause, at least one alternative must satisfy its temporal rule.
    for (const cl of c.preClauses) {
      let anyOk = false;
      let anyKnown = false;
      for (const code of cl.codes) {
        const pre = courses.find((x) => x.codeNorm === code);
        if (!pre) continue;
        anyKnown = true;
        const m = manualMoves.get(pre.id);
        const pYi = m ? m.yearIdx : pre.yearIdx;
        const pSi = m ? m.semIdx : pre.semIdx;
        const pOrder = pYi * 10 + pSi;
        const ok = cl.kind === "pass" ? pOrder < newOrder : pOrder <= newOrder;
        if (ok) { anyOk = true; break; }
      }
      if (anyKnown && !anyOk) return true;
    }
    return false;
  }

  /* -------- focus mode -------- */
  function enterFocus(c: CourseNode) {
    const upstream = bfs(c.id, adjacency.inn);
    const downstream = bfs(c.id, adjacency.out);
    setFocus({ id: c.id, upstream, downstream });
  }
  function leaveFocus() {
    setFocus(null);
  }

  /* -------- tooltip -------- */
  function showTip(c: CourseNode, e: React.MouseEvent) {
    const desc = bfs(c.id, adjacency.out);
    const isAffected = affected.has(c.id) && !withdrawn.has(c.id);
    const isWithdrawn = withdrawn.has(c.id);

    const lines: string[] = [];
    lines.push(
      `<code>${escapeHtml(c.code || "—")}</code>  ${escapeHtml(c.name)}`
    );
    if (c.credits != null) lines.push(`${c.credits} หน่วยกิต`);

    // render each prereq clause with its kind label
    for (const cl of c.preClauses) {
      const codes = cl.codes.join(" หรือ ");
      const tag =
        cl.kind === "concurrent"
          ? `<span style="color:var(--blue-soft)">เรียนควบคู่ได้</span>`
          : `<span style="color:var(--blue)">ต้องสอบได้ก่อน</span>`;
      lines.push(`${tag} <code>${escapeHtml(codes)}</code>`);
    }

    if (desc.size)
      lines.push(`เป็นวิชาก่อนของ ${desc.size} วิชาด้านหลัง`);
    if (isWithdrawn) lines.push(`<span class="impact">ถอนแล้ว</span>`);
    if (isAffected)
      lines.push(
        `<span class="impact">⚠ ได้รับผลกระทบจากการถอนวิชาอื่น</span>`
      );
    setTip({
      x: e.clientX + 14,
      y: e.clientY + 14,
      html: lines.join("<br>")
    });
  }
  function moveTip(e: React.MouseEvent) {
    setTip((prev) =>
      prev ? { ...prev, x: e.clientX + 14, y: e.clientY + 14 } : null
    );
  }
  function hideTip() {
    setTip(null);
  }

  /* -------- render -------- */
  if (!plan) {
    return (
      <div
        ref={stageRef}
        className="stage"
        style={{ cursor: "default" }}
      >
        <div className="welcome">
          <div className="welcome-inner">
            <div className="welcome-step">เริ่มต้น</div>
            <h1>
              เลือก <b>ปี · คณะ · สาขา · แทร็ก · แผน</b>
              <br />
              เพื่อวาดเส้นทางการเรียนของคุณ
            </h1>
            <p>
              คลิกเลือกด้านบนตามลำดับ ระบบจะวาดแผนที่หลักสูตรให้คุณ
              เห็นทุกเทอม ทุกวิชา และเส้นเชื่อมวิชาก่อนหลังในกราฟเดียว
            </p>
          </div>
        </div>
      </div>
    );
  }

  const cohort = plan.cohorts[0];
  // Some plans carry no cohort/year data in the source. Guard so the render
  // doesn't crash to a blank canvas (rebuildGraph guards the same case).
  if (!cohort || !cohort.years || cohort.years.length === 0) {
    return (
      <div ref={stageRef} className="stage" style={{ cursor: "default" }}>
        <div className="welcome">
          <div className="welcome-inner">
            <div className="welcome-step">ไม่มีข้อมูล</div>
            <h1>
              แผนนี้<b>ยังไม่มีข้อมูลรายวิชา</b>
            </h1>
            <p>ลองเลือกแผนเรียนอื่น หรือปีการศึกษาอื่นดูนะ</p>
          </div>
        </div>
      </div>
    );
  }
  // single-row: flatten all (year, semester) pairs in order
  const flatSemesters: { yi: number; si: number; sem: any; year: number }[] = [];
  cohort.years.forEach((y, yi) => {
    y.semesters.forEach((s, si) => {
      flatSemesters.push({ yi, si, sem: s, year: y.year });
    });
  });

  return (
    <div
      ref={stageRef}
      className={"stage" + (isPanning ? " panning" : "")}
      onMouseDown={onStageMouseDown}
      onWheel={onStageWheel}
    >
      <div
        ref={canvasRef}
        className={"canvas" + (focus ? " focusing" : "")}
        style={{
          transform: `translate3d(${pan.x}px, ${pan.y}px, 0) scale(${zoom})`
        }}
      >
        {/* arcs sit behind the row but inside the same scaled canvas */}
        <svg
          className="arcs"
          width={canvasSize.w}
          height={canvasSize.h}
          viewBox={`0 0 ${canvasSize.w || 1} ${canvasSize.h || 1}`}
          style={{ width: canvasSize.w, height: canvasSize.h }}
        >
          {arcPaths.map((p, i) => {
            const lineage =
              focus &&
              (p.fromId === focus.id ||
                p.toId === focus.id ||
                (focus.upstream.has(p.fromId) &&
                  (p.toId === focus.id || focus.upstream.has(p.toId))) ||
                (focus.downstream.has(p.toId) &&
                  (p.fromId === focus.id || focus.downstream.has(p.fromId))));
            const cls = [
              "arc",
              "draw-in",
              p.affected ? "affected" : "",
              p.violation ? "violation" : "",
              p.concurrent ? "concurrent" : "",
              lineage ? "lineage" : ""
            ]
              .filter(Boolean)
              .join(" ");
            return (
              <g key={i}>
                <path className={cls} d={p.d} />
                <circle
                  className={"arc-node" + (p.affected ? " affected" : "")}
                  cx={p.ax}
                  cy={p.ay}
                  r={2.2}
                />
                <circle
                  className={"arc-node" + (p.affected ? " affected" : "")}
                  cx={p.bx}
                  cy={p.by}
                  r={2.2}
                />
              </g>
            );
          })}
        </svg>

        <div className="row" key={`${courses.length}-${courses[0]?.id ?? "0"}`}>
          {flatSemesters.map((entry, idx) => {
            const list = grid[entry.yi]?.[entry.si] || [];
            const credits = list.reduce(
              (acc, c) => acc + (c.credits || 0),
              0
            );
            const dropping =
              dropHint &&
              dropHint.yearIdx === entry.yi &&
              dropHint.semIdx === entry.si;
            const cls = [
              "semester",
              dropping
                ? dropHint.violates
                  ? "drop-violation"
                  : "drop-target"
                : ""
            ]
              .filter(Boolean)
              .join(" ");
            return (
              <div key={idx} style={{ display: "contents" }}>
                <div
                  className={cls}
                  onDragOver={(e) => {
                    if (!dragging) return;
                    e.preventDefault();
                    setDropHint({
                      yearIdx: entry.yi,
                      semIdx: entry.si,
                      violates: wouldViolate(dragging, entry.yi, entry.si)
                    });
                  }}
                  onDragLeave={() => {
                    if (
                      dropHint &&
                      dropHint.yearIdx === entry.yi &&
                      dropHint.semIdx === entry.si
                    ) {
                      setDropHint(null);
                    }
                  }}
                  onDrop={(e) => {
                    e.preventDefault();
                    const id = e.dataTransfer.getData("text/plain");
                    if (id) onMoveCourse(id, entry.yi, entry.si);
                    setDropHint(null);
                  }}
                >
                  <div className="sem-header">
                    <div className="sem-title">
                      ปี {entry.year}{" "}
                      <small>· เทอม {entry.sem.semester}</small>
                    </div>
                    <div className="sem-credits">{credits} นก.</div>
                  </div>
                  <div className="course-list">
                    {list.map((c) => {
                      const isWithdrawn = withdrawn.has(c.id);
                      const isAffected = !isWithdrawn && affected.has(c.id);
                      const isViolation = violations.has(c.id);
                      let lineageCls = "";
                      if (focus) {
                        if (focus.id === c.id) lineageCls = "lineage";
                        else if (focus.upstream.has(c.id))
                          lineageCls = "lineage upstream";
                        else if (focus.downstream.has(c.id))
                          lineageCls = "lineage downstream";
                      }
                      const courseCls = [
                        "course",
                        isWithdrawn ? "withdrawn" : "",
                        isAffected ? "affected" : "",
                        isViolation ? "violation" : "",
                        lineageCls
                      ]
                        .filter(Boolean)
                        .join(" ");
                      return (
                        <div
                          key={c.id}
                          className={courseCls}
                          data-course-id={c.id}
                          draggable
                          onDragStart={(e) => {
                            setDragging(c);
                            e.dataTransfer.setData("text/plain", c.id);
                            e.dataTransfer.effectAllowed = "move";
                          }}
                          onDragEnd={() => {
                            setDragging(null);
                            setDropHint(null);
                          }}
                          onClick={(e) => {
                            if (e.detail === 0) return;
                            // ignore clicks that came from a pan
                            if (panState.current.panning) return;
                            onToggleWithdrawn(c.id);
                          }}
                          onMouseEnter={(e) => {
                            showTip(c, e);
                            enterFocus(c);
                          }}
                          onMouseMove={moveTip}
                          onMouseLeave={() => {
                            hideTip();
                            leaveFocus();
                          }}
                          onMouseDown={(e) => e.stopPropagation()}
                        >
                          <div className="course-code">
                            <span>{c.code || "—"}</span>
                            <span className="credits">
                              {c.credits != null ? `${c.credits} นก.` : ""}
                            </span>
                          </div>
                          <div className="course-name">{c.name}</div>
                          {c.preCodes.length > 0 && (
                            <div className="course-pre">
                              ↺ ต้องผ่าน {c.preCodes.join(", ")}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
                {idx < flatSemesters.length - 1 && (
                  <div className="between" aria-hidden="true">
                    <svg viewBox="0 0 28 14">
                      <path
                        d="M0 7 L24 7 M18 2 L24 7 L18 12"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.2"
                      />
                    </svg>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {tip && (
        <div
          className="tip"
          style={{ left: tip.x, top: tip.y }}
          dangerouslySetInnerHTML={{ __html: tip.html }}
        />
      )}

      <div className="zoom-panel" aria-label="zoom controls">
        <div className="zoom-readout">{Math.round(zoom * 100)}%</div>
        <button className="zoom-btn" title="ขยาย" onClick={zoomIn}>
          +
        </button>
        <button className="zoom-btn" title="ย่อ" onClick={zoomOut}>
          −
        </button>
        <button className="zoom-btn" title="พอดีจอ" onClick={fitView}>
          ⤢
        </button>
        <button className="zoom-btn" title="100%" onClick={resetView}>
          1
        </button>
      </div>

      <div className="legend">
        <div className="legend-row">
          <span className="dot" /> ต้องสอบได้ก่อน
        </div>
        <div className="legend-row">
          <span className="dot dashed-blue" /> เรียนควบคู่ได้
        </div>
        <div className="legend-row">
          <span className="dot red" /> ผลกระทบจากการถอน
        </div>
        <div className="legend-row">
          <span className="dot gold-dashed" /> ลำดับไม่ถูกต้อง
        </div>
      </div>
    </div>
  );
}

function escapeHtml(s: string) {
  return (s || "").replace(/[&<>"]/g, (ch) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch] || ch)
  );
}
