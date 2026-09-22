"""Provider-agnostic LLM client with the production scaffolding the case study asks for."""

import hashlib
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

TRACE_LOG_PATH = Path(__file__).resolve().parents[2] / "traces" / "llm_calls.jsonl"

PROVIDERS = {
    "groq": {
        "kind": "openai_compat",
        "base_url": "https://api.groq.com/openai/v1",
        "key_env": "GROQ_API_KEY",
        "models": {"small": "openai/gpt-oss-20b", "large": "openai/gpt-oss-120b"},
        "extra_params": {"reasoning_effort": "low"},
        "min_interval_s": 2.2,  # free tier is ~30 requests/minute
    },
    "gemini": {
        "kind": "openai_compat",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "key_env": "GEMINI_API_KEY",
        # Free tier measured: gemini-3.6-flash allows only ~20 requests/day
        "models": {"small": "gemini-3.5-flash-lite", "large": "gemini-3.5-flash-lite"},
        "extra_params": {},
        "min_interval_s": 4.5,  # ~13 requests/minute
    },
    "anthropic": {
        "kind": "anthropic",
        "key_env": "ANTHROPIC_API_KEY",
        "models": {"small": "claude-haiku-4-5-20251001", "large": "claude-sonnet-5"},
        "extra_params": {},
        "min_interval_s": 0.0,
    },
}

# USD per million tokens (input, output)
MODEL_PRICING = {
    "openai/gpt-oss-20b": (0.075, 0.30),
    "openai/gpt-oss-120b": (0.15, 0.60),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "gemini-3.5-flash-lite": (0.30, 2.50),  # ai.google.dev/gemini-api/docs/pricing
    "gemini-3.1-flash-lite": (0.25, 1.50),
}

# Default provider for each skill
SKILL_DEFAULT_PROVIDER = {"org_classification": "gemini", "risk_narrative": "gemini"}

_last_call_at: dict[str, float] = {}


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> tuple[float, bool]:
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return 0.0, False
    return (input_tokens / 1e6) * pricing[0] + (output_tokens / 1e6) * pricing[1], True


