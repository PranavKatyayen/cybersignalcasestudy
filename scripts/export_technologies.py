#!/usr/bin/env python3
"""Extracts the technologies used by each account from the raw scan and writes data/curated/tech_evidence.jsonl.

Usage:
python scripts/export_technologies.py --input sample.jsonl
python scripts/export_technologies.py --input sample.jsonl --origins seed
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.backend.pipeline.attribution import attribute_without_llm
from app.backend.pipeline.technology import extract, load_rules, unmapped

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "data" / "curated"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to a scan-data JSONL file")
    parser.add_argument("--origins", default="seed,discovered", help="Which rules to use: seed, discovered or both")
    args = parser.parse_args()

    rules = load_rules(tuple(args.origins.split(",")))
    rows, accounts, with_tech, records, attributable = {}, set(), set(), 0, 0
    unmapped_counts = Counter()

    with open(args.input, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            records += 1
            entity_key = attribute_without_llm(rec)
            if not entity_key:
                continue
            attributable += 1
            accounts.add(entity_key)
            ip = rec.get("ip_str") or rec.get("ipv6")
            country = (rec.get("location") or {}).get("country_name")
            for kind, value, _ in unmapped(rec, rules):
                unmapped_counts[(kind, value)] += 1
            for hit in extract(rec, rules):
                with_tech.add(entity_key)
                key = (entity_key, hit["technology"], hit["source"], hit["version"], ip, rec.get("port"))
                rows[key] = {"entity_key": entity_key, **hit, "ip": ip, "port": rec.get("port"), "country": country}

    ordered = [rows[k] for k in sorted(rows, key=lambda k: tuple(str(x) for x in k))]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "tech_evidence.jsonl", "w", encoding="utf-8") as out:
        for row in ordered:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")

    catalog = rules.catalog()
    with open(OUTPUT_DIR / "tech_catalog.jsonl", "w", encoding="utf-8") as out:
        for row in catalog:
            out.write(json.dumps(row, ensure_ascii=False) + "\n")
    category_of = {c["technology"]: c["category"] for c in catalog}
    by_category = Counter(category_of[r["technology"]] for r in ordered)
    techs_per_account = defaultdict(set)
    for r in ordered:
        techs_per_account[r["entity_key"]].add(r["technology"])
    coverage = {
        "rules_used": args.origins,
        "records": records,
        "attributable_records": attributable,
        "accounts": len(accounts),
        "accounts_with_technology": len(with_tech),
        "evidence_rows": len(ordered),
        "distinct_technologies": len({r["technology"] for r in ordered}),
        "avg_technologies_per_account": round(sum(len(v) for v in techs_per_account.values()) / max(1, len(techs_per_account)), 1),
        "by_category": dict(by_category.most_common()),
        "unmapped_signal_values": len(unmapped_counts),
        "top_unmapped": [{"kind": k, "value": v, "records": n} for (k, v), n in unmapped_counts.most_common(25)],
    }
    (OUTPUT_DIR / "tech_coverage.json").write_text(json.dumps(coverage, indent=2), encoding="utf-8")

    print(f"{records} records, {attributable} attributable to {len(accounts)} accounts")
    print(f"{len(ordered)} evidence rows, {coverage['distinct_technologies']} technologies, "
          f"{len(with_tech)} accounts with at least one technology (avg {coverage['avg_technologies_per_account']})")
    print(f"{len(unmapped_counts)} signal values are not covered by any rule yet")
    print(f"Wrote tech_evidence.jsonl, tech_catalog.jsonl and tech_coverage.json in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
