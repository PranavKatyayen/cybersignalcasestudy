import { query } from "@/lib/snowflake";
import { parseJsonArray } from "@/lib/parse";

import { TIERS, matchCountry, sanitizeFilters, type ChatFilters } from "@/lib/filters";
export { TIERS, matchCountry, sanitizeFilters };
export type { ChatFilters };

export interface AccountRow {
  entity_key: string;
  tier: string;
  rank: number;
  score: number;
  confidence: string;
  headline: string;
  country: string | null;
  brief: string | null;
}

let countryCache: { at: number; list: string[] } | null = null;

export async function knownCountries(): Promise<string[]> {
  if (countryCache && Date.now() - countryCache.at < 10 * 60_000) return countryCache.list;
  const rows = await query<{ COUNTRIES: unknown }>(`SELECT countries FROM mart_prospect_accounts`);
  const set = new Set<string>();
  rows.forEach((r) => parseJsonArray(r.COUNTRIES).forEach((c) => set.add(c)));
  countryCache = { at: Date.now(), list: [...set].sort() };
  return countryCache.list;
}

export async function runAccountSearch(f: ChatFilters): Promise<AccountRow[]> {
  const where: string[] = [];
  const binds: (string | number)[] = [];
  if (f.tiers.length) {
    where.push(`priority_tier IN (${f.tiers.map(() => "?").join(",")})`);
    binds.push(...f.tiers);
  }
  if (f.country) {
    where.push(`ARRAY_CONTAINS(TO_VARIANT(?), countries)`);
    binds.push(f.country);
  }
  if (f.minScore !== null) {
    where.push(`total_score >= ?`);
    binds.push(f.minScore);
  }
  if (f.confidence) {
    where.push(`attribution_confidence = ?`);
    binds.push(f.confidence);
  }
  if (f.text) {
    where.push(`(LOWER(entity_key) LIKE ? OR LOWER(headline_finding) LIKE ?)`);
    const like = `%${f.text.toLowerCase().replace(/[%_]/g, "")}%`;
    binds.push(like, like);
  }
  const sql = `SELECT entity_key, priority_tier, priority_rank, total_score, attribution_confidence,
                      headline_finding, countries, narrative_summary
               FROM mart_prospect_accounts
               ${where.length ? "WHERE " + where.join(" AND ") : ""}
               ORDER BY priority_rank LIMIT ${f.limit}`; // limit is a validated integer 1-10
  const rows = await query<Record<string, unknown>>(sql, binds);
  return rows.map((r) => ({
    entity_key: String(r.ENTITY_KEY),
    tier: String(r.PRIORITY_TIER),
    rank: Number(r.PRIORITY_RANK),
    score: Number(r.TOTAL_SCORE),
    confidence: String(r.ATTRIBUTION_CONFIDENCE),
    headline: String(r.HEADLINE_FINDING ?? ""),
    country: parseJsonArray(r.COUNTRIES)[0] ?? null,
    brief: (r.NARRATIVE_SUMMARY as string) ?? null,
  }));
}

export async function getAccount(entityKey: string): Promise<(AccountRow & { findings: string[] }) | null> {
  const rows = await query<Record<string, unknown>>(
    `SELECT entity_key, priority_tier, priority_rank, total_score, attribution_confidence, headline_finding,
            countries, narrative_summary, top_findings
     FROM mart_prospect_accounts WHERE entity_key = ?`,
    [entityKey]
  );
  const r = rows[0];
  if (!r) return null;
  return {
    entity_key: String(r.ENTITY_KEY),
    tier: String(r.PRIORITY_TIER),
    rank: Number(r.PRIORITY_RANK),
    score: Number(r.TOTAL_SCORE),
    confidence: String(r.ATTRIBUTION_CONFIDENCE),
    headline: String(r.HEADLINE_FINDING ?? ""),
    country: parseJsonArray(r.COUNTRIES)[0] ?? null,
    brief: (r.NARRATIVE_SUMMARY as string) ?? null,
    findings: parseJsonArray(r.TOP_FINDINGS),
  };
}

// Best-effort abuse protection
const hits = new Map<string, number[]>();
let dayCount = { day: new Date().toDateString(), n: 0 };

export function allowRequest(ip: string): { ok: boolean; reason?: string } {
  // local eval runs send many requests in a row; never disabled in production builds
  if (process.env.NODE_ENV !== "production" && process.env.CHAT_DISABLE_RATE_LIMIT === "1") return { ok: true };
  const now = Date.now();
  const today = new Date().toDateString();
  if (dayCount.day !== today) dayCount = { day: today, n: 0 };
  if (dayCount.n >= 400) return { ok: false, reason: "Daily chat capacity reached. Please try again tomorrow." };
  const recent = (hits.get(ip) ?? []).filter((t) => now - t < 10 * 60_000);
  if (recent.length >= 12) return { ok: false, reason: "Too many questions in a short time. Please wait a few minutes." };
  recent.push(now);
  hits.set(ip, recent);
  dayCount.n += 1;
  return { ok: true };
}
