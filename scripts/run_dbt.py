#!/usr/bin/env python3
"""Runs dbt with credentials loaded from .env

Usage:
python scripts/run_dbt.py run
python scripts/run_dbt.py test
python scripts/run_dbt.py run --select staging
python scripts/run_dbt.py debug   # sanity-checks the Snowflake connection
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DBT_PROJECT_DIR = ROOT / "dbt_project"

load_dotenv(ROOT / ".env")


def find_dbt_executable() -> str:
    """pip installs dbt.exe into the Python install's Scripts/ dir, which is often not on PATH."""
    found = shutil.which("dbt")
    if found:
        return found

    candidate = Path(sys.executable).parent / ("Scripts" if os.name == "nt" else "bin") / ("dbt.exe" if os.name == "nt" else "dbt")
    if candidate.exists():
        return str(candidate)

    raise RuntimeError(
        "Could not find the dbt executable. Make sure `pip install -r requirements.txt` "
        "has been run, or add your Python Scripts directory to PATH."
    )


def main():
    env = os.environ.copy()
    env["DBT_PROFILES_DIR"] = str(DBT_PROJECT_DIR)

    dbt_exe = find_dbt_executable()
    result = subprocess.run(
        [dbt_exe] + sys.argv[1:],
        cwd=DBT_PROJECT_DIR,
        env=env,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
