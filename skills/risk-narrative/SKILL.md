# SKILL: risk-narrative

## Purpose
Turn one aggregated entity's structured, deterministic findings (exposure
score, findings list, provider role, attribution reasoning) into a short
narrative a salesperson can read in five seconds and immediately understand
why this account is worth calling, plus a suggested opening angle for
outreach. This is the only place in the pipeline where an LLM produces
free-text content shown directly to a human -- everything upstream of this
(attribution gate, exposure scoring) is deterministic rules.

## Trigger Conditions
Run this skill when:
- An entity has been scored and aggregated (`aggregate_entities()` in
  `app/backend/pipeline/scoring.py`) and has at least one finding in
  `top_findings`
- A salesperson opens an account detail view in the app and the narrative
  hasn't been generated/cached yet for the current findings set

Do NOT run this skill when:
- The entity has zero findings (nothing to narrate -- handled by a
  short-circuit in `generate_narrative()`, no LLM call made, zero cost)
- The findings for that entity haven't changed since the last narrative was
  generated (cache by entity_key + hash of top_findings, avoiding redundant
  spend on every dashboard page load)

## Inputs
| Field | Type | Description |
|---|---|---|
| `entity_key` | string | Domain or org identifying the account |
| `attribution_confidence` | "HIGH" \| "MEDIUM" | From the attribution layer |
| `provider_roles` | list[string] | e.g. `customer_hosted`, `self_hosted_or_direct` |
| `total_score` | int | Deterministic exposure score |
| `asset_count` | int | Number of scanned assets rolled into this entity |
| `countries` | list[string] | Observed geolocation(s) |
| `top_findings` | list[string] | The deterministic findings this narrative must be grounded in |

## Outputs
```json
{
  "summary": "2-3 sentence sales-readable narrative",
  "outreach_angle": "one sentence suggested opening angle",
  "cited_evidence_indices": [0, 2],
  "evidence": [{"index": 0, "text": "..."}, {"index": 1, "text": "..."}, ...]
}
```
`evidence` is not model output -- it's echoed back by
`generate_narrative()` so the caller (and the eval harness) can validate
`cited_evidence_indices` without recomputing the mapping.

## Dependent Prompt
`prompts/risk_narrative/v1.md` and `v2.md`; **v2 is the default**. Model tier: **large** -- this is
a writing/judgement task where failure (fabrication, overclaiming) matters more than a few cents.
The shipped briefs were written by Gemini (prompt v2): the first ~214 by `gemini-3.5-flash-lite`, the rest by `gemini-3.1-flash-lite`
after the first model's free daily quota (500 requests/day) ran out. Every brief records its model, and the app shows it. The prompt
comparison was measured on Groq `openai/gpt-oss-120b`; v2 was re-measured on both Gemini models.

## Routing Logic After This Skill Runs
Unlike org_classification, there is no confidence score to threshold on --
the risk here is fabrication, not miscalibration. Logic is a hard validity
gate, not a soft trust tier:
- Every index in `cited_evidence_indices` is checked to be a valid index into
  `evidence`. If any citation is out of range → **reject the narrative
  entirely** and fall back to a template-only summary built directly from
  `top_findings` (no LLM text shown to the salesperson for that account).
- If `cited_evidence_indices` is empty despite `evidence` being non-empty →
  same fallback (an ungrounded narrative is treated as equivalent to an
  invalid one).
- Passing validation does not guarantee the *prose* only contains cited
  facts -- see Known Failure Mode below.

## Worked Example Invocation
```python
from app.backend.skills.risk_narrative import generate_narrative

entity = {
    "entity_key": "example-corp.com",
    "attribution_confidence": "HIGH",
    "provider_roles": ["customer_hosted"],
    "total_score": 140,
    "asset_count": 3,
    "countries": ["United States"],
    "top_findings": [
        "Known CVE(s) present: CVE-2023-44487",
        "Risky service exposed on port 3389: RDP (Windows Remote Desktop)",
    ],
}
result = generate_narrative(entity)
# -> {"summary": "...", "outreach_angle": "...",
#     "cited_evidence_indices": [0, 1], "evidence": [...]}
```

## Evaluation
- Labelled set: `evals/risk_narrative/labeled_set.jsonl` (23 real entities sampled from the curated
  data, spanning both confidence tiers and every finding category present; `compromised_or_c2` has
  no example because this sample contains none). Built by `evals/risk_narrative/build_labeled_set.py`.
- Harness: `evals/risk_narrative/run_eval.py --prompt-version v2 --compare-to results/v1_groq_gpt-oss-120b.json`
- Generative task, so no precision/recall on prose. Checks run in code on every narrative:
  citation validity, coverage of the most severe finding, fabricated CVE/port tokens, unsupported
  consequence words ("steal", "breach", "leak"...), and third-person perspective.
- **Measured results (real models, 23 examples):**

| Metric | v1 (Groq 120b) | v2 (Groq 120b) | v2 (Gemini 3.5-flash-lite) | v2 (Gemini 3.1-flash-lite) |
|---|---|---|---|---|
| citation validity | 100% | 100% | 100% | 100% |
| most severe finding cited | 100% | 100% | 100% | 100% |
| no fabricated CVE/port | 100% | 100% | 100% | 100% |
| no unsupported consequence claims | 56.5% | 100% | 100% | 100% |
| describes the account (third person) | 78.3% | 100% | 100% | 100% |

- The 3.5-flash-lite column was recorded from a console run; its raw results file was overwritten by a later run with a name
  collision (fixed: filenames now include the model). Re-running it is pending free-quota reset.
- Caveat: v2 was written after reading v1's failures on these same 23 examples, and the
  overclaim/perspective checks are keyword and pattern based -- so 100% shows the prompt avoids
  those specific failures, not that prose quality is perfect.

## Known Failure Mode (documented, not hidden)
- Passing citation validation does not prove every sentence is grounded. The keyword overclaim
  check catches the failures observed in v1 ("data theft", "breach", "attackers can") but not every
  possible unsupported claim; a model-based judge pass would catch more at the cost of a second
  call per account. Documented, not built.
- The narrative model sees only the findings list, never the raw scan record: fabrication is
  structurally harder, at the price of briefs that are less specific than they could be.

