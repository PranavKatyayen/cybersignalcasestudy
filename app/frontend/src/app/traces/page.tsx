import Link from "next/link";
import { StatCard } from "@/components/StatCard";
import { Pager, parsePaging } from "@/components/Pager";
import { ArrowLeftIcon, LayersIcon, DollarIcon, ClockIcon, CheckCircleIcon } from "@/components/icons";
import {
  FILTER_KEYS,
  applyFilters,
  bySkillVersion,
  loadCalls,
  loadEvals,
  loadExamples,
  options,
  parseFilters,
  summarize,
  type Filters,
} from "@/lib/traces";

const CALL_SIZES = [10, 20, 50, 100];

const FILTER_LABELS: Record<(typeof FILTER_KEYS)[number], string> = {
  skill: "Skill",
  version: "Prompt version",
  provider: "Provider",
  model: "Model",
  status: "Status",
};

const METRIC_LABELS: Record<string, string> = {
  accuracy: "Accuracy",
  overclaim_free_rate: "No unsupported claims",
  third_person_rate: "Written about the account",
  citation_validity_rate: "Citations valid",
  fabrication_free_rate: "No made-up CVEs or ports",
  critical_coverage_rate: "Covers the top finding",
  avg_evidence_coverage: "Evidence covered",
  filter_correct: "Correct filters",
  no_invented_account: "No invented accounts",
  no_invented_cve: "No invented CVEs",
  no_trend_claim: "No trend claims",
  no_unrelated_accounts_shown: "No unrelated accounts",
  refuses_off_topic: "Refuses off-topic",
};

const COST_ROWS = [
  { task: "Organization classification", model: "small model: gemini-3.5-flash-lite", tokens: "371 / 40", cost: "$0.00021" },
  { task: "Sales brief", model: "writing model: gemini-3.1-flash-lite", tokens: "531 / 101", cost: "$0.00028" },
  { task: "Sales brief", model: "writing model: gemini-3.5-flash-lite", tokens: "562 / 136", cost: "$0.00051" },
  { task: "Chat question (2 calls, estimate)", model: "gemini flash-lite", tokens: "about 1,500 / 300", cost: "about $0.0024" },
];

const PROD_ROWS = [
  { item: "Briefs", math: "417 accounts × $0.00051", day: "$0.21" },
  { item: "Organization classification", math: "about 45 new names × $0.00021", day: "$0.01" },
  { item: "Chat", math: "500 questions × $0.0024", day: "$1.20" },
];

const TH = "px-3.5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400";
const pct = (n: number) => `${Math.round(n * 1000) / 10}%`;

