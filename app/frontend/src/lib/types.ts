// Column names are uppercase because Snowflake returns them that way

export type PriorityTier = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type AttributionConfidence = "HIGH" | "MEDIUM";
export type NarrativeSource = "llm" | "fallback_template" | "mock" | null;

export interface ProspectAccountRow {
  ENTITY_KEY: string;
  PRIORITY_TIER: PriorityTier;
  PRIORITY_RANK: number;
  ATTRIBUTION_CONFIDENCE: AttributionConfidence;
  TOTAL_SCORE: number;
  FINDING_COUNT: number;
  ASSET_COUNT: number;
  PROVIDER_ROLES: unknown; // VARIANT array
  ATTRIBUTION_REASONS: unknown; // VARIANT array
  ORGS: unknown; // VARIANT array
  COUNTRIES: unknown; // VARIANT array
  SAMPLE_IPS: unknown; // VARIANT array
  TOP_FINDINGS: unknown; // VARIANT array
  HEADLINE_FINDING: string;
  NARRATIVE_SUMMARY: string | null;
  NARRATIVE_OUTREACH_ANGLE: string | null;
  NARRATIVE_CITED_EVIDENCE_INDICES: unknown; // VARIANT array
  NARRATIVE_SOURCE: NarrativeSource;
  NARRATIVE_PROVIDER: string | null;
  NARRATIVE_MODEL: string | null;
  NARRATIVE_PROMPT_VERSION: string | null;
  LOADED_AT: string;
}

export interface AssetEvidenceRow {
  ENTITY_KEY: string;
  PRIORITY_TIER: PriorityTier;
  IP: string;
  PORT: number;
  PRODUCT: string;
  COUNTRY: string;
  ORG: string;
  DOMAIN: string | null;
  PROVIDER_ROLE: string;
  ATTRIBUTION_REASON: string;
  RAW_SCORE: number;
  ADJUSTED_SCORE: number;
  FINDINGS: unknown; // VARIANT array
  TAGS: unknown; // VARIANT array
  LOADED_AT: string;
}
