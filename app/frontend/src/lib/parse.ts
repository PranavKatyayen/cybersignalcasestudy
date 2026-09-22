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