def _log_trace(record: dict):
    TRACE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(TRACE_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def resolve_provider(skill: str, mock: bool | None = None) -> str:
    if mock:
        return "mock"
    forced = os.environ.get(f"LLM_PROVIDER_{skill.upper()}") or os.environ.get("LLM_PROVIDER")
    if forced:
        if forced != "mock" and forced not in PROVIDERS:
            raise RuntimeError(f"Unknown LLM provider '{forced}'. Use one of: {list(PROVIDERS)} or mock.")
        if forced != "mock" and not os.environ.get(PROVIDERS[forced]["key_env"]):
            raise RuntimeError(f"LLM provider '{forced}' selected but {PROVIDERS[forced]['key_env']} is not set.")
        return forced
    # Default per-skill provider (see SKILL_DEFAULT_PROVIDER); falls back to any provider with a key
    preferred = SKILL_DEFAULT_PROVIDER.get(skill)
    if preferred and os.environ.get(PROVIDERS[preferred]["key_env"]):
        return preferred
    for name, cfg in PROVIDERS.items():
        if os.environ.get(cfg["key_env"]):
            return name
    return "mock"


def _mock_response(skill: str, user_input: str) -> dict:
    """Deterministic offline stand-in."""
    h = int(hashlib.sha256(user_input.encode()).hexdigest(), 16)

    if skill == "org_classification":
        infra_kw = ["cloud", "hosting", "telecom", "internet", "isp", "gmbh",
                    "communications", "cdn", "llc", "digitalocean", "google",
                    "amazon", "microsoft", "cloudflare", "korea telecom",
                    "hetzner", "sakura", "huawei", "deutsche telekom",
                    "railtel", "uzbektelekom", "scancom", "ionos", "aliyun",
                    "incapsula"]
        is_infra = any(kw in user_input.lower() for kw in infra_kw)
        pseudo_random = (h % 1000) / 1000.0
        confidence = round(0.65 + pseudo_random * 0.30, 2) if is_infra else round(0.45 + pseudo_random * 0.45, 2)
        return {
            "classification": "infra" if is_infra else "end_business",
            "confidence": confidence,
            "reasoning": "[MOCK MODE] keyword-based approximation, not a real model call",
        }
    if skill == "risk_narrative":
        import re
        evidence_lines = re.findall(r"^\[(\d+)\]\s*(.+)$", user_input, re.MULTILINE)
        if not evidence_lines:
            return {"summary": "[MOCK MODE] No parsable evidence found in prompt.",
                    "outreach_angle": "[MOCK MODE] N/A", "cited_evidence_indices": []}
        indices = [int(i) for i, _ in evidence_lines]
        texts = {int(i): t for i, t in evidence_lines}
        primary_idx = indices[h % len(indices)]
        cited = [primary_idx]
        if len(indices) > 1:
            secondary_idx = indices[(h // 7) % len(indices)]
            if secondary_idx != primary_idx:
                cited.append(secondary_idx)
        cited_texts = "; ".join(texts[i].rstrip(".") for i in cited)
        return {
            "summary": f"[MOCK MODE] This account shows: {cited_texts}.",
            "outreach_angle": f"[MOCK MODE] Open by referencing: {texts[primary_idx].rstrip('.')}.",
            "cited_evidence_indices": cited,
        }
    return {}


def _parse_json(raw_text: str) -> dict:
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # some models wrap the JSON in prose; take the outermost object
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def _throttle(provider: str):
    gap = PROVIDERS[provider]["min_interval_s"]
    wait = gap - (time.time() - _last_call_at.get(provider, 0))
    if wait > 0:
        time.sleep(wait)
    _last_call_at[provider] = time.time()


def _call_openai_compat(provider: str, model: str, system_prompt: str, user_prompt: str, max_tokens: int):
    import requests

    cfg = PROVIDERS[provider]
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        **cfg["extra_params"],
    }
    resp = requests.post(
        f"{cfg['base_url']}/chat/completions",
        headers={"Authorization": f"Bearer {os.environ[cfg['key_env']]}"},
        json=payload,
        timeout=90,
    )
    if resp.status_code == 429:
        retry_after = float(resp.headers.get("retry-after", "10"))
        raise RateLimited(retry_after, resp.text[:300])
    if resp.status_code in (400, 401, 403, 404):
        # permanent errors (bad model name, bad key): retrying cannot fix these
        raise NonRetryable(f"{provider} HTTP {resp.status_code}: {resp.text[:400]}")
    if resp.status_code >= 400:
        raise RuntimeError(f"{provider} HTTP {resp.status_code}: {resp.text[:400]}")
    data = resp.json()
    text = data["choices"][0]["message"].get("content") or ""
    usage = data.get("usage", {})
    return text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)


def _call_anthropic(model: str, system_prompt: str, user_prompt: str, max_tokens: int):
    import anthropic

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model, max_tokens=max_tokens, system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return text, resp.usage.input_tokens, resp.usage.output_tokens


class NonRetryable(Exception):
    pass


class RateLimited(Exception):
    def __init__(self, retry_after: float, detail: str):
        super().__init__(detail)
        self.retry_after = retry_after


def call_llm_structured(
    skill: str,
    system_prompt: str,
    user_prompt: str,
    prompt_version: str,
    model_tier: str = "small",
    max_tokens: int = 1200,
    max_retries: int = 10,
    mock: bool | None = None,
) -> dict:
    """Calls the active provider."""
    request_id = str(uuid.uuid4())
    provider = resolve_provider(skill, mock)
    # the model can be overridden with an env variable
    model = (f"{model_tier} [MOCK]" if provider == "mock"
             else os.environ.get(f"{provider.upper()}_MODEL_{model_tier.upper()}") or PROVIDERS[provider]["models"][model_tier])

    start = time.time()
    input_tokens = output_tokens = 0
    raw_text = None
    result = None
    last_error = None
    attempts = 0

    if provider == "mock":
        time.sleep(0.02)
        result = _mock_response(skill, user_prompt)
        raw_text = json.dumps(result)
        input_tokens, output_tokens = len(user_prompt.split()), len(raw_text.split())
    else:
        for attempt in range(max_retries):
            attempts = attempt + 1
            try:
                _throttle(provider)
                if PROVIDERS[provider]["kind"] == "anthropic":
                    raw_text, input_tokens, output_tokens = _call_anthropic(model, system_prompt, user_prompt, max_tokens)
                else:
                    raw_text, input_tokens, output_tokens = _call_openai_compat(provider, model, system_prompt, user_prompt, max_tokens)
                result = _parse_json(raw_text)
                last_error = None
                break
            except NonRetryable as e:
                last_error = str(e)
                break
            except RateLimited as e:
                last_error = f"rate_limited: {e}"
                time.sleep(min(e.retry_after + 1, 90))
            except json.JSONDecodeError as e:
                last_error = f"invalid_json: {e}"
                time.sleep(1)
            except Exception as e:
                last_error = f"{type(e).__name__}: {e}"
                # server overloads (429/5xx) on free tiers are usually brief; wait progressively longer
                time.sleep(min(5 * (attempt + 1), 60))

    latency_ms = int((time.time() - start) * 1000)
    cost, priced = _estimate_cost(model, input_tokens, output_tokens)

    record = {
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "skill": skill,
        "prompt_version": prompt_version,
        "provider": provider,
        "model": model,
        "request": {"system_prompt": system_prompt, "user_prompt": user_prompt},
        "response": raw_text,
        "latency_ms": latency_ms,
        "attempts": attempts,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
        "cost_priced": priced,
        "status": "success" if result is not None else "failed",
        "error_type": last_error,
        "decision": result,
    }
    _log_trace(record)

    if result is None:
        raise RuntimeError(f"LLM call failed after {max_retries} attempts ({provider}/{model}): {last_error}")

    result["_provider"] = provider
    result["_model"] = model
    return result
