import { matchCountry } from "@/lib/filters";

export const ACCOUNT_TIERS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;

export interface AccountFilters {
  tier: string | null;
  q: string | null;
  country: string | null;
  confidence: "HIGH" | "MEDIUM" | null;
}

type Params = Record<string, string | string[] | undefined>;
const one = (v: string | string[] | undefined) => (typeof v === "string" ? v : null);

export function parseAccountFilters(params: Params, countries: string[]): AccountFilters {
  const tier = one(params.tier)?.toUpperCase() ?? null;
  const conf = one(params.confidence)?.toUpperCase() ?? null;
  const country = one(params.country);
  const q = one(params.q)?.trim().slice(0, 60) || null;
  return {
    tier: tier && (ACCOUNT_TIERS as readonly string[]).includes(tier) ? tier : null,
    q,
    country: country ? matchCountry(country, countries) : null,
    confidence: conf === "HIGH" || conf === "MEDIUM" ? conf : null,
  };
}

// Builds a WHERE clause with bound parameters only; nothing from the user is put into the SQL text.
export function accountWhere(f: AccountFilters, skip: (keyof AccountFilters)[] = []) {
  const where: string[] = [];
  const binds: (string | number)[] = [];
  if (f.tier && !skip.includes("tier")) {
    where.push("priority_tier = ?");
    binds.push(f.tier);
  }
  if (f.confidence && !skip.includes("confidence")) {
    where.push("attribution_confidence = ?");
    binds.push(f.confidence);
  }
  if (f.country && !skip.includes("country")) {
    where.push("ARRAY_CONTAINS(TO_VARIANT(?), countries)");
    binds.push(f.country);
  }
  if (f.q && !skip.includes("q")) {
    const like = `%${f.q.toLowerCase().replace(/[%_]/g, "")}%`;
    where.push("(LOWER(entity_key) LIKE ? OR LOWER(headline_finding) LIKE ?)");
    binds.push(like, like);
  }
  return { sql: where.length ? `WHERE ${where.join(" AND ")}` : "", binds };
}

export function toQueryString(f: AccountFilters, extra: Record<string, string | number | null> = {}) {
  const q = new URLSearchParams();
  (Object.keys(f) as (keyof AccountFilters)[]).forEach((k) => f[k] && q.set(k, String(f[k])));
  Object.entries(extra).forEach(([k, v]) => v !== null && q.set(k, String(v)));
  return q.toString();
}
