import Link from "next/link";
import { query } from "@/lib/snowflake";
import { parseJsonArray, parseJsonObject } from "@/lib/parse";
import { TierBadge } from "@/components/TierBadge";
import { StatCard } from "@/components/StatCard";
import { Pager, parsePaging } from "@/components/Pager";
import { LayersIcon, GlobeIcon, AlertIcon } from "@/components/icons";
import { CATEGORY_ORDER, categoryStyle, getCatalog, parseTechFilters, profileWhere, techQueryString } from "@/lib/tech";
import type { PriorityTier } from "@/lib/types";

export const revalidate = 60;

const PAGE_SIZES = [10, 20, 50, 100];
const input = "rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-normal normal-case tracking-normal text-slate-700";
const label = "flex flex-col gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400";

async function safe<T>(run: () => Promise<T>, fallback: T): Promise<T> {
  try {
    return await run();
  } catch {
    return fallback;
  }
}

function Chip({ name, category }: { name: string; category: string }) {
  return <span className={`inline-flex rounded-md border px-2 py-0.5 text-xs font-medium ${categoryStyle(category)}`}>{name}</span>;
}

export default async function TechnologiesPage({ searchParams }: PageProps<"/technologies">) {
  const params = await searchParams;

  const countryRows = await safe(
    () => query<{ C: string }>(`SELECT DISTINCT f.value::string AS c FROM mart_account_tech_profile, LATERAL FLATTEN(input => countries) f ORDER BY 1`),
    []
  );
  const countries = countryRows.map((r) => r.C);
  const filters = parseTechFilters(params, countries);
  const { size, page: requestedPage } = parsePaging(params, PAGE_SIZES, 20);

  const overview = await safe(
    () => query<{ ACCOUNTS: number; RANKED: number }>(`SELECT COUNT(*) AS accounts, COUNT_IF(is_ranked) AS ranked FROM mart_account_tech_profile`),
    []
  );
  const catalogTotals = await safe(
    () => query<{ TECHS: number; CATS: number }>(`SELECT COUNT(*) AS techs, COUNT(DISTINCT category) AS cats FROM mart_technology_catalog`),
    []
  );
  const catalog = await getCatalog({ limit: 150 });
  const top = catalog.slice(0, 16);

  const where = profileWhere(filters);
  const totalRows = await safe(() => query<{ N: number }>(`SELECT COUNT(*) AS n FROM mart_account_tech_profile ${where.sql}`, where.binds), []);
  const total = Number(totalRows[0]?.N ?? 0);
  const pages = Math.max(1, Math.ceil(total / size));
  const page = Math.min(requestedPage, pages);
  const rows = await safe(
    () =>
      query<Record<string, unknown>>(
        `SELECT entity_key, tech_count, category_count, technologies, tech_by_category, asset_count, countries,
                is_ranked, priority_tier, priority_rank, total_score
         FROM mart_account_tech_profile ${where.sql}
         ORDER BY is_ranked DESC, priority_rank ASC NULLS LAST, tech_count DESC, entity_key
         LIMIT ${size} OFFSET ${(page - 1) * size}`, // size and page are validated integers
        where.binds
      ),
    []
  );

  const anyFilter = Boolean(filters.tech || filters.category || filters.q || filters.country || filters.scope === "ranked");
  const accounts = Number(overview[0]?.ACCOUNTS ?? 0);
  const ranked = Number(overview[0]?.RANKED ?? 0);
  const href = (over: Partial<typeof filters>) => {
    const qs = techQueryString({ ...filters, ...over }, { size: size !== 20 ? size : null });
    return qs ? `/technologies?${qs}` : "/technologies";
  };

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-[26px] font-bold tracking-tight text-slate-900">Technologies</h1>
        <p className="mt-1.5 max-w-3xl text-[15px] text-slate-500">
          What each account runs, read from the same scan: cloud, web servers, CDNs, frameworks, operating systems and more. It
          covers every account where the scan showed a business website, including {(accounts - ranked).toLocaleString()} that have no
          security findings and so are not in the ranked list. Found by fixed rules, not AI.
        </p>
      </header>

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Accounts with technology data" value={accounts.toLocaleString()} accent="#4f46e5" icon={<LayersIcon className="h-4.5 w-4.5" />} />
        <StatCard label="Also in the ranked list" value={ranked.toLocaleString()} accent="#ef4444" icon={<AlertIcon className="h-4.5 w-4.5" />} />
        <StatCard label="Technologies identified" value={Number(catalogTotals[0]?.TECHS ?? 0).toLocaleString()} accent="#0891b2" icon={<LayersIcon className="h-4.5 w-4.5" />} />
        <StatCard label="Categories" value={Number(catalogTotals[0]?.CATS ?? 0)} accent="#64748b" icon={<GlobeIcon className="h-4.5 w-4.5" />} />
      </div>

      {top.length > 0 && (
        <section className="mb-6">
          <h2 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Most common technologies</h2>
          <div className="flex flex-wrap gap-1.5">
            {top.map((t) => (
              <Link
                key={t.technology}
                href={href({ tech: filters.tech === t.technology ? null : t.technology })}
                className={`rounded-md border px-2.5 py-1 text-sm font-medium transition-opacity hover:opacity-80 ${categoryStyle(t.category)} ${
                  filters.tech === t.technology ? "ring-2 ring-indigo-500" : ""
                }`}
              >
                {t.technology} <span className="opacity-70">({t.accounts.toLocaleString()})</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      <form method="get" action="/technologies" className="surface-card mb-4 flex flex-wrap items-end gap-3 px-4 py-3.5">
        <label className={`${label} min-w-[12rem] flex-1`}>
          Search account
          <input name="q" defaultValue={filters.q ?? ""} maxLength={60} placeholder="e.g. duolingo" className={input} />
        </label>
        <label className={label}>
          Technology
          <select name="tech" defaultValue={filters.tech ?? ""} className={input}>
            <option value="">Any</option>
            {catalog
              .slice()
              .sort((a, b) => a.technology.localeCompare(b.technology))
              .map((t) => (
                <option key={t.technology} value={t.technology}>{t.technology} ({t.accounts})</option>
              ))}
          </select>
        </label>
        <label className={label}>
          Category
          <select name="category" defaultValue={filters.category ?? ""} className={input}>
            <option value="">Any</option>
            {CATEGORY_ORDER.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className={label}>
          Country
          <select name="country" defaultValue={filters.country ?? ""} className={input}>
            <option value="">Any</option>
            {countries.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className={label}>
          Show
          <select name="scope" defaultValue={filters.scope} className={input}>
            <option value="all">All accounts</option>
            <option value="ranked">Only ranked accounts</option>
          </select>
        </label>
        {size !== 20 && <input type="hidden" name="size" value={size} />}
        <button type="submit" className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">Apply</button>
        {anyFilter && <Link href="/technologies" className="py-1.5 text-sm font-medium text-slate-500 hover:text-indigo-600">Clear</Link>}
      </form>

      <div className="mb-3">
        <Pager
          basePath="/technologies"
          extra={{ tech: filters.tech, category: filters.category, q: filters.q, country: filters.country, scope: filters.scope === "ranked" ? "ranked" : null }}
          page={page}
          size={size}
          total={total}
          sizes={PAGE_SIZES}
          noun="accounts"
        />
      </div>

      <div className="surface-card overflow-hidden">
        <table className="min-w-full">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50/60">
              <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">Account</th>
              <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">Security exposure</th>
              <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">Technologies seen</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row) => {
              const key = String(row.ENTITY_KEY);
              const technologies = parseJsonArray(row.TECHNOLOGIES);
              const byCategory = parseJsonObject(row.TECH_BY_CATEGORY);
              const categoryOf = new Map<string, string>();
              Object.entries(byCategory).forEach(([category, names]) => names.forEach((n) => categoryOf.set(n, category)));
              const rowCountries = parseJsonArray(row.COUNTRIES);
              const isRanked = row.IS_RANKED === true || row.IS_RANKED === "true";
              const shown = technologies.slice(0, 8);
              return (
                <tr key={key} className="align-top transition-colors hover:bg-indigo-50/30">
                  <td className="px-4 py-4">
                    {isRanked ? (
                      <Link href={`/accounts/${encodeURIComponent(key)}`} className="font-semibold text-slate-900 hover:text-indigo-600">{key}</Link>
                    ) : (
                      <span className="font-semibold text-slate-900">{key}</span>
                    )}
                    <div className="mt-1 text-xs text-slate-500">
                      {rowCountries[0] ?? "Country unknown"} &middot; {Number(row.ASSET_COUNT)} system{Number(row.ASSET_COUNT) === 1 ? "" : "s"} seen
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    {isRanked ? (
                      <div className="space-y-1.5">
                        <TierBadge tier={row.PRIORITY_TIER as PriorityTier} />
                        <div className="text-xs text-slate-500">Score {Number(row.TOTAL_SCORE)} &middot; rank #{Number(row.PRIORITY_RANK)}</div>
                      </div>
                    ) : (
                      <span className="text-xs text-slate-400">No findings in this scan</span>
                    )}
                  </td>
                  <td className="max-w-xl px-4 py-4">
                    <div className="flex flex-wrap gap-1.5">
                      {shown.map((name) => (
                        <Chip key={name} name={name} category={categoryOf.get(name) ?? "Other"} />
                      ))}
                    </div>
                    {technologies.length > shown.length && (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-xs font-medium text-indigo-600">
                          All {technologies.length} technologies in {Number(row.CATEGORY_COUNT)} categories
                        </summary>
                        <div className="mt-2 space-y-2">
                          {CATEGORY_ORDER.filter((c) => byCategory[c]).map((c) => (
                            <div key={c}>
                              <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{c}</div>
                              <div className="flex flex-wrap gap-1.5">
                                {byCategory[c].map((name) => (
                                  <Chip key={name} name={name} category={c} />
                                ))}
                              </div>
                            </div>
                          ))}
                        </div>
                      </details>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {rows.length === 0 && <p className="mt-6 text-center text-sm text-slate-500">No accounts match these filters.</p>}

      <div className="mt-4">
        <Pager
          basePath="/technologies"
          extra={{ tech: filters.tech, category: filters.category, q: filters.q, country: filters.country, scope: filters.scope === "ranked" ? "ranked" : null }}
          page={page}
          size={size}
          total={total}
          sizes={PAGE_SIZES}
          noun="accounts"
        />
      </div>
    </main>
  );
}
