// Turns the raw finding sentences into short, plain labels a salesperson can scan.
export type Severity = "critical" | "high" | "medium" | "low";

export interface FindingChip {
  label: string;
  severity: Severity;
  detail: string; // the original sentence plus what it means, shown on hover
}

const ORDER: Record<Severity, number> = { critical: 0, high: 1, medium: 2, low: 3 };

export function describeFinding(text: string): FindingChip {
  let m: RegExpMatchArray | null;

  if (/^Host shows signs of compromise/i.test(text)) {
    return { label: "Signs of compromise", severity: "critical", detail: `${text}. The strongest signal: worth an immediate call.` };
  }
  if ((m = text.match(/^Known CVE\(s\) present:\s*(.+)$/i))) {
    const ids = m[1].match(/CVE-\d{4}-\d+/g) ?? [];
    const first = ids[0] ?? "CVE";
    const label = ids.length > 1 ? `Known flaw ${first} +${ids.length - 1} more` : `Known flaw ${first}`;
    return { label, severity: "high", detail: `${text}. A publicly listed security flaw that has a known fix.` };
  }
  if ((m = text.match(/^Risky service exposed on port (\d+):\s*([^(]+)/i))) {
    return { label: `Exposed ${m[2].trim()} (port ${m[1]})`, severity: "high", detail: `${text}. A door that should not be open to the whole internet.` };
  }
  if ((m = text.match(/^End-of-life software detected:\s*(.+)$/i))) {
    return { label: `Outdated ${m[1].trim()}`, severity: "medium", detail: `${text}. The maker no longer fixes new flaws in it.` };
  }
  if ((m = text.match(/^IoT\/camera device exposed:\s*(.+)$/i))) {
    return { label: `Exposed camera: ${m[1].trim()}`, severity: "medium", detail: `${text}. Connected devices are often left with weak settings.` };
  }
  if (/^Self-signed TLS/i.test(text)) {
    return { label: "Self-signed certificate", severity: "low", detail: `${text}. A sign of careless upkeep.` };
  }
  if (/^Open directory listing/i.test(text)) {
    return { label: "Open directory listing", severity: "low", detail: `${text}. Files can be browsed by anyone.` };
  }
  return { label: text.length > 42 ? `${text.slice(0, 40)}...` : text, severity: "medium", detail: text };
}

// unique labels, most severe first
export function describeFindings(list: string[]): FindingChip[] {
  const seen = new Set<string>();
  return list
    .map(describeFinding)
    .filter((c) => (seen.has(c.label) ? false : (seen.add(c.label), true)))
    .sort((a, b) => ORDER[a.severity] - ORDER[b.severity]);
}

export const CHIP_STYLES: Record<Severity, string> = {
  critical: "border-red-200 bg-red-50 text-red-700",
  high: "border-orange-200 bg-orange-50 text-orange-700",
  medium: "border-amber-200 bg-amber-50 text-amber-800",
  low: "border-slate-200 bg-slate-50 text-slate-600",
};
