import Link from "next/link";

export function parsePaging(
  params: Record<string, string | string[] | undefined>,
  sizes: number[],
  defaultSize: number
) {
  const rawSize = Number(typeof params.size === "string" ? params.size : NaN);
  const size = sizes.includes(rawSize) ? rawSize : defaultSize;
  const rawPage = Number(typeof params.page === "string" ? params.page : NaN);
  const page = Number.isInteger(rawPage) && rawPage > 0 ? rawPage : 1;
  return { size, page };
}

function pageList(page: number, pages: number): (number | "...")[] {
  const set = new Set([1, pages, page - 1, page, page + 1].filter((p) => p >= 1 && p <= pages));
  const sorted = [...set].sort((a, b) => a - b);
  const out: (number | "...")[] = [];
  sorted.forEach((p, i) => {
    if (i > 0 && p - sorted[i - 1] > 1) out.push("...");
    out.push(p);
  });
  return out;
}

export function Pager({
  basePath,
  extra = {},
  page,
  size,
  total,
  sizes,
  noun = "rows",
}: {
  basePath: string;
  extra?: Record<string, string | null | undefined>;
  page: number;
  size: number;
  total: number;
  sizes: number[];
  noun?: string;
}) {
  const pages = Math.max(1, Math.ceil(total / size));
  const current = Math.min(page, pages);
  const from = total === 0 ? 0 : (current - 1) * size + 1;
  const to = Math.min(current * size, total);

  const href = (p: number, s: number) => {
    const q = new URLSearchParams();
    Object.entries(extra).forEach(([k, v]) => v && q.set(k, v));
    q.set("size", String(s));
    if (p > 1) q.set("page", String(p));
    const qs = q.toString();
    return qs ? `${basePath}?${qs}` : basePath;
  };

  const btn = "rounded-md border px-2.5 py-1 text-sm font-medium transition-colors";
  const idle = "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:bg-slate-50";
  const active = "border-indigo-600 bg-indigo-600 text-white";
  const off = "cursor-not-allowed border-slate-100 bg-slate-50 text-slate-300";

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-500">
      <div>
        Showing <strong className="text-slate-700">{from.toLocaleString()}&ndash;{to.toLocaleString()}</strong> of{" "}
        <strong className="text-slate-700">{total.toLocaleString()}</strong> {noun}
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-slate-400">Per page</span>
          {sizes.map((s) => (
            <Link key={s} href={href(1, s)} className={`${btn} ${s === size ? active : idle}`}>
              {s}
            </Link>
          ))}
        </div>

        <nav className="flex items-center gap-1" aria-label="Pagination">
          {current > 1 ? (
            <Link href={href(current - 1, size)} className={`${btn} ${idle}`}>Prev</Link>
          ) : (
            <span className={`${btn} ${off}`}>Prev</span>
          )}
          {pageList(current, pages).map((p, i) =>
            p === "..." ? (
              <span key={`d${i}`} className="px-1 text-slate-400">&hellip;</span>
            ) : (
              <Link key={p} href={href(p, size)} className={`${btn} ${p === current ? active : idle}`}>
                {p}
              </Link>
            )
          )}
          {current < pages ? (
            <Link href={href(current + 1, size)} className={`${btn} ${idle}`}>Next</Link>
          ) : (
            <span className={`${btn} ${off}`}>Next</span>
          )}
        </nav>
      </div>
    </div>
  );
}
