#!/usr/bin/env python3
"""Runs the full local pipeline

Usage:
python scripts/export_curated_dataset.py --input /path/to/sample.jsonl
python scripts/export_curated_dataset.py --input /path/to/full_file.jsonl --limit 500000
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.backend.pipeline.scoring import score_record, aggregate_entities
from app.backend.skills.org_classification import save_learned_cache

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "curated"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to a scan-data JSONL file")
    parser.add_argument("--limit", type=int, default=None, help="Max records to process (omit for all)")
    parser.add_argument("--mock", action="store_true", help="Force mock mode for the LLM org-classification step")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    scored_assets = []
    processed = 0

    print(f"Reading: {args.input}")
    with open(args.input) as f:
        for line in f:
            if args.limit and processed >= args.limit:
                break
            processed += 1
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue

            s = score_record(rec, mock=args.mock if args.mock else None)
            if s:
                scored_assets.append(s)

            if processed % 5000 == 0:
                print(f"  ...{processed} records processed, {len(scored_assets)} scored assets so far")

    save_learned_cache()

    print(f"\nTotal records processed: {processed}")
    print(f"Scored assets (attributable + meaningful signal): {len(scored_assets)}")

    entities = aggregate_entities(scored_assets)
    print(f"Distinct attributed entities: {len(entities)}")

    assets_path = OUTPUT_DIR / "assets.jsonl"
    with open(assets_path, "w") as f:
        for a in scored_assets:
            f.write(json.dumps(a) + "\n")

    entities_path = OUTPUT_DIR / "entities.jsonl"
    with open(entities_path, "w") as f:
        for e in entities:
            f.write(json.dumps(e) + "\n")

    print(f"\nWrote {len(scored_assets)} assets -> {assets_path}")
    print(f"Wrote {len(entities)} entities -> {entities_path}")

    # quick summary breakdown, useful for the planning doc
    high = sum(1 for e in entities if e["attribution_confidence"] == "HIGH")
    med = sum(1 for e in entities if e["attribution_confidence"] == "MEDIUM")
    print(f"\nAttribution confidence breakdown: HIGH={high}, MEDIUM={med}")


if __name__ == "__main__":
    main()
