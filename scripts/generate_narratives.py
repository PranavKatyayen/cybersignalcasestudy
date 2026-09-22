#!/usr/bin/env python3
"""Generates a risk narrative for every curated entity and writes data/curated/narratives.jsonl

Usage:
python scripts/generate_narratives.py
python scripts/generate_narratives.py --limit 20     # quick smoke test
python scripts/generate_narratives.py --fresh        # ignore previous progress
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.backend.skills.risk_narrative import generate_narrative, PROMPT_VERSION

ENTITIES_PATH = Path(__file__).resolve().parents[1] / "data" / "curated" / "entities.jsonl"
OUTPUT_PATH = Path(__file__).resolve().parents[1] / "data" / "curated" / "narratives.jsonl"


def findings_hash(entity: dict) -> str:
    return hashlib.sha256(json.dumps(entity.get("top_findings", []), sort_keys=True).encode()).hexdigest()[:16]


def template_fallback(entity: dict) -> dict:
    findings = entity.get("top_findings", [])
    summary = f"{entity['entity_key']} has {len(findings)} security finding(s), including: {findings[0]}" if findings \
        else f"{entity['entity_key']} has no notable findings."
    return {
        "summary": summary,
        "outreach_angle": f"Ask about: {findings[0]}" if findings else "",
        "cited_evidence_indices": list(range(len(findings))),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--fresh", action="store_true", help="discard existing progress and start over")
    args = parser.parse_args()

    entities = [json.loads(l) for l in open(ENTITIES_PATH, encoding="utf-8")]
    if args.limit:
        entities = entities[: args.limit]

    done = {}
    if OUTPUT_PATH.exists() and not args.fresh:
        for l in open(OUTPUT_PATH, encoding="utf-8"):
            r = json.loads(l)
            if r.get("prompt_version") == PROMPT_VERSION and r.get("narrative_source") != "mock" and r.get("findings_hash"):
                done[(r["entity_key"], r["findings_hash"])] = r
    current = {(e["entity_key"], findings_hash(e)) for e in entities}
    done = {k: v for k, v in done.items() if k in current}  # drop briefs for accounts that no longer exist
    if args.fresh and OUTPUT_PATH.exists():
        OUTPUT_PATH.unlink()
    # rewrite the file with only the kept rows so a resumed run appends cleanly
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for r in done.values():
            f.write(json.dumps(r) + "\n")

    todo = [e for e in entities if e.get("top_findings") and (e["entity_key"], findings_hash(e)) not in done]
    print(f"{len(entities)} entities, {len(done)} already done, {len(todo)} to generate (prompt {PROMPT_VERSION})")
    start = time.time()
    fallback_count = 0

    with open(OUTPUT_PATH, "a", encoding="utf-8") as out:
        for i, entity in enumerate(todo, 1):
            try:
                result = generate_narrative(entity, mock=args.mock if args.mock else None)
            except RuntimeError as e:
                print(f"\nStopped after {i - 1} new narratives: {e}")
                print("Progress is saved. Re-run the same command later to continue.")
                break

            evidence = result.get("evidence", [])
            cited = result.get("cited_evidence_indices", [])
            valid_range = set(range(len(evidence)))
            citation_valid = len(evidence) > 0 and bool(cited) and all(isinstance(c, int) and c in valid_range for c in cited)

            provider = result.get("_provider", "unknown")
            if provider == "mock":
                narrative_source = "mock"
            elif citation_valid:
                narrative_source = "llm"
            else:
                narrative_source = "fallback_template"
                result = {**result, **template_fallback(entity)}
                fallback_count += 1

            out.write(json.dumps({
                "entity_key": entity["entity_key"],
                "summary": result["summary"],
                "outreach_angle": result["outreach_angle"],
                "cited_evidence_indices": result["cited_evidence_indices"],
                "narrative_source": narrative_source,
                "provider": provider,
                "model": result.get("_model"),
                "prompt_version": PROMPT_VERSION,
                "findings_hash": findings_hash(entity),
            }) + "\n")
            out.flush()

            if i % 25 == 0:
                print(f"  ...{i}/{len(todo)} ({time.time() - start:.0f}s)")

    total = sum(1 for _ in open(OUTPUT_PATH, encoding="utf-8"))
    print(f"\n{total} narratives in {OUTPUT_PATH}; {fallback_count} fell back to the safe template this run "
          f"({time.time() - start:.0f}s)")


if __name__ == "__main__":
    main()
