import type { CourseNode, PrereqEdge } from "./types";

export function buildEdges(courses: CourseNode[]): {
  edges: PrereqEdge[];
  byCode: Map<string, CourseNode>;
} {
  const byCode = new Map<string, CourseNode>();
  for (const c of courses) {
    if (c.codeNorm && !byCode.has(c.codeNorm)) byCode.set(c.codeNorm, c);
  }
  const edges: PrereqEdge[] = [];
  for (const c of courses) {
    c.preClauses.forEach((cl, ci) => {
      for (const code of cl.codes) {
        const from = byCode.get(code);
        if (from && from.id !== c.id) {
          edges.push({
            from,
            to: c,
            kind: cl.kind,
            clauseIdx: ci,
            altCount: cl.codes.length
          });
        }
      }
    });
  }
  return { edges, byCode };
}

export function buildAdjacency(edges: PrereqEdge[]) {
  const out = new Map<string, string[]>();
  const inn = new Map<string, string[]>();
  for (const e of edges) {
    if (!out.has(e.from.id)) out.set(e.from.id, []);
    out.get(e.from.id)!.push(e.to.id);
    if (!inn.has(e.to.id)) inn.set(e.to.id, []);
    inn.get(e.to.id)!.push(e.from.id);
  }
  return { out, inn };
}

export function bfs(startId: string, adj: Map<string, string[]>): Set<string> {
  const seen = new Set<string>();
  const q: string[] = [startId];
  while (q.length) {
    const id = q.shift()!;
    const next = adj.get(id) || [];
    for (const n of next) {
      if (!seen.has(n)) { seen.add(n); q.push(n); }
    }
  }
  return seen;
}

/** Compute set of courses that cannot be taken because at least one of their
 *  prereq clauses has no remaining alternative. Iterates to fixed point so the
 *  cascade goes all the way down the chain. */
export function computeUnavailable(
  courses: CourseNode[],
  withdrawn: Set<string>
): Set<string> {
  const codeToId = new Map<string, string>();
  for (const c of courses) if (c.codeNorm) codeToId.set(c.codeNorm, c.id);

  const unavail = new Set<string>(withdrawn);
  let changed = true;
  while (changed) {
    changed = false;
    for (const c of courses) {
      if (unavail.has(c.id)) continue;
      if (c.preClauses.length === 0) continue;
      let cantSatisfy = false;
      for (const cl of c.preClauses) {
        let anyAvailable = false;
        let anyKnown = false;
        for (const code of cl.codes) {
          const altId = codeToId.get(code);
          if (!altId) continue;          // off-plan code — ignore
          anyKnown = true;
          if (!unavail.has(altId)) { anyAvailable = true; break; }
        }
        // If the clause has no in-plan codes, treat it as satisfied
        // (the API is the source of truth; we don't penalize unknown codes).
        if (anyKnown && !anyAvailable) { cantSatisfy = true; break; }
      }
      if (cantSatisfy) {
        unavail.add(c.id);
        changed = true;
      }
    }
  }
  return unavail;
}

/** A course "violates placement" if for at least one of its clauses, no
 *  alternative satisfies the temporal constraint (pass: alt strictly earlier;
 *  concurrent: alt earlier-or-same). */
export function computeViolations(
  courses: CourseNode[],
  manualMoves: Map<string, { yearIdx: number; semIdx: number }>
): Set<string> {
  const codeToId = new Map<string, string>();
  for (const c of courses) if (c.codeNorm) codeToId.set(c.codeNorm, c.id);
  const courseById = new Map(courses.map((c) => [c.id, c]));
  const order = (c: CourseNode) => {
    const m = manualMoves.get(c.id);
    const yi = m ? m.yearIdx : c.yearIdx;
    const si = m ? m.semIdx : c.semIdx;
    return yi * 10 + si;
  };
  const viol = new Set<string>();
  for (const c of courses) {
    if (c.preClauses.length === 0) continue;
    const cOrder = order(c);
    for (const cl of c.preClauses) {
      let anyOk = false;
      let anyKnown = false;
      for (const code of cl.codes) {
        const altId = codeToId.get(code);
        if (!altId) continue;
        anyKnown = true;
        const alt = courseById.get(altId)!;
        const aOrder = order(alt);
        const ok = cl.kind === "pass" ? aOrder < cOrder : aOrder <= cOrder;
        if (ok) { anyOk = true; break; }
      }
      if (anyKnown && !anyOk) { viol.add(c.id); break; }
    }
  }
  return viol;
}
