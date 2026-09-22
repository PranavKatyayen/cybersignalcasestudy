import Link from "next/link";
import { query } from "@/lib/snowflake";
import { parseJsonArray } from "@/lib/parse";
import { TierBadge, ConfidenceBadge } from "@/components/TierBadge";
import { StatCard } from "@/components/StatCard";
import { Pager, parsePaging } from "@/components/Pager";
import { knownCountries } from "@/lib/chat";
import { accountWhere, parseAccountFilters, toQueryString } from "@/lib/accounts";
import { AlertIcon, LayersIcon, GlobeIcon } from "@/components/icons";
import { CHIP_STYLES, describeFindings } from "@/lib/findings";
import type { ProspectAccountRow, PriorityTier } from "@/lib/types";

// ISR: re-query Snowflake at most once every 60s rather than on every request
export const revalidate = 60;

const TIERS: PriorityTier[] = ["CRITICAL", "HIGH", "MEDIUM", "LOW"];
const PAGE_SIZES = [10, 20, 50, 100];

const TIER_PILL_ACTIVE: Record<PriorityTier, string> = {
  CRITICAL: "bg-red-600 border-red-600 text-white",
  HIGH: "bg-orange-500 border-orange-500 text-white",
  MEDIUM: "bg-amber-500 border-amber-500 text-white",
  LOW: "bg-slate-500 border-slate-500 text-white",
};

