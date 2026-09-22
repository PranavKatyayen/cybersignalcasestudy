"""Implementation of the risk-narrative skill described in skills/risk-narrative/SKILL.md."""

from app.backend.llm_client import call_llm_structured
from app.backend.prompts import active_version, load_system_prompt

# default = the version that won the last eval; override with PROMPT_VERSION_RISK_NARRATIVE
PROMPT_VERSION = active_version("risk_narrative", "v2")
MODEL_TIER = "large"  # judgment/writing task, not cheap classification

def _build_evidence_list(top_findings: list[str]) -> list[dict]:
    return [{"index": i, "text": f} for i, f in enumerate(top_findings)]


def _build_user_prompt(entity: dict) -> str:
    evidence = _build_evidence_list(entity.get("top_findings", []))
    evidence_block = "\n".join(f"[{e['index']}] {e['text']}" for e in evidence)
    return f"""Account: {entity.get('entity_key')}
Attribution confidence: {entity.get('attribution_confidence')}
Provider role(s): {', '.join(entity.get('provider_roles', []))}
Countries: {', '.join(entity.get('countries', [])) or 'unknown'}
Exposure score: {entity.get('total_score')} (higher = more urgent)
Assets observed: {entity.get('asset_count')}

EVIDENCE:
{evidence_block}

Write the narrative and outreach angle for this account."""


def generate_narrative(entity: dict, mock: bool = None, prompt_version: str = None) -> dict:
    """Writes the brief for one account and returns it with its evidence list."""
    evidence = _build_evidence_list(entity.get("top_findings", []))
    if not evidence:
        return {
            "summary": "No security-relevant findings to narrate for this account.",
            "outreach_angle": "",
            "cited_evidence_indices": [],
            "evidence": [],
        }

    version = prompt_version or PROMPT_VERSION
    user_prompt = _build_user_prompt(entity)
    result = call_llm_structured(
        skill="risk_narrative",
        system_prompt=load_system_prompt("risk_narrative", version),
        user_prompt=user_prompt,
        prompt_version=version,
        model_tier=MODEL_TIER,
        max_tokens=650,  # brief + reasoning fit well under this
        mock=mock,
    )
    result["evidence"] = evidence
    return result
