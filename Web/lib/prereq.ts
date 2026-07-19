/**
 * Prereq strings come in Thai with two semantic kinds:
 *
 *   "สอบได้ CS102"                         → must-pass: CS102 in earlier semester
 *   "สอบได้ CS 454 และ CS 448"             → must-pass: BOTH (AND)
 *   "สอบได้ EL 214 หรือ EL 216"            → must-pass: EITHER (OR alternatives)
 *   "สอบได้ EL 331 หรือเรียนควบคู่กัน"      → must-pass OR taken concurrently
 *   "EE 312 หรือ เรียน ควบคู่กัน"           → (สอบได้ implicit) pass-or-concurrent
 *   "เคยเรียน IEN 108"                       → previously taken (a grade of F is allowed)
 *
 * "และ" = AND  → splits into separate clauses (all required)
 * "หรือ" between codes = OR alternatives (any one satisfies the clause)
 * "ควบคู่" / "เรียนควบคู่กัน" = concurrent modifier for its own clause.
 * For example, "สอบได้ MK 101 และ BA 207 หรือเรียนควบคู่กัน" means
 * MK 101 must be passed, while BA 207 may be passed or taken in parallel.
 */

export type PrereqKind = "pass" | "concurrent" | "taken";

export interface PrereqClause {
  /** Course codes that satisfy this clause (alternatives via หรือ). */
  codes: string[];
  /** Whether it must be passed, previously taken, or may be taken concurrently. */
  kind: PrereqKind;
}

export function normalizeCode(raw: string | null | undefined): string | null {
  if (!raw) return null;
  return raw.replace(/\s+/g, "").toUpperCase();
}

function extractCodes(s: string): string[] {
  // Letters: 1–3 uppercase letters with possible internal spaces ("C S389" → CS389)
  // Digits: 3–4 digits with possible internal spaces ("CE 3 34" → CE334)
  const re = /([A-Z](?:\s*[A-Z]){0,3})\s*(\d(?:\s*\d){2,3})/g;
  const upper = s.toUpperCase();
  const out: string[] = [];
  let m: RegExpExecArray | null;
  while ((m = re.exec(upper)) !== null) {
    const letters = m[1].replace(/\s+/g, "");
    const digits = m[2].replace(/\s+/g, "");
    out.push(letters + digits);
  }
  return out;
}

export function parsePrereqClauses(
  raw: string | null | undefined
): PrereqClause[] {
  if (!raw) return [];
  const trimmed = raw.trim();
  if (!trimmed || trimmed === "-" || trimmed === "—") return [];

  // Split first: "และ" creates independent requirements, and a parallel
  // modifier applies only to the requirement it appears with.
  const andParts = trimmed.split(/และ/);
  const clauses: PrereqClause[] = [];

  for (const rawPart of andParts) {
    const kind: PrereqKind = /ควบ\s*คู่/.test(rawPart)
      ? "concurrent"
      : /เคยเรียน|previously\s+taken|previously\s+enrolled/i.test(rawPart)
        ? "taken"
        : "pass";
    const part = rawPart
      .replace(/(หรือ\s*)?(เรียน\s*)?ควบ\s*คู่กัน?/g, " ")
      .replace(/(หรือ\s*)?(เรียน\s*)?ควบ\s*คู่/g, " ")
      .replace(/สอบได้/g, " ")
      .replace(/^\s*ผ่าน/, " ")
      .trim();
    // Codes inside an AND-part are alternatives (often joined by หรือ; even when
    // หรือ is missing we treat sibling codes as alternatives — the safer default).
    const codes = extractCodes(part);
    if (codes.length === 0) continue;
    const seen = new Set<string>();
    const uniq: string[] = [];
    for (const c of codes) if (!seen.has(c)) { seen.add(c); uniq.push(c); }
    clauses.push({ codes: uniq, kind });
  }

  return clauses;
}

/** Flat list of every code referenced (any kind, any clause). Kept for callers
 *  that just need a list of codes. */
export function parsePrereqs(raw: string | null | undefined): string[] {
  const out: string[] = [];
  for (const cl of parsePrereqClauses(raw)) for (const c of cl.codes) out.push(c);
  return out;
}
