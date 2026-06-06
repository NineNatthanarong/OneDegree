"use client";

import Link from "next/link";
import type { DegreePlan, DegreePlanQuery } from "@/lib/types";

interface TopBarProps {
  selected: DegreePlanQuery;
  labels: Record<string, string>;
  plan: DegreePlan | null;
  activeCredits: number;
  activeCount: number;
  totalCount: number;
  withdrawnCount: number;
  onReset: () => void;
  onOpenPicker: () => void;
}

// Order the compact summary reads in. Track is omitted — it's usually the
// implicit default and just adds noise to the topbar.
const SUMMARY_FIELDS: (keyof DegreePlanQuery)[] = [
  "academic_year",
  "faculty_slug",
  "department_slug",
  "plan_slug"
];

export default function TopBar(props: TopBarProps) {
  const {
    labels,
    plan,
    activeCredits,
    activeCount,
    totalCount,
    withdrawnCount,
    onReset,
    onOpenPicker
  } = props;

  const summary = SUMMARY_FIELDS.map((k) => labels[k])
    .filter(Boolean)
    .join("  ·  ");

  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark">
          <svg viewBox="0 0 24 24" width={20} height={20} aria-hidden="true">
            <circle
              cx="12"
              cy="12"
              r="10"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.4"
            />
            <path
              d="M5 17 Q 12 3 19 17"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.4"
            />
            <circle cx="5" cy="17" r="1.4" fill="currentColor" />
            <circle cx="19" cy="17" r="1.4" fill="currentColor" />
            <circle cx="12" cy="6.5" r="1.4" fill="currentColor" />
          </svg>
        </div>
        <div>
          <div className="brand-name">
            One<span className="deg">Degree</span>
          </div>
          <div className="brand-tag">แผนที่หลักสูตร</div>
        </div>
        <nav className="mode-switch">
          <span className="mode-pill active">แผนที่หลักสูตร</span>
          <Link className="mode-pill" href="/timetable">จัดตารางเรียน</Link>
        </nav>
      </div>

      <div className="topbar-center">
        {plan && (
          <button
            className="plan-summary"
            onClick={onOpenPicker}
            title={summary}
          >
            <span className="plan-summary-text">{summary}</span>
            <span className="plan-summary-change">
              เปลี่ยน <span aria-hidden="true">▾</span>
            </span>
          </button>
        )}
      </div>

      <div className="topbar-tools">
        <a
          className="tool-btn link-btn"
          href="https://ursa2.bu.ac.th/seat/seat1.cfm"
          target="_blank"
          rel="noopener noreferrer"
        >
          ดูรายวิชาที่เปิดสอน
        </a>
        <a
          className="tool-btn link-btn"
          href="https://registration.bu.ac.th/thai/free-elective-courses"
          target="_blank"
          rel="noopener noreferrer"
        >
          วิชาเสรีที่เปิด
        </a>
        {plan && (
          <>
            <div className="meta">
              <div className="pill">
                <strong>{activeCredits}</strong> หน่วยกิต
              </div>
              <div className="pill">
                <strong>{activeCount}</strong>/{totalCount} วิชา
              </div>
              {withdrawnCount > 0 && (
                <div
                  className="pill"
                  style={{
                    background: "rgba(224,49,49,0.10)",
                    borderColor: "var(--red)",
                    color: "var(--red)"
                  }}
                >
                  ถอน <strong>{withdrawnCount}</strong> วิชา
                </div>
              )}
            </div>
            <button className="tool-btn" onClick={onReset}>
              ล้างค่า
            </button>
          </>
        )}
      </div>
    </header>
  );
}
