// Pure filter helpers used by the chat and the dashboard (no database access here).
export const TIERS = ["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;

export interface ChatFilters {
  tiers: string[];
  country: string | null;
  minScore: number | null;
  confidence: "HIGH" | "MEDIUM" | null;
  text: string | null;
  technology: string | null;
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

// Exact name first, then a prefix of at least 4 letters ("apache" -> "Apache HTTP Server"). Short names never match by containment.
export function matchTechnology(raw: string, technologies: string[]): string | null {
  const q = raw.trim().toLowerCase();
  if (!q) return null;
  return (
    technologies.find((t) => t.toLowerCase() === q) ??
    (q.length >= 4 ? technologies.find((t) => t.toLowerCase().startsWith(q)) : undefined) ??
    null
  );
}

// The model only proposes filters; nothing it says is ever interpolated into SQL
export function sanitizeFilters(raw: unknown, countries: string[], technologies: string[] = []): ChatFilters {
  const r = (raw && typeof raw === "object" ? raw : {}) as Record<string, unknown>;
  const tiers = Array.isArray(r.tiers)
    ? r.tiers.map((t) => String(t).toUpperCase()).filter((t) => (TIERS as readonly string[]).includes(t))
    : [];
  const country = typeof r.country === "string" ? matchCountry(r.country, countries) : null;
  const minScore = typeof r.min_score === "number" && isFinite(r.min_score) ? Math.max(0, Math.floor(r.min_score)) : null;
  const confidence = r.confidence === "HIGH" || r.confidence === "MEDIUM" ? r.confidence : null;
  const technology = typeof r.technology === "string" ? matchTechnology(r.technology, technologies) : null;
  const text = typeof r.text === "string" && r.text.trim() ? r.text.trim().slice(0, 60) : null;
  const limitRaw = typeof r.limit === "number" ? Math.floor(r.limit) : 8;
  return { tiers, country, minScore, confidence, text, technology, limit: Math.min(Math.max(limitRaw, 1), 10) };
}
