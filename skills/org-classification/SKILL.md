# SKILL: org-classification

## Purpose
Classify a network-scan record's organization name (WHOIS/ASN "org" field) as
either `infra` (a hosting/cloud/CDN/telecom provider) or `end_business` (a
real company that can be treated as a sales prospect). This is the gate that
decides whether a scanned asset is attributable to a specific prospect at
all -- infra-classified orgs are excluded from the prospect pipeline entirely
because their IP ranges serve many unrelated third parties.

## Trigger Conditions
Run this skill when:
- A new, previously unseen `org` string appears in the ingestion pipeline
  (i.e. it is not already present in the deterministic fast-path cache --
  see `cache/known_orgs.json`)
- A human reviewer flags a prior classification as wrong (triggers
  re-classification + cache update)

Do NOT run this skill when:
- The org string matches an entry already in the fast-path cache (~40 known
  global providers hardcoded for zero-cost, zero-latency classification --
  see `app/backend/org_cache.json`). This keeps LLM spend focused on the
  genuinely ambiguous long tail instead of re-classifying "Amazon.com, Inc."
  on every single record.

## Inputs
| Field | Type | Description |
|---|---|---|
| `org_name` | string | Raw `org` field value from the scan record |

## Outputs
```json
{
  "classification": "infra" | "end_business",
  "confidence": 0.0-1.0,
  "reasoning": "one short sentence"
}
```

## Dependent Prompt
`prompts/org_classification/v1.md` and `v2.md`. The code loads the prompt from these files
(`app/backend/prompts.py`); **v2 is the default** because it measured better (see Evaluation).
Model tier: **small** -- a cheap model, because this is a narrow classification. The pipeline
run that produced the shipped data used **Gemini `gemini-3.5-flash-lite`** (default); the eval was also run on Groq
`openai/gpt-oss-20b`. The provider is swappable (Gemini / Groq / Anthropic) in `app/backend/llm_client.py`, which maps the
tier to a concrete model.

## Routing Logic After This Skill Runs
- `confidence >= 0.85` → trust the label automatically
- `0.60 <= confidence < 0.85` → trust the label but flag for periodic audit
- `confidence < 0.60` → route to human review queue rather than auto-decide

## Worked Example Invocation
```python
from app.backend.skills.org_classification import classify_org

result = classify_org("Sakura Internet Inc.")
# -> {"classification": "infra", "confidence": 0.93,
#     "reasoning": "Sakura Internet is a major Japanese cloud/hosting provider."}
```

## Evaluation
- Labelled set: `evals/org_classification/labeled_set.jsonl` (25 hand-labelled real org names)
- Harness: `evals/org_classification/run_eval.py` -- always calls the model directly (caches
  bypassed) so it measures the model and prompt, not the hardcoded provider list.
- Run: `python evals/org_classification/run_eval.py --prompt-version v2 --compare-to results/v1_groq_gpt-oss-20b.json`
- **Measured results (real models, 25 examples):**

| Prompt | Accuracy | end_business precision / recall | infra precision / recall |
|---|---|---|---|
| v1 (Groq gpt-oss-20b) | 80.0% (20/25) | 60.0% / 85.7% | 93.3% / 77.8% |
| v2 (Groq gpt-oss-20b) | 92.0% (23/25) | 85.7% / 85.7% | 94.4% / 94.4% |
| v2 (Gemini 3.5-flash-lite) | 92.0% (23/25) | 85.7% / 85.7% | 94.4% / 94.4% |

  v2 fixed all three large-cloud-provider misses (Google, Amazon, Microsoft) and broke nothing.
- Why accuracy is not the gating metric: real traffic is mostly infra, so a model that always
  says "infra" scores well while finding no prospects. end_business precision and recall are the
  numbers that matter.
- Caveat: v2 was written after reading v1's misses on this same 25-example set, so the gain
  is partly fitted to it; the rules are general (no test company is named) but a fresh held-out
  set would be needed to prove it.

## Known Failure Mode (documented, not hidden)
Measured on the real model, not assumed:
- **Small hosting providers with generic company-style names** (`A100 ROW GmbH`) are still
  misclassified as end_business, at 0.90 confidence even in v2 -- the "cap confidence when the
  name gives no signal" rule did not take effect on this example. Mitigation in the pipeline: the
  hardcoded provider list and domain rules catch known cases; the rest is a documented weakness.
- **Debatable label:** `CENCOM INC` is labelled end_business by us but the model reads it as a
  telecom; the label may be the error. Both v1 and v2 disagree with it.
- The model classifies from the name only (no live lookup), so ambiguous names stay ambiguous.

