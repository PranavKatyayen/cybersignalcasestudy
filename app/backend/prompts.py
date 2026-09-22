"""Loads versioned prompts from prompts/<skill>/<version>.md so the files ARE the source of truth."""

import os
import re
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def active_version(skill: str, default: str) -> str:
    """Prompt version to use: PROMPT_VERSION_<SKILL> env var if set, else the default."""
    return os.environ.get(f"PROMPT_VERSION_{skill.upper()}", default)


def available_versions(skill: str) -> list[str]:
    return sorted(p.stem for p in (PROMPTS_DIR / skill).glob("v*.md"))


def load_system_prompt(skill: str, version: str) -> str:
    path = PROMPTS_DIR / skill / f"{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"No prompt file {path}. Available: {available_versions(skill)}")
    text = path.read_text(encoding="utf-8")
    match = re.search(r"^## System Prompt\s*\n(.*?)(?=^## )", text, re.S | re.M)
    if not match:
        raise ValueError(f"{path} has no '## System Prompt' section")
    return match.group(1).strip()
