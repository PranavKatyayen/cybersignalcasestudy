import type { ReactNode } from "react";

export function StatCard({
  label,
  value,
  accent,
  icon,
}: {
  label: string;
  value: string | number;
  accent?: string;
  icon?: ReactNode;
}) {
  return (
    <div className="surface-card flex items-center gap-3.5 px-5 py-4">
      {icon && (
        <div
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg"
          style={{ background: accent ? `${accent}1a` : "var(--surface-muted)", color: accent || "#64748b" }}
        >
          {icon}
        </div>
      )}
      <div className="min-w-0">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{label}</div>
        <div className="mt-0.5 text-2xl font-bold tracking-tight text-slate-900">{value}</div>
      </div>
    </div>
  );
}
