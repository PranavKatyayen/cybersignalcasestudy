import { CATEGORY_ORDER, SOURCE_LABELS, categoryStyle, type AccountTech, type TechEvidence } from "@/lib/tech";

const cell = "px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-slate-400";

export function TechnologyStack({ technologies, evidence }: { technologies: AccountTech[]; evidence: TechEvidence[] }) {
  if (technologies.length === 0) return null;
  const groups = CATEGORY_ORDER.map((category) => ({
    category,
    items: technologies.filter((t) => t.category === category),
  })).filter((g) => g.items.length > 0);

  return (
    <section className="mb-8">
      <h2 className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
        Technology stack &middot; {technologies.length} technolog{technologies.length === 1 ? "y" : "ies"} in {groups.length}{" "}
        {groups.length === 1 ? "category" : "categories"}
      </h2>
      <p className="mb-3 text-sm text-slate-500">
        What the scan saw running on this account&apos;s systems. Found by fixed rules, not AI. It is one snapshot, so it shows
        what was visible then, not necessarily what the company uses today.
      </p>
      <div className="surface-card space-y-4 p-5">
        {groups.map((g) => (
          <div key={g.category}>
            <div className="mb-1.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{g.category}</div>
            <div className="flex flex-wrap gap-1.5">
              {g.items.map((t) => (
                <span
                  key={t.technology}
                  title={`Seen on ${t.assetCount} asset${t.assetCount === 1 ? "" : "s"} via ${t.sources.map((s) => SOURCE_LABELS[s] ?? s).join(", ")}${t.vendor ? `. Vendor: ${t.vendor}` : ""}`}
                  className={`inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-sm font-medium ${categoryStyle(g.category)}`}
                >
                  {t.technology}
                  {t.versions.length > 0 && <span className="font-mono text-xs opacity-75">{t.versions.slice(0, 2).join(", ")}</span>}
                  <span className="rounded bg-white/70 px-1 text-[11px] font-normal opacity-80">&times;{t.assetCount}</span>
                </span>
              ))}
            </div>
          </div>
        ))}
        <details className="border-t border-slate-100 pt-3">
          <summary className="cursor-pointer text-sm font-medium text-indigo-600">
            How we know &middot; {evidence.length}{evidence.length >= 400 ? "+" : ""} pieces of evidence
          </summary>
          <p className="mt-2 text-xs text-slate-500">
            Each technology is traced to the exact string and asset that revealed it. The number after &times; is how many assets showed it.
          </p>
          <div className="mt-2 max-h-96 overflow-auto rounded-lg border border-slate-200">
            <table className="min-w-full text-xs">
              <thead className="sticky top-0 bg-slate-50">
                <tr>
                  <th className={cell}>Technology</th>
                  <th className={cell}>Version</th>
                  <th className={cell}>How it was seen</th>
                  <th className={cell}>Revealed by</th>
                  <th className={cell}>Asset</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {evidence.map((e, i) => (
                  <tr key={i}>
                    <td className="px-3 py-1.5 font-medium text-slate-700">{e.technology}</td>
                    <td className="px-3 py-1.5 font-mono text-slate-500">{e.version ?? ""}</td>
                    <td className="px-3 py-1.5 text-slate-500">{SOURCE_LABELS[e.source] ?? e.source}</td>
                    <td className="max-w-[16rem] truncate px-3 py-1.5 font-mono text-slate-500" title={e.signal}>{e.signal}</td>
                    <td className="px-3 py-1.5 font-mono text-slate-500">{e.asset}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </div>
    </section>
  );
}
