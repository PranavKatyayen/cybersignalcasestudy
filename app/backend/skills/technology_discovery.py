"""Implementation of the technology-discovery skill described in skills/technology-discovery/SKILL.md."""

import json

from app.backend.llm_client import call_llm_structured
from app.backend.prompts import active_version, load_system_prompt

PROMPT_VERSION = active_version("technology_discovery", "v1")
MODEL_TIER = "large"  # a one-time judgement job over a few hundred strings


def classify_batch(items: list[dict], categories: list[str], mock: bool = None, prompt_version: str = None) -> dict:
    """Proposes a technology name, category and vendor for each unrecognised string."""
    version = prompt_version or PROMPT_VERSION
    user_prompt = json.dumps({"allowed_categories": categories, "items": items}, ensure_ascii=False)
    return call_llm_structured(
        skill="technology_discovery",
        system_prompt=load_system_prompt("technology_discovery", version),
        user_prompt=user_prompt,
        prompt_version=version,
        model_tier=MODEL_TIER,
        max_tokens=3500,  # about 40 items of roughly 40 tokens each, with room to spare
        mock=mock,
    )


def validate_decisions(raw_items: list, batch: list[dict], categories: list[str]) -> dict[int, dict]:
    """Keeps only well-formed decisions for ids we asked about. Anything else is dropped, never repaired."""
    asked = {item["id"] for item in batch}
    clean = {}
    for entry in raw_items if isinstance(raw_items, list) else []:
        if not isinstance(entry, dict) or entry.get("id") not in asked:
            continue
        keep = entry.get("keep") is True
        technology = entry.get("technology")
        category = entry.get("category")
        if keep and (not isinstance(technology, str) or not technology.strip() or category not in categories):
            keep = False
        vendor = entry.get("vendor") if isinstance(entry.get("vendor"), str) else None
        clean[entry["id"]] = {
            "technology": technology.strip() if keep else None,
            "category": category if keep else None,
            "vendor": vendor if keep else None,
            "keep": keep,
        }
    return clean
