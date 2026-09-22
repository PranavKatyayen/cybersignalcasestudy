"""Implementation of the org-classification skill described in skills/org-classification/SKILL.md."""

import json
from pathlib import Path

from app.backend.llm_client import call_llm_structured
from app.backend.prompts import active_version, load_system_prompt

# default = the version that won the last eval; override with PROMPT_VERSION_ORG_CLASSIFICATION
PROMPT_VERSION = active_version("org_classification", "v2")
MODEL_TIER = "small"  # cheap model tier

CACHE_PATH = Path(__file__).resolve().parent / "org_cache.json"

# Answers learned from the model
LEARNED_CACHE_PATH = Path(__file__).resolve().parent / "org_learned_cache.json"
_learned_cache: dict | None = None


def _load_learned_cache() -> dict:
    global _learned_cache
    if _learned_cache is None:
        _learned_cache = json.loads(LEARNED_CACHE_PATH.read_text()) if LEARNED_CACHE_PATH.exists() else {}
    return _learned_cache


def save_learned_cache():
    """Persists the in-memory learned cache to disk."""
    if _learned_cache is not None:
        LEARNED_CACHE_PATH.write_text(json.dumps(_learned_cache, indent=2, sort_keys=True))

def _load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text())
    return {}


def classify_org(org_name: str, mock: bool = None, use_cache: bool = True, prompt_version: str = None,
                 allow_llm: bool = True) -> dict:
    """Says if an org is infrastructure or a real business (checks the caches first)."""
    if not org_name:
        return {"classification": "infra", "confidence": 1.0, "reasoning": "empty org treated as unattributable", "source": "rule"}

    key = org_name.strip().lower()
    version = prompt_version or PROMPT_VERSION
    learned = _load_learned_cache()
    if use_cache:
        for cached_key, cached_val in _load_cache().items():
            if cached_key in key:
                return {**cached_val, "source": "cache"}
        if key in learned:
            return {**learned[key], "source": "learned_cache"}

    if not allow_llm:
        # The model is reserved for decisions that change the outcome
        return {"classification": "unknown", "confidence": 0.0,
                "reasoning": "not classified: LLM reserved for inclusion decisions", "source": "skipped"}

    user_prompt = f'Organization name: "{org_name}"\n\nClassify this organization.'
    result = call_llm_structured(
        skill="org_classification",
        system_prompt=load_system_prompt("org_classification", version),
        user_prompt=user_prompt,
        prompt_version=version,
        model_tier=MODEL_TIER,
        max_tokens=350,  # replies are ~100 tokens
        mock=mock,
    )
    result["source"] = "llm"
    # never let offline mock guesses poison the persistent cache real runs read from
    if use_cache and result.get("_provider") != "mock" and version == PROMPT_VERSION:
        learned[key] = {k: v for k, v in result.items() if k != "source"}
        if len(learned) % 20 == 0:
            save_learned_cache()  # free-tier quotas can cut a run short
    return result
