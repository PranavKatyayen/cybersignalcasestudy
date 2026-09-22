# CyberSignal - external exposure intelligence for cybersecurity sales

Ranks businesses by verifiable, externally visible security weaknesses (known CVEs, exposed risky services, end-of-life
software, weak certificates), so a sales team knows **who to call first, why, and what to say**.

Live app: https://cybersignal-web.vercel.app

## What it does

- **Ranked account list** with priority tiers (CRITICAL / HIGH / MEDIUM / LOW), attribution confidence and filters.
- **Account pages** with an AI sales brief (model and prompt version shown), the evidence behind the score, and per-asset detail.
- **Ask CyberSignal**: a grounded chat assistant that answers only from the account data (the AI never writes SQL).
- **Traces page**: every LLM call is logged; the page summarises calls, latency and paid-equivalent cost.

## How it is built (short)

```
raw internet-scan sample -> Python: rules score accounts; LLM classifies ambiguous org names
   -> LLM writes one cited brief per account (offline, once) -> Snowflake RAW -> dbt (staging/intermediate/marts)
   -> Next.js app on Vercel (reads the marts; chat calls Gemini with Groq as backup)
```

Design principles: rules decide scores, the LLM only handles genuine ambiguity and writing; every LLM call is traced;
prompts are versioned files that the code actually loads; every LLM skill has a labelled eval and a one-command harness.

## Repository map

| Path | What it is |
|---|---|
| `app/backend/` | Python engine: provider-agnostic LLM client, prompt loader, attribution + scoring rules, the two AI skills |
| `app/frontend/` | Next.js 16 app (dashboard, account pages, traces, chat API + widget) |
| `scripts/` | Pipeline steps: score, generate briefs, Snowflake setup + fast stage/COPY load, dbt runner, trace summary |
| `dbt_project/` | Snowflake transformations and data-quality tests |
| `prompts/` | Versioned prompts (v1, v2 per skill); the code loads these files |
| `skills/` | `SKILL.md` specs for `org-classification` and `risk-narrative` |
| `evals/` | Labelled sets, harnesses and real results for org classification, briefs, and the chat assistant |
| `data/curated/` | Pipeline outputs that were loaded into Snowflake |
| `traces/` | Aggregate + sample of the LLM call log (the full log stays local) |
| `docs/` | Planning, architecture and the how-I-built-this reflection (Markdown, with Word versions in `docs/word/`) |

## Documentation

- [`docs/planning.md`](docs/planning.md) - the use cases chosen and why, what was left out, how it maps to B2B prospecting
- [`docs/architecture.md`](docs/architecture.md) - how the pieces fit, the rule-vs-LLM split, design decisions and trade-offs, the cost model and ceiling
- [`docs/how_i_built_this.md`](docs/how_i_built_this.md) - dev loop and tools, where AI helped and cost more, one weakness to flag
- Word versions of the three: [`docs/word/`](docs/word/)

## Quick start

```bash
pip install -r requirements.txt
copy .env.example .env            # fill in Snowflake + at least one LLM key (Gemini or Groq are free)
python scripts/run_snowflake_setup.py
python scripts/export_curated_dataset.py --input sample.jsonl     # score accounts (needs the raw scan sample)
python scripts/generate_narratives.py                              # resumable; free tiers may need a second day
python scripts/load_curated_to_snowflake.py
python scripts/run_dbt.py run && python scripts/run_dbt.py test

python evals/org_classification/run_eval.py --prompt-version v2 --compare-to results/v1_groq_gpt-oss-20b.json
python evals/risk_narrative/run_eval.py --prompt-version v2 --compare-to results/v1_groq_gpt-oss-120b.json

cd app/frontend
copy .env.local.example .env.local   # SNOWFLAKE_SCHEMA=ANALYTICS, plus GEMINI_API_KEY / GROQ_API_KEY
npm install && npm run dev           # http://localhost:3000
```

LLM provider is chosen per skill (`LLM_PROVIDER_<SKILL>`), then globally (`LLM_PROVIDER`), else the default in
`app/backend/llm_client.py`. Without any key the code falls back to an offline mock that is always labelled as mock.

## Honest limits

- The dataset is a single ~12-minute scan snapshot: no trend or change claims are made anywhere.
- Scores measure *need* (visible weakness), not *fit* (company size, industry) or *intent*.
- Evals are small (25 and 23 labelled examples plus 12 chat questions); v2 prompts were written after seeing v1's failures on the
  same sets, and some checks are keyword-based. Results and caveats are in `skills/*/SKILL.md` and `evals/*/results/`.
- Development ran on free LLM tiers, which cap requests and tokens per day; the pipeline is resumable for that reason.
