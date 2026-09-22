import { query } from "@/lib/snowflake";
import { knownCountries } from "@/lib/chat";
import { accountWhere, parseAccountFilters } from "@/lib/accounts";
import { parseJsonArray } from "@/lib/parse";

export const maxDuration = 30;

// A cell that starts with = + - @ can run as a formula in Excel, so it gets an apostrophe in front.
function cell(v: unknown): string {
  let s = v === null || v === undefined ? "" : String(v);
  if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
  return `"${s.replace(/"/g, '""')}"`;
}

export async function GET(req: Request) {
  const params = Object.fromEntries(new URL(req.url).searchParams.entries());
  const filters = parseAccountFilters(params, await knownCountries());
  const { sql, binds } = accountWhere(filters);
  const rows = await query<Record<string, unknown>>(
    `SELECT priority_rank, entity_key, priority_tier, total_score, attribution_confidence, countries, headline_finding,
            narrative_summary, narrative_outreach_angle
     FROM mart_prospect_accounts ${sql} ORDER BY priority_rank LIMIT 5000`,
    binds
  );
  const header = ["rank", "account", "tier", "score", "confidence", "country", "top_finding", "ai_brief", "suggested_opening"];
  const lines = [header.join(",")];
  for (const r of rows) {
    lines.push(
      [
        r.PRIORITY_RANK,
        r.ENTITY_KEY,
        r.PRIORITY_TIER,
        r.TOTAL_SCORE,
        r.ATTRIBUTION_CONFIDENCE,
        parseJsonArray(r.COUNTRIES)[0] ?? "",
        r.HEADLINE_FINDING,
        r.NARRATIVE_SUMMARY,
        r.NARRATIVE_OUTREACH_ANGLE,
      ]
        .map(cell)
        .join(",")
    );
  }
  return new Response(lines.join("\r\n") + "\r\n", {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": 'attachment; filename="cybersignal_accounts.csv"',
    },
  });
}