export default async function TracesPage({ searchParams }: PageProps<"/traces">) {
  const params = await searchParams;
  const all = loadCalls();
  const filters = parseFilters(params, all);
  const { size, page: requestedPage } = parsePaging(params, CALL_SIZES, 20);

  const filtered = applyFilters(all, filters);
  const view = summarize(filtered);
  const pages = Math.max(1, Math.ceil(filtered.length / size));
  const page = Math.min(requestedPage, pages);
  const rows = filtered.slice((page - 1) * size, page * size);
  const anyFilter = FILTER_KEYS.some((k) => filters[k]);
  const unpriced = filtered.filter((c) => !c.priced).length;

  const versionRows = bySkillVersion(all);
  const evals = loadEvals();
  const examples = loadExamples();

  const filterHref = (over: Partial<Filters>) => {
    const next = { ...filters, ...over };
    const q = new URLSearchParams();
    FILTER_KEYS.forEach((k) => next[k] && q.set(k, next[k] as string));
    if (size !== 20) q.set("size", String(size));
    const qs = q.toString();
    return qs ? `/traces?${qs}` : "/traces";
  };

  const pill = (active: boolean) =>
    `rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
      active
        ? "border-indigo-600 bg-indigo-600 text-white"
        : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50"
    }`;

  return (
    <main className="mx-auto max-w-6xl px-6 py-10">
      <Link href="/" className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 hover:text-indigo-600">
        <ArrowLeftIcon className="h-3.5 w-3.5" />
        Back to dashboard
      </Link>

      <header className="mt-5 mb-6">
        <h1 className="text-[26px] font-bold tracking-tight text-slate-900">LLM call tracing</h1>
        <p className="mt-1.5 max-w-3xl text-[15px] text-slate-500">
          Every AI call made while building this project, {all.length.toLocaleString()} in total. Filter by skill, prompt
          version, provider, model or status, compare prompt v1 with v2, and open example calls to see the exact
          request and response. This is a snapshot of the pipeline log, not a live feed.
        </p>
      </header>

      <section className="surface-card mb-6 space-y-3 px-5 py-4">
        {FILTER_KEYS.map((key) => (
          <div key={key} className="flex flex-wrap items-center gap-2">
            <span className="w-28 shrink-0 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
              {FILTER_LABELS[key]}
            </span>
            <Link href={filterHref({ [key]: null })} className={pill(!filters[key])}>
              All
            </Link>
            {options(all, key).map((o) => (
              <Link key={o.value} href={filterHref({ [key]: o.value })} className={pill(filters[key] === o.value)}>
                {o.value} <span className="opacity-70">({o.count.toLocaleString()})</span>
              </Link>
            ))}
          </div>
        ))}
        {anyFilter && (
          <div className="pt-1 text-xs text-slate-500">
            <Link href="/traces" className="font-medium text-indigo-600 hover:underline">Clear all filters</Link>
          </div>
        )}
      </section>

      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        <StatCard label={anyFilter ? "Matching calls" : "Total calls"} value={view.n.toLocaleString()} accent="#4f46e5" icon={<LayersIcon className="h-4.5 w-4.5" />} />
        <StatCard label="Billed to you" value="$0.00" accent="#16a34a" icon={<DollarIcon className="h-4.5 w-4.5" />} />
        <StatCard label="Paid-equivalent cost" value={`$${view.cost.toFixed(4)}`} accent="#0891b2" icon={<DollarIcon className="h-4.5 w-4.5" />} />
        <StatCard label="Avg latency" value={`${Math.round(view.avgMs).toLocaleString()}ms`} accent="#64748b" icon={<ClockIcon className="h-4.5 w-4.5" />} />
        <StatCard label="Success rate" value={view.n ? `${view.successRate.toFixed(1)}%` : "-"} accent="#16a34a" icon={<CheckCircleIcon className="h-4.5 w-4.5" />} />
      </div>

      <div className="mb-8 rounded-xl border border-indigo-100 bg-indigo-50/60 px-4 py-3.5 text-sm text-slate-700">
        <strong>Two different numbers.</strong> <em>Billed to you</em> is $0.00 because every call ran on a free tier.{" "}
        <em>Paid-equivalent cost</em> is what the same calls would cost at each provider&apos;s published paid rates.
        {unpriced > 0 && <> {unpriced} of the matching calls use a model with no published rate, so they count as $0 rather than a guess.</>}
      </div>

      <section className="mb-8">
        <h2 className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Prompt versions compared</h2>
        <p className="mb-3 text-sm text-slate-500">
          Runs of each skill by prompt version, across all calls. Latency and cost also depend on the provider and model
          used for those runs (see the Models column), so read them alongside the quality results below.
        </p>
        <div className="surface-card overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/60">
                <th className={TH}>Skill</th>
                <th className={TH}>Prompt</th>
                <th className={TH}>Calls</th>
                <th className={TH}>Success</th>
                <th className={TH}>Avg latency</th>
                <th className={TH}>Avg tokens in / out</th>
                <th className={TH}>Avg cost / call</th>
                <th className={TH}>Models</th>
                <th className={TH}></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {versionRows.map((v) => (
                <tr key={`${v.skill}${v.version}`} className="hover:bg-slate-50/60">
                  <td className="px-3.5 py-2.5 font-mono text-xs text-slate-700">{v.skill}</td>
                  <td className="px-3.5 py-2.5 font-semibold text-slate-700">{v.version}</td>
                  <td className="px-3.5 py-2.5 text-slate-600">{v.n.toLocaleString()}</td>
                  <td className="px-3.5 py-2.5 text-slate-600">{v.successRate.toFixed(1)}%</td>
                  <td className="px-3.5 py-2.5 text-slate-600">{Math.round(v.avgMs).toLocaleString()}ms</td>
                  <td className="px-3.5 py-2.5 text-slate-600">{Math.round(v.avgIn)} / {Math.round(v.avgOut)}</td>
                  <td className="px-3.5 py-2.5 text-slate-600">${v.avgCost.toFixed(5)}</td>
                  <td className="px-3.5 py-2.5 text-xs text-slate-500">{v.models.join(", ")}</td>
                  <td className="px-3.5 py-2.5">
                    <Link href={filterHref({ skill: v.skill, version: v.version, provider: null, model: null, status: null })} className="text-xs font-medium text-indigo-600 hover:underline">
                      View calls
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="mb-2 mt-5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Quality results from the evaluations</h3>
        <div className="surface-card overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/60">
                <th className={TH}>Skill</th>
                <th className={TH}>Prompt</th>
                <th className={TH}>Model</th>
                <th className={TH}>Results</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {evals.map((e, i) => (
                <tr key={i} className="align-top hover:bg-slate-50/60">
                  <td className="px-3.5 py-2.5 font-mono text-xs text-slate-700">{e.skill}</td>
                  <td className="px-3.5 py-2.5 font-semibold text-slate-700">{e.version}</td>
                  <td className="px-3.5 py-2.5 text-xs text-slate-500">{e.model ?? "live app"}</td>
                  <td className="px-3.5 py-2.5">
                    <div className="flex flex-wrap gap-1.5">
                      {Object.entries(e.metrics).map(([k, v]) => (
                        <span
                          key={k}
                          className={`rounded-md px-2 py-0.5 text-xs ${
                            v >= 0.999 ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"
                          }`}
                        >
                          {METRIC_LABELS[k] ?? k} {pct(v)}
                        </span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-xs text-slate-400">
          The v2 prompts were written after seeing v1&apos;s failures on the same small test sets, so part of the gain is tuning to the test.
        </p>
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Calls &middot; {anyFilter ? `${filtered.length.toLocaleString()} matching` : "all"} of {all.length.toLocaleString()}
        </h2>
        <div className="mb-3">
          <Pager
            basePath="/traces"
            extra={Object.fromEntries(FILTER_KEYS.map((k) => [k, filters[k]]))}
            page={page}
            size={size}
            total={filtered.length}
            sizes={CALL_SIZES}
            noun="calls"
          />
        </div>
        <div className="surface-card overflow-x-auto">
          <table className="min-w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/60">
                <th className={TH}>Time (UTC)</th>
                <th className={TH}>Skill</th>
                <th className={TH}>Prompt</th>
                <th className={TH}>Provider</th>
                <th className={TH}>Model</th>
                <th className={TH}>Latency</th>
                <th className={TH}>Tokens in / out</th>
                <th className={TH}>Cost</th>
                <th className={TH}>Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((r) => (
                <tr key={r.id + r.ts} className="hover:bg-slate-50/60">
                  <td className="px-3.5 py-2.5 text-slate-400">{r.ts.slice(11, 19)}</td>
                  <td className="px-3.5 py-2.5 font-mono text-slate-700">{r.skill}</td>
                  <td className="px-3.5 py-2.5 text-slate-500">{r.version}</td>
                  <td className="px-3.5 py-2.5 text-slate-500">{r.provider}</td>
                  <td className="px-3.5 py-2.5 text-slate-500">{r.model}</td>
                  <td className="px-3.5 py-2.5 text-slate-500">{r.ms.toLocaleString()}ms</td>
                  <td className="px-3.5 py-2.5 text-slate-500">{r.tin} / {r.tout}</td>
                  <td className="px-3.5 py-2.5 text-slate-500">{r.priced ? `$${r.cost.toFixed(6)}` : "no rate"}</td>
                  <td className="px-3.5 py-2.5">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        r.status === "success" ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
                      }`}
                    >
                      {r.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {rows.length === 0 && <p className="mt-4 text-center text-sm text-slate-500">No calls match these filters.</p>}
        <div className="mt-4">
          <Pager
            basePath="/traces"
            extra={Object.fromEntries(FILTER_KEYS.map((k) => [k, filters[k]]))}
            page={page}
            size={size}
            total={filtered.length}
            sizes={CALL_SIZES}
            noun="calls"
          />
        </div>
      </section>

      <section className="mb-8">
        <h2 className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Inspect example calls</h2>
        <p className="mb-3 text-sm text-slate-500">
          One real call per skill and prompt version, with the full request sent to the model and the response that came
          back. Open one to see how v1 and v2 differ in what the model was told.
        </p>
        <div className="space-y-2">
          {examples.map((e) => (
            <details key={e.id} className="surface-card group px-4 py-3">
              <summary className="cursor-pointer text-sm font-medium text-slate-700">
                <span className="font-mono text-xs">{e.skill}</span> &middot; prompt {e.version} &middot; {e.model} &middot;{" "}
                {e.ms.toLocaleString()}ms &middot; {e.tin} in / {e.tout} out
              </summary>
              <div className="mt-3 grid gap-3 lg:grid-cols-2">
                <div>
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Request (instructions + data)</div>
                  <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-900 p-3 text-[11px] leading-relaxed text-slate-100">{e.request}</pre>
                </div>
                <div>
                  <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Response</div>
                  <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-lg bg-slate-50 p-3 text-[11px] leading-relaxed text-slate-700">{e.response}</pre>
                </div>
              </div>
            </details>
          ))}
        </div>
      </section>

      <details className="surface-card px-5 py-4 text-sm text-slate-700">
        <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          How the cost is calculated
        </summary>
        <div className="mt-4 space-y-5">
          <p>
            <strong>Cost per call</strong> = (input tokens &times; input price + output tokens &times; output price) &divide; 1,000,000.
            Tokens are measured from the calls above; prices are the providers&apos; published rates. Example, one
            organization classification on gemini-3.5-flash-lite ($0.30 in / $2.50 out per million tokens):
            (371 &times; 0.30 + 40 &times; 2.50) &divide; 1,000,000 = <strong>$0.00021</strong>.
          </p>
          <table className="min-w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/60 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="px-3 py-2">Task</th>
                <th className="px-3 py-2">Model choice</th>
                <th className="px-3 py-2">Avg tokens in / out</th>
                <th className="px-3 py-2">Cost per call</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {COST_ROWS.map((r) => (
                <tr key={r.task + r.model}>
                  <td className="px-3 py-2 font-medium text-slate-700">{r.task}</td>
                  <td className="px-3 py-2 text-slate-600">{r.model}</td>
                  <td className="px-3 py-2 text-slate-600">{r.tokens}</td>
                  <td className="px-3 py-2 text-slate-600">{r.cost}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <table className="min-w-full text-xs">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50/60 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                <th className="px-3 py-2">Production estimate (volume &times; frequency)</th>
                <th className="px-3 py-2">Volume &times; cost per call</th>
                <th className="px-3 py-2">Per day</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {PROD_ROWS.map((r) => (
                <tr key={r.item}>
                  <td className="px-3 py-2 font-medium text-slate-700">{r.item}</td>
                  <td className="px-3 py-2 text-slate-600">{r.math}</td>
                  <td className="px-3 py-2 text-slate-600">{r.day}</td>
                </tr>
              ))}
              <tr className="bg-slate-50/60">
                <td className="px-3 py-2 font-semibold text-slate-800">Total</td>
                <td className="px-3 py-2 text-slate-600">&times; 30 days = about $43 a month</td>
                <td className="px-3 py-2 font-semibold text-slate-800">about $1.40</td>
              </tr>
            </tbody>
          </table>
          <p>
            <strong>Ceiling: $60 a month</strong>, with a hard stop if one day&apos;s spend passes 3&times; the expected
            amount (about $4.30). Each logged call carries its cost, so that check is a sum over one day&apos;s records.
            Volumes are planning assumptions (a daily scan of this size, 20% new organization names, 500 chat questions a
            day); token counts and prices are measured or published. The chat cost per question is an estimate.
          </p>
        </div>
      </details>
    </main>
  );
}
