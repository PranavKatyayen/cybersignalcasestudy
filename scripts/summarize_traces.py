#!/usr/bin/env python3
"""Builds the small data files the Traces page reads from the local traces/llm_calls.jsonl.

Usage:
python scripts/summarize_traces.py
"""

import json
import shutil
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.backend.llm_client import MODEL_PRICING

TRACE_LOG_PATH = ROOT / "traces" / "llm_calls.jsonl"
OUT_DIR = ROOT / "traces"
SITE_DATA_DIR = ROOT / "app" / "frontend" / "data"
EXAMPLE_TEXT_LIMIT = 6000


def load_calls():
    calls = []
    with open(TRACE_LOG_PATH, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            # calls logged before a model had a known price are re-priced from their token counts
            if not rec.get("cost_priced") and rec.get("model") in MODEL_PRICING:
                pin, pout = MODEL_PRICING[rec["model"]]
                rec["cost_usd"] = (rec.get("input_tokens", 0) / 1e6) * pin + (rec.get("output_tokens", 0) / 1e6) * pout
            calls.append(rec)
    return calls


def slim(rec):
    return {
        "id": rec.get("request_id", "")[:8],
        "ts": rec.get("timestamp", ""),
        "skill": rec.get("skill", "unknown"),
        "version": rec.get("prompt_version", "unknown"),
        "provider": rec.get("provider", "unknown"),
        "model": rec.get("model", "unknown"),
        "ms": rec.get("latency_ms") or 0,
        "tin": rec.get("input_tokens") or 0,
        "tout": rec.get("output_tokens") or 0,
        "cost": round(rec.get("cost_usd") or 0, 6),
        "priced": bool(rec.get("cost_priced")) or rec.get("model") in MODEL_PRICING,
        "status": rec.get("status", "unknown"),
        "attempts": rec.get("attempts") or 1,
        "error": rec.get("error_type"),
    }


def totals(calls):
    n = len(calls)
    ok = sum(1 for c in calls if c.get("status") == "success")
    return {
        "total_calls": n,
        "total_cost_usd": round(sum(c.get("cost_usd") or 0 for c in calls), 4),
        "avg_latency_ms": round(sum(c.get("latency_ms") or 0 for c in calls) / n, 1) if n else 0,
        "success_count": ok,
        "failed_count": n - ok,
    }


def examples(calls):
    """One successful call per skill and prompt version, with the full request and response."""
    best = {}
    for rec in calls:
        if rec.get("status") != "success" or not rec.get("request"):
            continue
        key = (rec.get("skill"), rec.get("prompt_version"))
        best[key] = rec  # keeps the most recent one
    out = []
    for (skill, version), rec in sorted(best.items()):
        s = slim(rec)
        s["request"] = str(rec.get("request"))[:EXAMPLE_TEXT_LIMIT]
        s["response"] = str(rec.get("response"))[:EXAMPLE_TEXT_LIMIT]
        out.append(s)
    return out


def eval_summary():
    rows = []
    for path in sorted((ROOT / "evals").glob("*/results/*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        if "skill" in d and "prompt_version" in d:
            metrics = {k: v for k, v in d.items() if isinstance(v, (int, float)) and k not in ("timestamp",)}
            rows.append({"skill": d["skill"], "version": d["prompt_version"], "provider": d.get("provider"),
                         "model": d.get("model"), "metrics": metrics, "file": path.name})
        elif path.name == "latest.json" and "summary" in d:
            rows.append({"skill": "chat_assistant", "version": "-", "provider": None, "model": None,
                         "metrics": {k: v for k, v in d["summary"].items() if isinstance(v, (int, float))}, "file": path.name})
    return rows


def main():
    calls = load_calls()
    stats = totals(calls)
    by_skill = defaultdict(list)
    for c in calls:
        by_skill[c.get("skill", "unknown")].append(c)
    stats["by_skill"] = {k: {"calls": len(v), **{x: y for x, y in totals(v).items() if x in ("total_cost_usd", "avg_latency_ms")}} for k, v in by_skill.items()}

    outputs = {
        "trace_stats.json": stats,
        "trace_calls.json": [slim(c) for c in calls],
        "trace_examples.json": examples(calls),
        "eval_summary.json": eval_summary(),
    }
    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in outputs.items():
        (OUT_DIR / name).write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
        shutil.copy(OUT_DIR / name, SITE_DATA_DIR / name)
        print(f"Wrote {name} ({(OUT_DIR / name).stat().st_size // 1024} KB)")
    print(f"{stats['total_calls']} calls, paid-equivalent ${stats['total_cost_usd']}, copied to {SITE_DATA_DIR}")


if __name__ == "__main__":
    main()
