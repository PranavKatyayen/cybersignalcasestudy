#!/usr/bin/env python3
"""Eval for the technology extractor: runs the rules over the labelled records and scores them.
No model is called, so it is free and takes about a second.

Usage:
python evals/technology_extraction/run_eval.py --label v1_seed --origins seed
python evals/technology_extraction/run_eval.py --label v2_seed_plus_discovered --compare-to results/v1_seed.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from app.backend.pipeline.technology import extract, load_rules

LABELED_SET = HERE / "labeled_set.jsonl"
RESULTS_DIR = HERE / "results"


def score(origins: tuple[str, ...]) -> dict:
    rules = load_rules(origins)
    tp = fp = fn = 0
    version_total = version_ok = exact = 0
    records = []
    for line in open(LABELED_SET, encoding="utf-8"):
        example = json.loads(line)
        predicted = {}
        for hit in extract(example["record"], rules):
            predicted.setdefault(hit["technology"], set())
            if hit["version"]:
                predicted[hit["technology"]].add(hit["version"])
        expected = {e["technology"]: e["version"] for e in example["expected"]}
        missed = sorted(set(expected) - set(predicted))
        extra = sorted(set(predicted) - set(expected))
        tp += len(set(expected) & set(predicted))
        fn += len(missed)
        fp += len(extra)
        exact += not missed and not extra
        wrong_versions = []
        for tech, version in expected.items():
            if version and tech in predicted:
                version_total += 1
                if version in predicted[tech]:
                    version_ok += 1
                else:
                    wrong_versions.append({"technology": tech, "expected": version, "got": sorted(predicted[tech])})
        records.append({"id": example["id"], "missed": missed, "extra": extra, "wrong_versions": wrong_versions})
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "examples": len(records),
        "true_positives": tp, "false_positives": fp, "false_negatives": fn,
        "precision": round(precision, 4), "recall": round(recall, 4),
        "f1": round(2 * precision * recall / (precision + recall), 4) if precision + recall else 0.0,
        "version_accuracy": round(version_ok / version_total, 4) if version_total else None,
        "versions_checked": version_total,
        "exact_match_rate": round(exact / len(records), 4),
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True, help="Name for this run, used as the results file name")
    parser.add_argument("--origins", default="seed,discovered", help="Which rules to use: seed, discovered or both")
    parser.add_argument("--compare-to", default=None, help="Previous results JSON to diff against")
    args = parser.parse_args()

    origins = tuple(args.origins.split(","))
    result = {"skill": "technology_extraction", "label": args.label, "rules_used": origins,
              "timestamp": datetime.now().isoformat(timespec="seconds"), **score(origins)}
    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"{args.label}.json"
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"{args.label}  rules: {', '.join(origins)}  ({result['examples']} labelled records)")
    print(f"precision {result['precision']:.1%}  recall {result['recall']:.1%}  f1 {result['f1']:.1%}  "
          f"exact-match {result['exact_match_rate']:.1%}  version accuracy "
          f"{result['version_accuracy']:.1%} of {result['versions_checked']}")
    print(f"missed {result['false_negatives']}  extra {result['false_positives']}")
    for r in result["records"]:
        if r["missed"] or r["extra"] or r["wrong_versions"]:
            print(f"  #{r['id']}: missed {r['missed']} extra {r['extra']} versions {r['wrong_versions']}")
    print(f"\nResults written to {out}")

    if args.compare_to:
        prev_path = Path(args.compare_to)
        prev_path = prev_path if prev_path.is_absolute() else HERE / prev_path
        if prev_path.exists():
            prev = json.loads(prev_path.read_text(encoding="utf-8"))
            print(f"\n--- {prev['label']} -> {args.label} ---")
            for metric in ("precision", "recall", "f1", "exact_match_rate"):
                print(f"{metric}: {prev[metric]:.1%} -> {result[metric]:.1%}  ({result[metric] - prev[metric]:+.1%})")
            before = {r["id"]: set(r["missed"]) | set(r["extra"]) for r in prev["records"]}
            for r in result["records"]:
                now = set(r["missed"]) | set(r["extra"])
                if now != before.get(r["id"], set()):
                    print(f"  #{r['id']}: errors {sorted(before.get(r['id'], set()))} -> {sorted(now)}")


if __name__ == "__main__":
    main()
