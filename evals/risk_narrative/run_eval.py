#!/usr/bin/env python3
"""One-command eval harness for the risk_narrative skill

Usage:
python evals/risk_narrative/run_eval.py --prompt-version v1
python evals/risk_narrative/run_eval.py --prompt-version v2 --compare-to results/v1_groq_gpt-oss-120b.json
python evals/risk_narrative/run_eval.py --mock       # offline plumbing check only
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.backend.skills.risk_narrative import generate_narrative, PROMPT_VERSION

LABELED_SET_PATH = Path(__file__).resolve().parent / "labeled_set.jsonl"
RESULTS_DIR = Path(__file__).resolve().parent / "results"

CVE_PATTERN = re.compile(r"CVE-\d{4}-\d+", re.IGNORECASE)
PORT_PATTERN = re.compile(r"\bport\s+(\d{2,5})\b", re.IGNORECASE)
# consequence claims a scan finding cannot prove on its own
OVERCLAIM_WORDS = ["steal", "stolen", "breach", "exfiltrat", "ransomware", "hacked", "data theft",
                   "actively exploited", "in the wild", "compromised", "attackers can", "leak"]
SECOND_PERSON = re.compile(r"\b(your|you're|you)\b", re.IGNORECASE)


def load_labeled_set():
    return [json.loads(line) for line in open(LABELED_SET_PATH, encoding="utf-8")]


def find_fabricated_facts(text: str, evidence_texts: list[str]) -> list[str]:
    blob = " ".join(evidence_texts)
    out = []
    for cve in CVE_PATTERN.findall(text):
        if cve.upper() not in blob.upper():
            out.append(f"CVE {cve} not present in evidence")
    for port in PORT_PATTERN.findall(text):
        if f"port {port}" not in blob.lower():
            out.append(f"port {port} not present in evidence")
    return out


def find_overclaims(text: str, evidence_texts: list[str]) -> list[str]:
    blob, low = " ".join(evidence_texts).lower(), text.lower()
    return [w for w in OVERCLAIM_WORDS if w in low and w not in blob]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-version", default=PROMPT_VERSION)
    parser.add_argument("--mock", action="store_true", help="Offline stand-in (plumbing check, NOT a quality number)")
    parser.add_argument("--compare-to", default=None, help="Previous results JSON to diff against")
    args = parser.parse_args()

    labeled = load_labeled_set()
    print(f"{len(labeled)} labelled examples | prompt {args.prompt_version} | "
          f"{'MOCK (not a real model)' if args.mock else 'real model'}\n")

    records, provider, model = [], None, None
    start = time.time()
    for row in labeled:
        entity = {k: row[k] for k in ("entity_key", "attribution_confidence", "provider_roles",
                                       "total_score", "asset_count", "countries", "top_findings")}
        result = generate_narrative(entity, mock=True if args.mock else None, prompt_version=args.prompt_version)
        provider, model = result.get("_provider"), result.get("_model")

        evidence = result.get("evidence", [])
        cited = result.get("cited_evidence_indices", [])
        valid = set(range(len(evidence)))
        invalid = [i for i in cited if i not in valid]
        summary, angle = result.get("summary", ""), result.get("outreach_angle", "")
        texts = [e["text"] for e in evidence]

        fabricated = find_fabricated_facts(f"{summary} {angle}", texts)
        overclaims = find_overclaims(f"{summary} {angle}", texts)
        second_person = bool(SECOND_PERSON.search(summary))

        rec = {
            "entity_key": row["entity_key"], "critical_category": row["critical_category"],
            "cited_evidence_indices": cited, "critical_index": row["critical_index"],
            "citation_valid": not invalid and bool(cited),
            "critical_cited": row["critical_index"] in cited,
            "fabricated_facts": fabricated, "overclaims": overclaims,
            "third_person": not second_person,
            "evidence_coverage": len(set(cited) & valid) / len(evidence) if evidence else None,
            "summary": summary, "outreach_angle": angle,
        }
        records.append(rec)
        ok = rec["citation_valid"] and rec["critical_cited"] and not fabricated and not overclaims and rec["third_person"]
        print(f"  [{'ok  ' if ok else 'FLAG'}] {row['entity_key']:38} cited={cited} crit={row['critical_index']} "
              f"fab={len(fabricated)} overclaim={overclaims} 3rd={rec['third_person']}")

    n = len(records)
    rate = lambda k: sum(1 for r in records if r[k]) / n
    metrics = {
        "citation_validity_rate": rate("citation_valid"),
        "critical_coverage_rate": rate("critical_cited"),
        "fabrication_free_rate": sum(1 for r in records if not r["fabricated_facts"]) / n,
        "overclaim_free_rate": sum(1 for r in records if not r["overclaims"]) / n,
        "third_person_rate": rate("third_person"),
    }
    cov = [r["evidence_coverage"] for r in records if r["evidence_coverage"] is not None]
    metrics["avg_evidence_coverage"] = sum(cov) / len(cov) if cov else None

    print(f"\n{'=' * 72}\nprovider={provider} model={model} prompt={args.prompt_version} ({time.time() - start:.0f}s, {n} examples)")
    for k, v in metrics.items():
        print(f"{k:26} {v:.1%}" if v is not None else f"{k:26} n/a")
    print("=" * 72)
    flagged = [r for r in records if r["overclaims"] or r["fabricated_facts"] or not r["third_person"]]
    for r in flagged[:6]:
        print(f"\nexample flag -- {r['entity_key']}: overclaims={r['overclaims']} fabricated={r['fabricated_facts']} "
              f"third_person={r['third_person']}\n  {r['summary']}")

    payload = {"skill": "risk_narrative", "prompt_version": args.prompt_version, "provider": provider, "model": model,
               "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), **metrics, "records": records}
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{args.prompt_version}_{provider}_{str(model).split('/')[-1]}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"\nResults written to {out}")

    if args.compare_to:
        prev_path = Path(args.compare_to)
        if not prev_path.is_absolute():
            prev_path = RESULTS_DIR.parent / prev_path
        if prev_path.exists():
            prev = json.loads(prev_path.read_text(encoding="utf-8"))
            print(f"\n--- {prev['prompt_version']} ({prev.get('model')}) -> {args.prompt_version} ({model}) ---")
            for k, v in metrics.items():
                if v is not None and prev.get(k) is not None:
                    print(f"{k:26} {prev[k]:.1%} -> {v:.1%}  ({v - prev[k]:+.1%})")
        else:
            print(f"WARNING: {prev_path} not found")


if __name__ == "__main__":
    main()
