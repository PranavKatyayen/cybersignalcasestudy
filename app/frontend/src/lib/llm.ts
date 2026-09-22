// Server-side LLM client for the chat feature

interface Provider {
  name: string;
  url: string;
  keyEnv: string;
  models: { small: string; large: string };
  extra: Record<string, unknown>;
}

const GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions";

// Tried in order: if one hits its free-tier limit, the next one is used
const PROVIDERS: Provider[] = [
  {
    name: "gemini",
    url: GEMINI_URL,
    keyEnv: "GEMINI_API_KEY",
    models: { small: "gemini-3.1-flash-lite", large: "gemini-3.1-flash-lite" },
    extra: {},
  },
  {
    name: "gemini",
    url: GEMINI_URL,
    keyEnv: "GEMINI_API_KEY",
    models: { small: "gemini-3.5-flash-lite", large: "gemini-3.5-flash-lite" },
    extra: {},
  },
  {
    name: "groq",
    url: "https://api.groq.com/openai/v1/chat/completions",
    keyEnv: "GROQ_API_KEY",
    models: { small: "openai/gpt-oss-20b", large: "openai/gpt-oss-120b" },
    extra: { reasoning_effort: "low" },
  },
];

export interface LlmResult {
  text: string;
  provider: string;
  model: string;
  inputTokens: number;
  outputTokens: number;
  latencyMs: number;
}

export async function chatComplete(opts: {
  tier: "small" | "large";
  system: string;
  user: string;
  json?: boolean;
  maxTokens?: number;
}): Promise<LlmResult> {
  const available = PROVIDERS.filter((p) => process.env[p.keyEnv]);
  if (available.length === 0) throw new Error("No LLM provider key configured (GEMINI_API_KEY or GROQ_API_KEY)");

  let lastError = "";
  for (const p of available) {
    const started = Date.now();
    try {
      const res = await fetch(p.url, {
        method: "POST",
        headers: { Authorization: `Bearer ${process.env[p.keyEnv]}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          model: p.models[opts.tier],
          messages: [
            { role: "system", content: opts.system },
            { role: "user", content: opts.user },
          ],
          max_tokens: opts.maxTokens ?? 500,
          temperature: 0,
          ...p.extra,
          ...(opts.json ? { response_format: { type: "json_object" } } : {}),
        }),
        signal: AbortSignal.timeout(20000),
      });
      if (!res.ok) {
        lastError = `${p.name} ${res.status}: ${(await res.text()).slice(0, 160)}`;
        continue; // rate limit, quota or outage: try the next provider
      }
      const data = await res.json();
      const text = data.choices?.[0]?.message?.content ?? "";
      if (!text) {
        lastError = `${p.name}: empty response`;
        continue;
      }
      return {
        text,
        provider: p.name,
        model: p.models[opts.tier],
        inputTokens: data.usage?.prompt_tokens ?? 0,
        outputTokens: data.usage?.completion_tokens ?? 0,
        latencyMs: Date.now() - started,
      };
    } catch (e) {
      lastError = `${p.name}: ${e instanceof Error ? e.message : "request failed"}`;
    }
  }
  throw new Error(`all providers failed (${lastError})`);
}
