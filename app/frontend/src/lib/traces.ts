import fs from "fs";
import path from "path";

export interface Call {
  id: string;
  ts: string;
  skill: string;
  version: string;
  provider: string;
  model: string;
  ms: number;
  tin: number;
  tout: number;
  cost: number;
  priced: boolean;
  status: string;
  attempts: number;
  error: string | null;
}

export interface Example extends Call {
  request: string;
  response: string;
}

export interface EvalRow {
  skill: string;
  version: string;
  provider: string | null;
  model: string | null;
  metrics: Record<string, number>;
}

export interface Filters {
  skill: string | null;
  version: string | null;
  provider: string | null;
  model: string | null;
  status: string | null;
}

export const FILTER_KEYS = ["skill", "version", "provider", "model", "status"] as const;
export type FilterKey = (typeof FILTER_KEYS)[number];

function readJson<T>(name: string): T {
  return JSON.parse(fs.readFileSync(path.join(process.cwd(), "data", name), "utf-8"));
}

export function loadCalls(): Call[] {
  // newest first
  return readJson<Call[]>("trace_calls.json").slice().reverse();
}
export const loadExamples = () => readJson<Example[]>("trace_examples.json");
export const loadEvals = () => readJson<EvalRow[]>("eval_summary.json");

export function options(calls: Call[], key: FilterKey): { value: string; count: number }[] {
  const counts = new Map<string, number>();
  calls.forEach((c) => counts.set(c[key], (counts.get(c[key]) ?? 0) + 1));
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([value, count]) => ({ value, count }));
}

// only values that exist in the data are accepted, anything else is ignored
export function parseFilters(params: Record<string, string | string[] | undefined>, calls: Call[]): Filters {
  const out = {} as Filters;
  for (const key of FILTER_KEYS) {
    const raw = typeof params[key] === "string" ? (params[key] as string) : null;
    out[key] = raw && calls.some((c) => c[key] === raw) ? raw : null;
  }
  return out;
}

export function applyFilters(calls: Call[], f: Filters): Call[] {
  return calls.filter((c) => FILTER_KEYS.every((k) => !f[k] || c[k] === f[k]));
}

export function summarize(calls: Call[]) {
  const n = calls.length;
  const ok = calls.filter((c) => c.status === "success").length;
  const sum = (fn: (c: Call) => number) => calls.reduce((a, c) => a + fn(c), 0);
  return {
    n,
    ok,
    failed: n - ok,
    cost: sum((c) => c.cost),
    avgMs: n ? sum((c) => c.ms) / n : 0,
    avgIn: n ? sum((c) => c.tin) / n : 0,
    avgOut: n ? sum((c) => c.tout) / n : 0,
    avgCost: n ? sum((c) => c.cost) / n : 0,
    successRate: n ? (ok / n) * 100 : 0,
  };
}

export function bySkillVersion(calls: Call[]) {
  const groups = new Map<string, Call[]>();
  calls.forEach((c) => {
    const k = `${c.skill}|${c.version}`;
    groups.set(k, [...(groups.get(k) ?? []), c]);
  });
  return [...groups.entries()]
    .map(([k, list]) => {
      const [skill, version] = k.split("|");
      return { skill, version, models: [...new Set(list.map((c) => c.model))], ...summarize(list) };
    })
    .sort((a, b) => a.skill.localeCompare(b.skill) || a.version.localeCompare(b.version));
}
