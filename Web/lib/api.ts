import type { DegreePlanLookupResponse, DegreePlanQuery } from "./types";

// Same-origin by default: the FastAPI backend serves this static build and the
// API under /api/v1. Override at build time with NEXT_PUBLIC_API_BASE for a
// split deployment (e.g. "https://bu.need.cat/api/v1").
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api/v1";

export async function fetchDegreePlan(
  partial: Partial<DegreePlanQuery>
): Promise<DegreePlanLookupResponse> {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(partial)) {
    if (v) params.set(k, v as string);
  }
  const url = `${API_BASE}/degree-plan${
    params.toString() ? "?" + params.toString() : ""
  }`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}