export default async function DashboardPage({
  searchParams,
}: PageProps<"/">) {
  const params = await searchParams;
  const countries = await knownCountries();
  const filters = parseAccountFilters(params, countries);
  const tierFilter = filters.tier;
  const { size, page: requestedPage } = parsePaging(params, PAGE_SIZES, 20);
  const anyFilter = Boolean(filters.q || filters.country || filters.confidence || filters.tier);

  // tier pill counts follow the other filters (search, country, confidence) but not the tier itself
  const scope = accountWhere(filters, ["tier"]);
  const counts = await query<{ PRIORITY_TIER: PriorityTier; C: number }>(
    `SELECT priority_tier, COUNT(*) as c FROM mart_prospect_accounts ${scope.sql} GROUP BY priority_tier`,
    scope.binds
  );
  const countByTier = Object.fromEntries(counts.map((r) => [r.PRIORITY_TIER, r.C]));
  const scopeTotal = Object.values(countByTier).reduce((a, b) => a + b, 0);
  const filteredTotal = tierFilter ? countByTier[tierFilter] ?? 0 : scopeTotal;

  const pages = Math.max(1, Math.ceil(filteredTotal / size));
  const page = Math.min(requestedPage, pages);
  const offset = (page - 1) * size; // size and page are validated integers

  const full = accountWhere(filters);
  const rows = await query<ProspectAccountRow>(
    `SELECT * FROM mart_prospect_accounts ${full.sql} ORDER BY priority_rank LIMIT ${size} OFFSET ${offset}`,
    full.binds
  );

  const allCounts = await query<{ C: number; A: number }>(`SELECT COUNT(*) AS c, SUM(asset_count) AS a FROM mart_prospect_accounts`);
  const totalAssets = Number(allCounts[0]?.A ?? 0);
  const totalCount = Number(allCounts[0]?.C ?? 0);
  const critical = await query<{ C: number }>(`SELECT COUNT(*) AS c FROM mart_prospect_accounts WHERE priority_tier = 'CRITICAL'`);
  const uniqueCountries = countries.length;
  const tierHref = (tier: string | null) => {
    const qs = toQueryString({ ...filters, tier }, { size: size !== 20 ? size : null });
    return qs ? `/?${qs}` : "/";
  };
  const exportHref = `/api/export?${toQueryString(filters)}`;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <header className="mb-8">
        <h1 className="text-[26px] font-bold tracking-tight text-slate-900">Prospect intelligence</h1>
        <p className="mt-1.5 max-w-2xl text-[15px] text-slate-500">
          Accounts ranked by real, evidence-backed external security exposure &mdash; every score traces back
          to a CVE, an open port, or another verifiable finding, not a guess.
        </p>
      </header>

      <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Attributed accounts" value={totalCount.toLocaleString()} accent="#4f46e5" icon={<LayersIcon className="h-4.5 w-4.5" />} />
        <StatCard label="Critical priority" value={Number(critical[0]?.C ?? 0)} accent="#ef4444" icon={<AlertIcon className="h-4.5 w-4.5" />} />
        <StatCard label="Scored assets" value={totalAssets.toLocaleString()} accent="#0891b2" icon={<LayersIcon className="h-4.5 w-4.5" />} />
        <StatCard label="Countries observed" value={uniqueCountries} accent="#64748b" icon={<GlobeIcon className="h-4.5 w-4.5" />} />
      </div>

      <form method="get" action="/" className="surface-card mb-4 flex flex-wrap items-end gap-3 px-4 py-3.5">
        <label className="flex min-w-[14rem] flex-1 flex-col gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Search
          <input
            name="q"
            defaultValue={filters.q ?? ""}
            maxLength={60}
            placeholder="Account or finding, e.g. nginx or CVE-2023"
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-normal normal-case tracking-normal text-slate-700 outline-none focus:border-indigo-400"
          />
        </label>
        <label className="flex flex-col gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Country
          <select
            name="country"
            defaultValue={filters.country ?? ""}
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-normal normal-case tracking-normal text-slate-700"
          >
            <option value="">All countries</option>
            {countries.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Confidence
          <select
            name="confidence"
            defaultValue={filters.confidence ?? ""}
            className="rounded-md border border-slate-200 bg-white px-3 py-1.5 text-sm font-normal normal-case tracking-normal text-slate-700"
          >
            <option value="">Any</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
          </select>
        </label>
        {tierFilter && <input type="hidden" name="tier" value={tierFilter} />}
        {size !== 20 && <input type="hidden" name="size" value={size} />}
        <button type="submit" className="rounded-md bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700">
          Apply
        </button>
        {anyFilter && (
          <Link href="/" className="py-1.5 text-sm font-medium text-slate-500 hover:text-indigo-600">
            Clear
          </Link>
        )}
        <a
          href={exportHref}
          className="ml-auto rounded-md border border-slate-200 bg-white px-3.5 py-1.5 text-sm font-medium text-slate-600 hover:border-slate-300 hover:bg-slate-50"
        >
          Export CSV
        </a>
      </form>

      <div className="mb-5 flex flex-wrap items-center gap-2">
        <Link
          href={tierHref(null)}
          className={`rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors ${
            !tierFilter
              ? "border-slate-900 bg-slate-900 text-white"
              : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
          }`}
        >
          All <span className="opacity-70">({scopeTotal})</span>
        </Link>
        {TIERS.map((tier) => (
          <Link
            key={tier}
            href={tierHref(tier)}
            className={`rounded-full border px-3.5 py-1.5 text-sm font-medium transition-colors ${
              tierFilter === tier
                ? TIER_PILL_ACTIVE[tier]
                : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
            }`}
          >
            {tier} <span className="opacity-70">({countByTier[tier] ?? 0})</span>
          </Link>
        ))}
      </div>

      <p className="mb-3 text-[13px] leading-relaxed text-slate-500">
        <strong className="font-semibold text-slate-600">How to read this list:</strong> the score adds points for each
        verified weakness (fixed rules, not AI). Priority bands: CRITICAL 100+, HIGH 40&ndash;99, MEDIUM 20&ndash;39, LOW
        under 20. <em>HIGH confidence</em> means we saw the business&apos;s own website; <em>MEDIUM</em> means it was matched by
        organization name only. Hover a tag for what it means.
      </p>

      <div className="mb-3">
        <Pager basePath="/" extra={{ tier: tierFilter, q: filters.q, country: filters.country, confidence: filters.confidence }} page={page} size={size} total={filteredTotal} sizes={PAGE_SIZES} noun="accounts" />
      </div>

      <div className="surface-card overflow-hidden">
        <table className="min-w-full">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50/60">
              <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">Rank</th>
              <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">Account</th>
              <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">Priority</th>
              <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400" title="Points for every verified weakness. Fixed rules, not AI.">Score</th>
              <th className="px-4 py-3 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">Why it is on the list</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((row) => {
              const countries = parseJsonArray(row.COUNTRIES);
              const chips = describeFindings(parseJsonArray(row.TOP_FINDINGS));
              const shown = chips.slice(0, 3);
              const opener = row.NARRATIVE_OUTREACH_ANGLE;
              const systems = row.ASSET_COUNT;
              return (
                <tr key={row.ENTITY_KEY} className="align-top transition-colors hover:bg-indigo-50/30">
                  <td className="px-4 py-4 text-sm font-medium text-slate-400">#{row.PRIORITY_RANK}</td>
                  <td className="px-4 py-4">
                    <Link
                      href={`/accounts/${encodeURIComponent(row.ENTITY_KEY)}`}
                      className="font-semibold text-slate-900 hover:text-indigo-600"
                    >
                      {row.ENTITY_KEY}
                    </Link>
                    <div className="mt-1 text-xs text-slate-500">
                      {countries.length > 0 ? countries[0] : "Country unknown"} &middot; {systems} exposed {systems === 1 ? "system" : "systems"}
                    </div>
                    <div className="mt-1.5">
                      <ConfidenceBadge confidence={row.ATTRIBUTION_CONFIDENCE} />
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <TierBadge tier={row.PRIORITY_TIER} />
                  </td>
                  <td className="px-4 py-4">
                    <div className="text-base font-bold text-slate-900">{row.TOTAL_SCORE}</div>
                    <div className="mt-1.5 h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.min(100, (row.TOTAL_SCORE / 300) * 100)}%`,
                          background: `var(--tier-${row.PRIORITY_TIER.toLowerCase()}-dot)`,
                        }}
                      />
                    </div>
                  </td>
                  <td className="max-w-md px-4 py-4">
                    <div className="flex flex-wrap gap-1.5">
                      {shown.map((c) => (
                        <span
                          key={c.label}
                          title={c.detail}
                          className={`inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium ${CHIP_STYLES[c.severity]}`}
                        >
                          {c.label}
                        </span>
                      ))}
                      {chips.length > shown.length && (
                        <span className="px-1 py-0.5 text-xs text-slate-400">+{chips.length - shown.length} more</span>
                      )}
                    </div>
                    {opener && (
                      <p className="mt-2 line-clamp-2 text-[13px] leading-snug text-slate-500">
                        <span className="font-semibold text-slate-600">Open with: </span>
                        {opener}
                      </p>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {rows.length === 0 && (
        <p className="mt-6 text-center text-sm text-slate-500">No accounts match this filter.</p>
      )}

      <div className="mt-4">
        <Pager basePath="/" extra={{ tier: tierFilter, q: filters.q, country: filters.country, confidence: filters.confidence }} page={page} size={size} total={filteredTotal} sizes={PAGE_SIZES} noun="accounts" />
      </div>
    </main>
  );
}
