"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type {
  DegreePlanOptions,
  DegreePlanQuery,
  AcademicYearOption,
  FacultyRef,
  DepartmentRef,
  TrackRef,
  PlanTypeRef
} from "@/lib/types";

type AnyOption =
  | AcademicYearOption
  | FacultyRef
  | DepartmentRef
  | TrackRef
  | PlanTypeRef;

const FIELDS: {
  key: keyof DegreePlanQuery;
  label: string;
  optionsKey: keyof DegreePlanOptions;
}[] = [
  { key: "academic_year",   label: "ปีการศึกษา", optionsKey: "academic_years" },
  { key: "faculty_slug",    label: "คณะ",         optionsKey: "faculties" },
  { key: "department_slug", label: "สาขาวิชา",    optionsKey: "departments" },
  { key: "track_slug",      label: "แทร็ก",       optionsKey: "tracks" },
  { key: "plan_slug",       label: "แผนเรียน",    optionsKey: "plans" }
];
const ORDER = FIELDS.map((f) => f.key);

function getOptionValue(
  field: keyof DegreePlanQuery,
  o: AnyOption
): { value: string; label: string; sub?: string } {
  if (field === "academic_year") {
    const yo = o as AcademicYearOption;
    return { value: yo.year, label: `ปีการศึกษา ${yo.year}` };
  }
  if (field === "faculty_slug" || field === "department_slug") {
    const fo = o as FacultyRef;
    return { value: fo.slug, label: fo.name_th, sub: fo.name_en || undefined };
  }
  const t = o as TrackRef;
  const label = t.slug === "default" ? "หลักสูตรปกติ" : t.name;
  return { value: t.slug, label };
}

interface PickerProps {
  mode: "hero" | "modal";
  selected: DegreePlanQuery;
  labels: Record<string, string>;
  options: DegreePlanOptions;
  nextField: keyof DegreePlanQuery | "done";
  loading: boolean;
  onPick: (field: keyof DegreePlanQuery, value: string, label: string) => void;
  onClose?: () => void;
}

