#!/usr/bin/env python3
"""One-time, model-assisted discovery of technology rules. The model proposes; a person reviews; rules do the work.

Usage:
python scripts/discover_tech_rules.py --input sample.jsonl     # ask the model about strings no rule covers yet
python scripts/discover_tech_rules.py --review                 # print every proposal
python scripts/discover_tech_rules.py --apply                  # merge reviewed proposals into tech_rules.json
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.backend.llm_client import resolve_provider
from app.backend.pipeline.attribution import attribute_without_llm
from app.backend.pipeline.technology import RULES_PATH, load_rules, save_rules, unmapped
from app.backend.skills.technology_discovery import PROMPT_VERSION, classify_batch, validate_decisions

PROPOSALS_PATH = Path(__file__).resolve().parents[1] / "data" / "curated" / "tech_rules_proposed.json"
SIGNAL_FIELD = {"components": "components", "cpe": "cpe", "products": "products", "server_headers": "server_headers"}


def load_proposals() -> dict:
    if PROPOSALS_PATH.exists():
        return json.loads(PROPOSALS_PATH.read_text(encoding="utf-8"))
    return {"prompt_version": PROMPT_VERSION, "decisions": {}}


def save_proposals(data: dict):
    PROPOSALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROPOSALS_PATH.write_text(json.dumps(data, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def collect_unmapped(input_path: str) -> list[dict]:
    """Strings of accounts' records that no rule recognises, most common first, with one example each."""
    rules = load_rules()
    counts, examples = Counter(), {}
    with open(input_path, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not attribute_without_llm(rec):
                continue
            for kind, value, original in unmapped(rec, rules):
                counts[(kind, value)] += 1
                examples.setdefault((kind, value), original)
    return [{"kind": k, "value": v, "records": n, "example": examples[(k, v)]} for (k, v), n in counts.most_common()]


def discover(args):
    if resolve_provider("technology_discovery") == "mock":
        sys.exit("No real model available (no API key). Discovery needs a real model, so nothing was written.")
    proposals = load_proposals()
    decided = proposals["decisions"]
    pending = [u for u in collect_unmapped(args.input) if f"{u['kind']}|{u['value']}" not in decided]
    categories = load_rules().categories
    print(f"{len(pending)} strings still need a decision ({len(decided)} already decided)")
    batches = [pending[i:i + args.batch_size] for i in range(0, len(pending), args.batch_size)]
    for number, chunk in enumerate(batches[: args.max_batches], 1):
        items = [{"id": i, "kind": u["kind"], "value": u["value"], "records": u["records"], "example": str(u["example"])[:80]}
                 for i, u in enumerate(chunk)]
        try:
            result = classify_batch(items, categories)
        except RuntimeError as e:
            print(f"Stopped at batch {number}: {e}\nProgress is saved. Run the same command later to continue.")
            break
        answers = validate_decisions(result.get("items"), items, categories)
        for i, unit in enumerate(chunk):
            if i not in answers:
                continue  # no usable answer: asked again next run
            decided[f"{unit['kind']}|{unit['value']}"] = {
                **answers[i], "kind": unit["kind"], "value": unit["value"], "records": unit["records"],
                "example": str(unit["example"])[:80], "rejected": False, "provider": result.get("_provider"),
                "model": result.get("_model"), "prompt_version": PROMPT_VERSION,
            }
        save_proposals(proposals)
        print(f"batch {number}/{min(len(batches), args.max_batches or len(batches))}: {len(answers)}/{len(items)} usable answers")


def review():
    decisions = load_proposals()["decisions"].values()
    kept = sorted((d for d in decisions if d["keep"]), key=lambda d: (d["technology"], d["kind"]))
    dropped = [d for d in decisions if not d["keep"]]
    print(f"{len(kept)} proposed rules, {len(dropped)} strings the model chose to ignore\n")
    for d in kept:
        flag = "REJECTED " if d["rejected"] else ""
        print(f"{flag}{d['kind']:<15} {d['value']:<40} -> {d['technology']} [{d['category']}] ({d['records']} records)")
    print("\nIgnored by the model:", ", ".join(f"{d['value']} ({d['records']})" for d in sorted(dropped, key=lambda d: -d["records"])[:40]))


def apply():
    data = json.loads(Path(RULES_PATH).read_text(encoding="utf-8"))
    known = {name.lower(): name for section in ("seed", "discovered") for name in data.get(section, {})}
    added = 0
    for d in load_proposals()["decisions"].values():
        if not d["keep"] or d["rejected"]:
            continue
        name = known.get(d["technology"].lower(), d["technology"])
        known[name.lower()] = name
        entry = data["discovered"].setdefault(name, {"category": d["category"], "vendor": d["vendor"]})
        values = entry.setdefault(SIGNAL_FIELD[d["kind"]], [])
        if d["value"] not in values:
            values.append(d["value"])
            added += 1
    save_rules(data)
    print(f"Merged {added} signal values into the 'discovered' section of {RULES_PATH.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", help="Path to a scan-data JSONL file")
    parser.add_argument("--batch-size", type=int, default=40)
    parser.add_argument("--max-batches", type=int, default=None)
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.review:
        review()
    elif args.apply:
        apply()
    elif args.input:
        discover(args)
    else:
        parser.error("give --input, --review or --apply")


if __name__ == "__main__":
    main()
