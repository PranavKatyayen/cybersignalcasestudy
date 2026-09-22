#!/usr/bin/env python3
"""One-command eval harness for the org_classification skill

Usage:
python evals/org_classification/run_eval.py --prompt-version v1
python evals/org_classification/run_eval.py --prompt-version v2 --compare-to results/v1_groq_gpt-oss-20b.json
python evals/org_classification/run_eval.py --mock        # offline plumbing check only
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app.backend.skills.org_classification import classify_org, PROMPT_VERSION

LABELED_SET_PATH = Path(__file__).resolve().parent / "labeled_set.jsonl"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def load_labeled_set():
    return [json.loads(line) for line in open(LABELED_SET_PATH, encoding="utf-8")]


def prf(predictions, labels, target):
    tp = sum(1 for p, l in zip(predictions, labels) if p == target and l == target)
    fp = sum(1 for p, l in zip(predictions, labels) if p == target and l != target)
    fn = sum(1 for p, l in zip(predictions, labels) if p != target and l == target)
    return {"tp": tp, "fp": fp, "fn": fn,
            "precision": tp / (tp + fp) if (tp + fp) else None,
            "recall": tp / (tp + fn) if (tp + fn) else None}


def pct(x):
    return f"{x:.1%}" if x is not None else "n/a"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-version", default=PROMPT_VERSION)
    parser.add_argument("--mock", action="store_true", help="Offline stand-in (plumbing check, NOT a quality number)")
    parser.add_argument("--compare-to", default=None, help="Previous results JSON to diff against")
    args = parser.parse_args()

    labeled = load_labeled_set()
    print(f"{len(labeled)} labelled examples | prompt {args.prompt_version} | "
          f"{'MOCK (not a real model)' if args.mock else 'real model'}\n")

    preds, labels, records = [], [], []
    start = time.time()
    provider = model = None
    for row in labeled:
        r = classify_org(row["org_name"], mock=True if args.mock else None, use_cache=False,
                         prompt_version=args.prompt_version)
        provider, model = r.get("_provider"), r.get("_model")
        pred = r["classification"]
        preds.append(pred)
        labels.append(row["expected"])
        records.append({"org_name": row["org_name"], "expected": row["expected"], "predicted": pred,
                        "confidence": r.get("confidence"), "reasoning": r.get("reasoning"),
                        "correct": pred == row["expected"]})
        flag = "ok   " if pred == row["expected"] else "MISS "
        print(f"  [{flag}] {row['org_name']:52} expected={row['expected']:12} got={pred:12} conf={r.get('confidence')}")

    n = len(records)
    acc = sum(r["correct"] for r in records) / n
    infra, biz = prf(preds, labels, "infra"), prf(preds, labels, "end_business")
    misses = [r for r in records if not r["correct"]]

    print(f"\n{'=' * 72}\nprovider={provider} model={model} prompt={args.prompt_version} ({time.time() - start:.0f}s)")
    print(f"accuracy {acc:.1%} ({n - len(misses)}/{n})")
    print(f"infra         precision {pct(infra['precision'])}  recall {pct(infra['recall'])}  (tp={infra['tp']} fp={infra['fp']} fn={infra['fn']})")
    print(f"end_business  precision {pct(biz['precision'])}  recall {pct(biz['recall'])}  (tp={biz['tp']} fp={biz['fp']} fn={biz['fn']})")
    if misses:
        print("\nMisses (these are the skill's documented weaknesses):")
        for m in misses:
            print(f"  - {m['org_name']}: expected {m['expected']}, got {m['predicted']} -- {m['reasoning']}")
    print("=" * 72)

    payload = {"skill": "org_classification", "prompt_version": args.prompt_version, "provider": provider,
               "model": model, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"), "accuracy": acc,
               "infra_metrics": infra, "end_business_metrics": biz, "records": records}
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
            print(f"accuracy: {prev['accuracy']:.1%} -> {acc:.1%}  ({acc - prev['accuracy']:+.1%})")
            for label, key, cur in (("end_business", "end_business_metrics", biz), ("infra", "infra_metrics", infra)):
                for m in ("precision", "recall"):
                    a, b = prev[key][m] or 0, cur[m] or 0
                    print(f"{label} {m}: {a:.1%} -> {b:.1%}  ({b - a:+.1%})")
            prev_missed = {r["org_name"] for r in prev["records"] if not r["correct"]}
            now_missed = {m["org_name"] for m in misses}
            print(f"fixed: {sorted(prev_missed - now_missed)}\nnewly broken: {sorted(now_missed - prev_missed)}")
        else:
            print(f"WARNING: {prev_path} not found")


if __name__ == "__main__":
    main()
