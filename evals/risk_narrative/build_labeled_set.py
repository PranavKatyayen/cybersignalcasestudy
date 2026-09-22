#!/usr/bin/env python3
"""Builds evals/risk_narrative/labeled_set.jsonl by sampling real entities from data/curated/entities.jsonl

Usage:
python evals/risk_narrative/build_labeled_set.py
"""

import json
from pathlib import Path

ENTITIES_PATH = Path(__file__).resolve().parents[2] / "data" / "curated" / "entities.jsonl"
OUTPUT_PATH = Path(__file__).resolve().parent / "labeled_set.jsonl"

TARGET_PER_CATEGORY = 4
MAX_EXAMPLES = 28

# Same severity ordering as SEVERITY_WEIGHTS in scoring.py
SEVERITY_ORDER = [
    ("compromise", "compromised_or_c2"),
    ("active c2", "compromised_or_c2"),
    ("cve", "vulns_present"),
    ("risky service exposed", "risky_port"),
    ("end-of-life software", "eol_product"),
    ("iot/camera device", "iot_camera"),
    ("self-signed", "self_signed"),
    ("open directory", "open_dir"),
]


def critical_index_and_category(findings: list[str]) -> tuple[int, str]:
    best_rank, best_idx, best_cat = 999, 0, "other"
    for i, f in enumerate(findings):
        f_lower = f.lower()
        for rank, (kw, cat) in enumerate(SEVERITY_ORDER):
            if kw in f_lower and rank < best_rank:
                best_rank, best_idx, best_cat = rank, i, cat
                break
    return best_idx, best_cat


def main():
    entities = []
    with open(ENTITIES_PATH) as f:
        for line in f:
            entities.append(json.loads(line))

    print(f"Loaded {len(entities)} entities from {ENTITIES_PATH}")

    by_category: dict[str, list[dict]] = {}
    for e in entities:
        findings = e.get("top_findings", [])
        if not findings:
            continue
        idx, cat = critical_index_and_category(findings)
        by_category.setdefault(cat, []).append({**e, "critical_index": idx, "critical_category": cat})

    print("Category distribution in curated data:")
    for cat, items in sorted(by_category.items(), key=lambda kv: -len(kv[1])):
        print(f"  {cat:20} {len(items)}")

    selected = []
    for cat, items in by_category.items():
        # prefer a mix of HIGH and MEDIUM confidence within each category
        high = [e for e in items if e["attribution_confidence"] == "HIGH"]
        med = [e for e in items if e["attribution_confidence"] == "MEDIUM"]
        take = []
        i = 0
        while len(take) < TARGET_PER_CATEGORY and (i < len(high) or i < len(med)):
            if i < len(high):
                take.append(high[i])
            if len(take) < TARGET_PER_CATEGORY and i < len(med):
                take.append(med[i])
            i += 1
        selected.extend(take[:TARGET_PER_CATEGORY])

    selected = selected[:MAX_EXAMPLES]
    print(f"\nSelected {len(selected)} examples across {len(by_category)} categories")

    with open(OUTPUT_PATH, "w") as f:
        for e in selected:
            f.write(json.dumps({
                "entity_key": e["entity_key"],
                "attribution_confidence": e["attribution_confidence"],
                "provider_roles": e["provider_roles"],
                "total_score": e["total_score"],
                "asset_count": e["asset_count"],
                "countries": e["countries"],
                "top_findings": e["top_findings"],
                "critical_index": e["critical_index"],
                "critical_category": e["critical_category"],
            }) + "\n")

    print(f"Wrote {len(selected)} labeled examples -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
