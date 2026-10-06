// snowflake-sdk returns VARIANT columns already parsed into JS values
export function parseJsonArray(value: unknown): string[] {
  if (Array.isArray(value)) return value;
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }
  return [];
}

export function parseJsonIntArray(value: unknown): number[] {
  return parseJsonArray(value).map(Number);
}

// OBJECT columns come back as JS objects from snowflake-sdk, or as JSON text from other clients
export function parseJsonObject(value: unknown): Record<string, string[]> {
  if (value && typeof value === "object" && !Array.isArray(value)) return value as Record<string, string[]>;
  if (typeof value === "string") {
    try {
      const parsed = JSON.parse(value);
      return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    } catch {
      return {};
    }
  }
  return {};
}
