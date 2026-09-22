import Link from "next/link";
import { notFound } from "next/navigation";
import { query } from "@/lib/snowflake";
import { parseJsonArray, parseJsonIntArray } from "@/lib/parse";
import { TierBadge, ConfidenceBadge } from "@/components/TierBadge";
import { ArrowLeftIcon, SparkleIcon } from "@/components/icons";
import type { ProspectAccountRow, AssetEvidenceRow } from "@/lib/types";

export const revalidate = 60;

export default async function AccountDetailPage(
  props: PageProps<"/accounts/[entity_key]">
) {
  const { entity_key } = await props.params;
  const entityKey = decodeURIComponent(entity_key);

  const accounts = await query<ProspectAccountRow>(
    `SELECT * FROM mart_prospect_accounts WHERE entity_key = ?`,
    [entityKey]
  );
  const account = accounts[0];
  if (!account) notFound();

  const assets = await query<AssetEvidenceRow>(
    `SELECT * FROM mart_asset_evidence WHERE entity_key = ? ORDER BY adjusted_score DESC`,
    [entityKey]
  );

  const topFindings = parseJsonArray(account.TOP_FINDINGS);
  const citedIndices = new Set(parseJsonIntArray(account.NARRATIVE_CITED_EVIDENCE_INDICES));
  const orgs = parseJsonArray(account.ORGS);
  const countries = parseJsonArray(account.COUNTRIES);
  const providerRoles = parseJsonArray(account.PROVIDER_ROLES);

  return (
    <main className="mx-auto max-w-4xl px-6 py-10">
      <Link href="/" className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-indigo-600">
        <ArrowLeftIcon className="h-3.5 w-3.5" />
        Back to dashboard
      </Link>

      <header className="mt-5 mb-8">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-[26px] font-bold tracking-tight text-slate-900">{account.ENTITY_KEY}</h1>
          <TierBadge tier={account.PRIORITY_TIER} />
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <ConfidenceBadge confidence={account.ATTRIBUTION_CONFIDENCE} />
          <span className="text-sm text-slate-500">
            Score <span className="font-semibold text-slate-800">{account.TOTAL_SCORE}</span>
          </span>
          <span className="h-1 w-1 rounded-full bg-slate-300" />
          <span className="text-sm text-slate-500">
            {account.ASSET_COUNT} asset{account.ASSET_COUNT === 1 ? "" : "s"}
          </span>
          {countries.length > 0 && (
            <>
              <span className="h-1 w-1 rounded-full bg-slate-300" />
              <span className="text-sm text-slate-500">{countries.join(", ")}</span>
            </>
          )}
        </div>
        {(orgs.length > 0 || providerRoles.length > 0) && (
          <div className="mt-2 space-y-0.5">
            {orgs.length > 0 && <p className="text-xs text-slate-400">Org(s): {orgs.join(", ")}</p>}
            {providerRoles.length > 0 && (
              <p className="text-xs text-slate-400">Provider role: {providerRoles.join(", ")}</p>
            )}
          </div>
        )}
      </header>

      <section className="surface-card mb-8 overflow-hidden">
        <div className="border-l-4 border-indigo-500 bg-gradient-to-br from-indigo-50/60 to-transparent p-5">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-indigo-700">
              <SparkleIcon className="h-3.5 w-3.5" />
              AI Sales Brief
            </h2>
            {account.NARRATIVE_SOURCE && (
              <span
                className={`rounded-full px-2.5 py-0.5 text-[11px] font-medium ${
                  account.NARRATIVE_SOURCE === "llm"
                    ? "bg-indigo-100 text-indigo-700"
                    : account.NARRATIVE_SOURCE === "mock"
                    ? "bg-amber-100 text-amber-800"
                    : "bg-slate-100 text-slate-500"
                }`}
                title={
                  account.NARRATIVE_SOURCE === "llm"
                    ? "Written by a real language model and citation-validated against the evidence below"
                    : account.NARRATIVE_SOURCE === "mock"
                    ? "Offline stand-in text, not written by a model"
                    : "The model's text failed citation validation, so a safe template built directly from the findings is shown instead"
                }
              >
                {account.NARRATIVE_SOURCE === "llm"
                  ? `AI-generated · ${(account.NARRATIVE_MODEL || "").replace("openai/", "")}${account.NARRATIVE_PROMPT_VERSION ? ` · prompt ${account.NARRATIVE_PROMPT_VERSION}` : ""}`
                  : account.NARRATIVE_SOURCE === "mock"
                  ? "Mock text"
                  : "Template fallback"}
              </span>
            )}
          </div>
          <p className="text-[15px] leading-relaxed text-slate-800">
            {account.NARRATIVE_SUMMARY || "No narrative available for this account."}
          </p>
          {account.NARRATIVE_OUTREACH_ANGLE && (
            <p className="mt-3 border-t border-indigo-100 pt-3 text-sm text-slate-600">
              <span className="font-semibold text-slate-700">Suggested opening: </span>
              {account.NARRATIVE_OUTREACH_ANGLE}
            </p>
          )}
        </div>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Why am I seeing this &middot; {topFindings.length} finding{topFindings.length === 1 ? "" : "s"}
        </h2>
        <ul className="space-y-2">
          {topFindings.map((finding, i) => (
            <li
              key={i}
              className={`flex items-start gap-2 rounded-lg border px-3.5 py-2.5 text-sm ${
                citedIndices.has(i)
                  ? "border-indigo-200 bg-indigo-50/60 text-indigo-950"
                  : "border-slate-200 bg-white text-slate-600"
              }`}
            >
              <span className="flex-1">{finding}</span>
              {citedIndices.has(i) && (
                <span className="shrink-0 rounded-full bg-indigo-100 px-2 py-0.5 text-[11px] font-medium text-indigo-600">
                  cited in AI brief
                </span>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Evidence detail &middot; {assets.length} asset{assets.length === 1 ? "" : "s"}
        </h2>
        <div className="surface-card overflow-hidden">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/60">
                <th className="px-3.5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">IP:Port</th>
                <th className="px-3.5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">Product</th>
                <th className="px-3.5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">Score</th>
                <th className="px-3.5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">Findings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {assets.map((asset, i) => (
                <tr key={i} className="hover:bg-slate-50/60">
                  <td className="px-3.5 py-2.5 font-mono text-xs text-slate-500">
                    {asset.IP}:{asset.PORT}
                  </td>
                  <td className="px-3.5 py-2.5 text-slate-600">{asset.PRODUCT}</td>
                  <td className="px-3.5 py-2.5 font-bold text-slate-900">{asset.ADJUSTED_SCORE}</td>
                  <td className="px-3.5 py-2.5 text-slate-600">
                    <ul className="space-y-0.5">
                      {parseJsonArray(asset.FINDINGS).map((f, j) => (
                        <li key={j} className="flex gap-1.5">
                          <span className="text-slate-300">&bull;</span>
                          {f}
                        </li>
                      ))}
                    </ul>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
