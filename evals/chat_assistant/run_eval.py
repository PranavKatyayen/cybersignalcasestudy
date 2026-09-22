#!/usr/bin/env python3
"""Eval for the chat assistant (Ask CyberSignal)

Usage:
python evals/chat_assistant/run_eval.py --url http://localhost:3000
"""
import argparse, json, re, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[2]
ENTITIES = {}
for line in open(ROOT / "data" / "curated" / "entities.jsonl", encoding="utf-8"):
    e = json.loads(line); ENTITIES[e["entity_key"]] = e
ALL_CVES = set(re.findall(r"CVE-\d{4}-\d+", " ".join(f for e in ENTITIES.values() for f in e["top_findings"])))

def tier_of(score): return "CRITICAL" if score >= 100 else "HIGH" if score >= 40 else "MEDIUM" if score >= 20 else "LOW"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--url", default="http://localhost:3000"); a = ap.parse_args()
    rows = [json.loads(l) for l in open(Path(__file__).parent / "questions.jsonl", encoding="utf-8")]
    results, t0 = [], time.time()
    for q in rows:
        try:
            r = requests.post(f"{a.url}/api/chat", json={"message": q["question"]}, timeout=90)
            d = r.json()
        except Exception as ex:
            d = {"error": str(ex)}
        answer = d.get("answer") or d.get("error") or ""
        accounts = d.get("accounts") or []
        rec = {"id": q["id"], "type": q["type"], "question": q["question"], "answer": answer,
               "accounts": [x["entity_key"] for x in accounts], "checks": {}}
        ck = rec["checks"]
        if q["type"] == "filter":
            exp, ok = q["expect"], True
            for x in accounts:
                e = ENTITIES.get(x["entity_key"])
                if not e: ok = False; continue
                if "tier" in exp and tier_of(e["total_score"]) != exp["tier"]: ok = False
                if "country" in exp and exp["country"] not in e["countries"]: ok = False
                if "confidence" in exp and e["attribution_confidence"] != exp["confidence"]: ok = False
                if "min_score" in exp and e["total_score"] < exp["min_score"]: ok = False
            ck["filter_correct"] = ok and len(accounts) > 0
        if q["type"] in ("filter", "general", "no_trend", "empty_ok"):
            named = [k for k in ENTITIES if len(k) > 5 and k in answer]
            ck["no_invented_account"] = all(k in rec["accounts"] for k in named) or not named
            ck["no_invented_cve"] = all(c in ALL_CVES for c in re.findall(r"CVE-\d{4}-\d+", answer))
        if q["type"] == "empty_ok":
            ck["no_unrelated_accounts_shown"] = len(accounts) == 0
        if q["type"] == "refuse":
            ck["refuses_off_topic"] = len(accounts) == 0 and "prospect accounts" in answer
        if q["type"] == "no_trend":
            low = answer.lower()
            ck["no_trend_claim"] = not any(w in low for w in ["is increasing", "are increasing", "has increased", "growing", "rising"]) or "single" in low or "snapshot" in low or "cannot" in low or "no " in low
        results.append(rec)
        print(f"[{q['id']}] {q['question'][:60]:60} -> {ck}")
        time.sleep(3)
    flat = [(k, v) for r in results for k, v in r["checks"].items()]
    summary = {}
    for name in sorted({k for k, _ in flat}):
        vals = [v for k, v in flat if k == name]
        summary[name] = sum(vals) / len(vals)
    print("\n" + "=" * 60)
    for k, v in summary.items(): print(f"{k:22} {v:.0%}")
    out = Path(__file__).parent / "results" / "latest.json"
    out.write_text(json.dumps({"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "url": a.url, "summary": summary, "results": results}, indent=2), encoding="utf-8")
    print(f"\nWrote {out} ({time.time()-t0:.0f}s)")

if __name__ == "__main__":
    main()
