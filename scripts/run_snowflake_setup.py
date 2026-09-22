#!/usr/bin/env python3
"""Creates the Snowflake database structure. Run once after filling in .env.

Usage:
python scripts/run_snowflake_setup.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.backend.config import SnowflakeConfig

def main():
    SnowflakeConfig.validate()

    import snowflake.connector

    print(f"Connecting to account: {SnowflakeConfig.ACCOUNT} as user: {SnowflakeConfig.USER} ...")
    conn = snowflake.connector.connect(
        account=SnowflakeConfig.ACCOUNT,
        user=SnowflakeConfig.USER,
        password=SnowflakeConfig.PASSWORD,
        role=SnowflakeConfig.ROLE,
    )
    print("Connected successfully.")

    sql_path = Path(__file__).resolve().parent / "snowflake_setup.sql"
    sql_text = sql_path.read_text()

    # Strip full-line comments BEFORE splitting on semicolons
    lines = [l for l in sql_text.split("\n") if not l.strip().startswith("--")]
    sql_text = "\n".join(lines)
    statements = [s.strip() for s in sql_text.split(";") if s.strip()]

    cur = conn.cursor()
    for i, stmt in enumerate(statements, 1):
        preview = stmt.split("\n")[0][:70]
        try:
            cur.execute(stmt)
            print(f"  [{i}] OK   -- {preview}")
        except Exception as e:
            print(f"  [{i}] FAIL -- {preview}\n        {e}")

    print("\nSetup run complete. Check for any FAIL lines above.")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