export default function Picker({
  mode,
  selected,
  labels,
  options,
  nextField,
  loading,
  onPick,
  onClose
}: PickerProps) {
  // Hide the single-default track step (mirrors the auto-skip in page.refresh).
  const trackCount = options.tracks?.length ?? 0;
  const hideTrack =
    trackCount <= 1 &&
    nextField !== "track_slug" &&
    selected.track_slug !== null &&
    !options.tracks.some((t) => t.slug !== "default");
  const fields = FIELDS.filter((f) => !(hideTrack && f.key === "track_slug"));

  const maxIdx =
    nextField === "done"
      ? ORDER.length
      : ORDER.indexOf(nextField as keyof DegreePlanQuery);

  // Which step's list is currently shown. Follows the backend's next step,
  // but the user can jump back by clicking a completed step.
  const [editing, setEditing] = useState<keyof DegreePlanQuery>(
    (nextField === "done" ? "plan_slug" : nextField) as keyof DegreePlanQuery
  );
  useEffect(() => {
    if (nextField === "done") return;
    setEditing(nextField as keyof DegreePlanQuery);
  }, [nextField]);

  // Modal closes on Esc. (It does NOT auto-close on "done" — opening it over an
  // already-finished plan must keep it open so the user can change things.)
  useEffect(() => {
    if (mode !== "modal") return;
    const onEsc = (e: KeyboardEvent) => e.key === "Escape" && onClose?.();
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [mode, onClose]);

  // Picking a (new) plan completes the selection → close the modal so the map
  // shows. Picking an upstream step clears the plan and the parent drops back to
  // the hero on its own.
  function handlePick(
    field: keyof DegreePlanQuery,
    value: string,
    label: string
  ) {
    onPick(field, value, label);
    if (mode === "modal" && field === "plan_slug") onClose?.();
  }

  const activeField = fields.find((f) => f.key === editing) ?? fields[0];
  const activeOptions =
    (options[activeField.optionsKey] as AnyOption[]) ?? [];

  const [q, setQ] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    setQ("");
    const t = setTimeout(() => inputRef.current?.focus(), 80);
    return () => clearTimeout(t);
  }, [editing]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return activeOptions;
    return activeOptions.filter((o) => {
      const v = getOptionValue(activeField.key, o);
      return (
        v.label.toLowerCase().includes(needle) ||
        (v.sub || "").toLowerCase().includes(needle) ||
        v.value.toLowerCase().includes(needle)
      );
    });
  }, [q, activeOptions, activeField]);

  const card = (
    <div className="picker-card" onMouseDown={(e) => e.stopPropagation()}>
      {mode === "modal" && (
        <button className="picker-close" onClick={onClose} aria-label="ปิด">
          ✕
        </button>
      )}

      <div className="picker-head">
        <div className="picker-kicker">OneDegree · แผนที่หลักสูตร</div>
        <h2 className="picker-title">
          {mode === "modal" ? "เปลี่ยนหลักสูตร" : "เลือกหลักสูตรของคุณ"}
        </h2>
        {mode !== "modal" && (
          <p className="picker-sub">
            เลือกทีละขั้น แล้วเราจะวาดเส้นทางการเรียนให้ทันที
          </p>
        )}
      </div>

      <ol className="picker-steps">
        {fields.map((f, i) => {
          const hasValue = !!selected[f.key];
          const idx = ORDER.indexOf(f.key);
          const enabled = idx <= maxIdx || hasValue;
          const isActive = editing === f.key;
          const cls = [
            "picker-step",
            hasValue ? "done" : "",
            isActive ? "active" : "",
            !enabled ? "locked" : ""
          ]
            .filter(Boolean)
            .join(" ");
          return (
            <li key={f.key}>
              <button
                className={cls}
                disabled={!enabled}
                onClick={() => enabled && setEditing(f.key)}
              >
                <span className="picker-step-n">
                  {hasValue ? "✓" : String(i + 1).padStart(2, "0")}
                </span>
                <span className="picker-step-text">
                  <span className="picker-step-label">{f.label}</span>
                  <span className="picker-step-value">
                    {hasValue ? labels[f.key] : "—"}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>

      <div className="picker-panel">
        <div className="picker-panel-head">
          <span className="picker-panel-title">
            เลือก{activeField.label}
            {!loading && filtered.length > 0 && (
              <span className="picker-count">{filtered.length}</span>
            )}
          </span>
          {activeOptions.length > 6 && (
            <input
              ref={inputRef}
              className="picker-search"
              placeholder="พิมพ์เพื่อค้นหา…"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          )}
        </div>
        <div
          className={
            "picker-list-wrap" + (filtered.length > 6 ? " scrollable" : "")
          }
        >
          <div className="picker-list">
            {loading && activeOptions.length === 0 ? (
              <div className="picker-empty">กำลังโหลด…</div>
            ) : loading && nextField === "done" ? (
              <div className="picker-empty">กำลังวาดแผนที่หลักสูตร…</div>
            ) : filtered.length === 0 ? (
              <div className="picker-empty">ไม่พบตัวเลือก</div>
            ) : (
              filtered.map((o, i) => {
                const v = getOptionValue(activeField.key, o);
                const chosen = selected[activeField.key] === v.value;
                return (
                  <button
                    key={v.value}
                    className={"picker-item" + (chosen ? " chosen" : "")}
                    onClick={() => handlePick(activeField.key, v.value, v.label)}
                  >
                    <span className="picker-item-n">
                      {String(i + 1).padStart(2, "0")}
                    </span>
                    <span className="picker-item-text">
                      <span className="picker-item-name">{v.label}</span>
                      {v.sub && (
                        <span className="picker-item-sub">{v.sub}</span>
                      )}
                    </span>
                    {chosen && <span className="picker-item-check">✓</span>}
                  </button>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );

  if (mode === "modal") {
    return (
      <div className="picker-overlay" onMouseDown={() => onClose?.()}>
        {card}
      </div>
    );
  }
  return <div className="picker-hero">{card}</div>;
}
