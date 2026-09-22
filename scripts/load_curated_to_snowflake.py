#!/usr/bin/env python3
"""Loads the local curated pipeline output (data/curated/*.jsonl) into Snowflake RAW tables

Usage:
python scripts/load_curated_to_snowflake.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.backend.config import SnowflakeConfig

CURATED_DIR = Path(__file__).resolve().parents[1] / "data" / "curated"

# target table -> (file, {column: expression over the staged JSON record $1})
LOADS = {
    "RAW.SCORED_ENTITIES": ("entities.jsonl", {
        "entity_key": "$1:entity_key::STRING",
        "attribution_confidence": "$1:attribution_confidence::STRING",
        "provider_roles": "$1:provider_roles",
        "attribution_reasons": "$1:attribution_reasons",
        "total_score": "$1:total_score::NUMBER",
        "asset_count": "$1:asset_count::NUMBER",
        "orgs": "$1:orgs",
        "countries": "$1:countries",
        "sample_ips": "$1:sample_ips",
        "top_findings": "$1:top_findings",
    }),
    "RAW.SCORED_ASSETS": ("assets.jsonl", {
        "entity_key": "$1:entity_key::STRING",
        "attribution_confidence": "$1:attribution_confidence::STRING",
        "provider_role": "$1:provider_role::STRING",
        "attribution_reason": "$1:attribution_reason::STRING",
        "org": "$1:org::STRING",
        "domain": "$1:domain::STRING",
        "ip": "$1:ip::STRING",
        "port": "$1:port::NUMBER",
        "product": "$1:product::STRING",
        "country": "$1:country::STRING",
        "raw_score": "$1:raw_score::NUMBER",
        "adjusted_score": "$1:adjusted_score::NUMBER",
        "findings": "$1:findings",
        "tags": "$1:tags",
    }),
    "RAW.ENTITY_NARRATIVES": ("narratives.jsonl", {
        "entity_key": "$1:entity_key::STRING",
        "summary": "$1:summary::STRING",
        "outreach_angle": "$1:outreach_angle::STRING",
        "cited_evidence_indices": "$1:cited_evidence_indices",
        "narrative_source": "$1:narrative_source::STRING",
        "provider": "$1:provider::STRING",
        "model": "$1:model::STRING",
        "prompt_version": "$1:prompt_version::STRING",
    }),
}


def load_table(conn, table: str, filename: str, columns: dict, source_dir: Path = CURATED_DIR):
    path = source_dir / filename
    expected = sum(1 for line in open(path, encoding="utf-8") if line.strip())
    stage_dir = f"@RAW.CURATED_STAGE/{table.split('.')[1].lower()}"

    cur = conn.cursor()
    cur.execute(f"TRUNCATE TABLE {table}")
    cur.execute(f"PUT 'file://{path.as_posix()}' {stage_dir} AUTO_COMPRESS=FALSE OVERWRITE=TRUE")
    cols = ", ".join(columns)
    exprs = ", ".join(columns.values())
    cur.execute(
        f"COPY INTO {table} ({cols}) FROM (SELECT {exprs} FROM {stage_dir}/{filename}) "
        f"FILE_FORMAT = (FORMAT_NAME = 'RAW.JSON_FORMAT') FORCE = TRUE ON_ERROR = ABORT_STATEMENT"
    )
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    loaded = cur.fetchone()[0]
    if loaded != expected:
        raise RuntimeError(f"{table}: loaded {loaded} rows but {filename} has {expected}")
    print(f"Loaded {loaded} rows -> {table}")


def main():
    SnowflakeConfig.validate()
    import snowflake.connector

    conn = snowflake.connector.connect(
        account=SnowflakeConfig.ACCOUNT,
        user=SnowflakeConfig.USER,
        password=SnowflakeConfig.PASSWORD,
        role=SnowflakeConfig.ROLE,
        warehouse=SnowflakeConfig.WAREHOUSE,
        database=SnowflakeConfig.DATABASE,
        schema="RAW",
    )
    print(f"Connected to {SnowflakeConfig.ACCOUNT}, loading into {SnowflakeConfig.DATABASE}.RAW ...")

    for table, (filename, columns) in LOADS.items():
        if not (CURATED_DIR / filename).exists():
            print(f"Skipping {table}: {filename} not found")
            continue
        load_table(conn, table, filename, columns)

    conn.close()
    print("\nDone. Run `python scripts/run_dbt.py run` next to rebuild the dbt models on top of this.")


if __name__ == "__main__":
    main()
