import type { PriorityTier } from "@/lib/types";

const TIER_VARS: Record<PriorityTier, { bg: string; border: string; text: string; dot: string }> = {
  CRITICAL: { bg: "var(--tier-critical-bg)", border: "var(--tier-critical-border)", text: "var(--tier-critical-text)", dot: "var(--tier-critical-dot)" },
  HIGH: { bg: "var(--tier-high-bg)", border: "var(--tier-high-border)", text: "var(--tier-high-text)", dot: "var(--tier-high-dot)" },
  MEDIUM: { bg: "var(--tier-medium-bg)", border: "var(--tier-medium-border)", text: "var(--tier-medium-text)", dot: "var(--tier-medium-dot)" },
  LOW: { bg: "var(--tier-low-bg)", border: "var(--tier-low-border)", text: "var(--tier-low-text)", dot: "var(--tier-low-dot)" },
};

export function TierBadge({ tier }: { tier: PriorityTier }) {
  const c = TIER_VARS[tier];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold tracking-wide"
      style={{ background: c.bg, borderColor: c.border, color: c.text }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: c.dot }} />
      {tier}
    </span>
  );
}

export function ConfidenceBadge({ confidence }: { confidence: string }) {
  const isHigh = confidence === "HIGH";
  return (
    <span
      title={isHigh ? "We saw this business's own website" : "Matched by organization name only; score counted at 70%"}
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-medium ${
        isHigh
          ? "bg-indigo-50 text-indigo-700 border-indigo-200"
          : "bg-slate-50 text-slate-500 border-slate-200"
      }`}
    >
      {confidence} confidence
    </span>
  );
}
