// Pure filter helpers used by the chat and the dashboard (no database access here).
export const TIERS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;

export interface ChatFilters {
  tiers: string[];
  country: string | null;
  minScore: number | null;
  confidence: "HIGH" | "MEDIUM" | null;
  text: string | null;
  limit: number;
}

// Exact match first, then a containment match ("Korea" -> "South Korea")
export function matchCountry(raw: string, countries: string[]): string | null {
  const q = raw.trim().toLowerCase();
  if (!q) return null;
  return (
    countries.find((c) => c.toLowerCase() === q) ??
    countries.find((c) => c.toLowerCase().includes(q) || q.includes(c.toLowerCase())) ??
    null
  );
}

// The model only proposes filters; nothing it says is ever interpolated into SQL
export function sanitizeFilters(raw: unknown, countries: string[]): ChatFilters {
  const r = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  const tiers = Array.isArray(r.tiers)
    ? r.tiers.map((t) => String(t).toUpperCase()).filter((t) => (TIERS as readonly string[]).includes(t))
    : [];
  const country = typeof r.country === "string" ? matchCountry(r.country, countries) : null;
  const minScore = typeof r.min_score === "number" && isFinite(r.min_score) ? Math.max(0, Math.floor(r.min_score)) : null;
  const confidence = r.confidence === "HIGH" || r.confidence === "MEDIUM" ? r.confidence : null;
  const text = typeof r.text === "string" && r.text.trim() ? r.text.trim().slice(0, 60) : null;
  const limitRaw = typeof r.limit === "number" ? Math.floor(r.limit) : 8;
  return { tiers, country, minScore, confidence, text, limit: Math.min(Math.max(limitRaw, 1), 10) };
}
