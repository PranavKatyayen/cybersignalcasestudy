import { query } from "@/lib/snowflake";
import { parseJsonArray } from "@/lib/parse";

// Same order as the categories in app/backend/pipeline/tech_rules.json
export const CATEGORY_ORDER = [
  "Cloud & hosting", "CDN & edge", "Web server & proxy", "Load balancer & gateway", "Security",
  "Language & runtime", "Web framework & front-end", "CMS & e-commerce", "Database", "Operating system",
  "Hosting control panel", "Analytics & marketing", "Mail & communications", "Network & remote access",
  "Devices & IoT", "Exposed service type", "Other",
];

// Whole class names so Tailwind can see them
const CATEGORY_STYLE: Record<string, string> = {
  "Cloud & hosting": "border-sky-200 bg-sky-50 text-sky-800",
  "CDN & edge": "border-cyan-200 bg-cyan-50 text-cyan-800",
  "Web server & proxy": "border-indigo-200 bg-indigo-50 text-indigo-800",
  "Load balancer & gateway": "border-violet-200 bg-violet-50 text-violet-800",
  "Security": "border-rose-200 bg-rose-50 text-rose-800",
  "Language & runtime": "border-emerald-200 bg-emerald-50 text-emerald-800",
  "Web framework & front-end": "border-teal-200 bg-teal-50 text-teal-800",
  "CMS & e-commerce": "border-amber-200 bg-amber-50 text-amber-800",
  "Database": "border-orange-200 bg-orange-50 text-orange-800",
  "Operating system": "border-slate-300 bg-slate-100 text-slate-700",
  "Hosting control panel": "border-lime-200 bg-lime-50 text-lime-800",
  "Analytics & marketing": "border-fuchsia-200 bg-fuchsia-50 text-fuchsia-800",
  "Mail & communications": "border-pink-200 bg-pink-50 text-pink-800",
  "Network & remote access": "border-red-200 bg-red-50 text-red-800",
  "Devices & IoT": "border-yellow-200 bg-yellow-50 text-yellow-800",
  "Exposed service type": "border-purple-200 bg-purple-50 text-purple-800",
};
export const categoryStyle = (category: string) => CATEGORY_STYLE[category] ?? "border-slate-200 bg-slate-50 text-slate-600";

export interface AccountTech {
  technology: string;
  category: string;
  vendor: string | null;
  assetCount: number;
  versions: string[];
  sources: string[];
}

export interface TechEvidence {
  technology: string;
  version: string | null;
  source: string;
  signal: string;
  asset: string;
}

export const SOURCE_LABELS: Record<string, string> = {
  component: "web page component",
  cpe: "software identifier (CPE)",
  product: "service banner",
  server_header: "HTTP server header",
  cloud: "cloud IP range",
  hostname: "hostname",
  os: "operating system",
  tag: "scan tag",
};

// These helpers never throw: a missing table or a database error just means the section is not shown.
export async function getAccountTechnologies(entityKey: string): Promise<{ technologies: AccountTech[]; evidence: TechEvidence[] }> {
  try {
    const rows = await query<Record<string, unknown>>(
      `SELECT technology, category, vendor, asset_count, versions, sources
       FROM mart_account_technologies WHERE entity_key = ? ORDER BY asset_count DESC, technology`,
      [entityKey]
    );
    const evidence = await query<Record<string, unknown>>(
      `SELECT technology, version, source, signal, asset_id
       FROM mart_tech_evidence WHERE entity_key = ? ORDER BY technology, source, asset_id LIMIT 400`,
      [entityKey]
    );
    return {
      technologies: rows.map((r) => ({
        technology: String(r.TECHNOLOGY),
        category: String(r.CATEGORY),
        vendor: (r.VENDOR as string) ?? null,
        assetCount: Number(r.ASSET_COUNT),
        versions: parseJsonArray(r.VERSIONS),
        sources: parseJsonArray(r.SOURCES),
      })),
      evidence: evidence.map((r) => ({
        technology: String(r.TECHNOLOGY),
        version: (r.VERSION as string) ?? null,
        source: String(r.SOURCE),
        signal: String(r.SIGNAL),
        asset: String(r.ASSET_ID),
      })),
    };
  } catch {
    return { technologies: [], evidence: [] };
  }
}

export interface CatalogRow {
  technology: string;
  category: string;
  accounts: number;
  rankedAccounts: number;
}

export async function getCatalog(opts: { rankedOnly?: boolean; limit: number }): Promise<CatalogRow[]> {
  try {
    const limit = Math.min(Math.max(Math.floor(opts.limit), 1), 300); // a validated integer
    const rows = await query<Record<string, unknown>>(
      `SELECT technology, category, account_count, ranked_account_count FROM mart_technology_catalog
       ${opts.rankedOnly ? "WHERE ranked_account_count > 0" : ""}
       ORDER BY ${opts.rankedOnly ? "ranked_account_count" : "account_count"} DESC, technology LIMIT ${limit}`
    );
    return rows.map((r) => ({
      technology: String(r.TECHNOLOGY),
      category: String(r.CATEGORY),
      accounts: Number(r.ACCOUNT_COUNT),
      rankedAccounts: Number(r.RANKED_ACCOUNT_COUNT),
    }));
  } catch {
    return [];
  }
}

export interface TechFilters {
  tech: string | null;
  category: string | null;
  q: string | null;
  country: string | null;
  scope: "ranked" | "all";
}

type Params = Record<string, string | string[] | undefined>;
const one = (v: string | string[] | undefined) => (typeof v === "string" ? v : null);

export function parseTechFilters(params: Params, countries: string[]): TechFilters {
  const category = one(params.category);
  const country = one(params.country);
  return {
    tech: one(params.tech)?.trim().slice(0, 80) || null,
    category: category && CATEGORY_ORDER.includes(category) ? category : null,
    q: one(params.q)?.trim().slice(0, 60) || null,
    country: country ? countries.find((c) => c.toLowerCase() === country.toLowerCase()) ?? null : null,
    scope: one(params.scope) === "ranked" ? "ranked" : "all",
  };
}

// Bound parameters only; nothing from the user is put into the SQL text.
export function profileWhere(f: TechFilters) {
  const where: string[] = [];
  const binds: (string | number)[] = [];
  if (f.tech) {
    where.push("ARRAY_CONTAINS(TO_VARIANT(?), technologies)");
    binds.push(f.tech);
  }
  if (f.category) {
    where.push("ARRAY_CONTAINS(TO_VARIANT(?), OBJECT_KEYS(tech_by_category))");
    binds.push(f.category);
  }
  if (f.country) {
    where.push("ARRAY_CONTAINS(TO_VARIANT(?), countries)");
    binds.push(f.country);
  }
  if (f.q) {
    where.push("LOWER(entity_key) LIKE ?");
    binds.push(`%${f.q.toLowerCase().replace(/[%_]/g, "")}%`);
  }
  if (f.scope === "ranked") where.push("is_ranked");
  return { sql: where.length ? `WHERE ${where.join(" AND ")}` : "", binds };
}

export function techQueryString(f: TechFilters, extra: Record<string, string | number | null> = {}) {
  const q = new URLSearchParams();
  if (f.tech) q.set("tech", f.tech);
  if (f.category) q.set("category", f.category);
  if (f.q) q.set("q", f.q);
  if (f.country) q.set("country", f.country);
  if (f.scope === "ranked") q.set("scope", "ranked");
  Object.entries(extra).forEach(([k, v]) => v !== null && q.set(k, String(v)));
  return q.toString();
}
