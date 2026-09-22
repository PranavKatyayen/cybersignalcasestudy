# Loom walkthrough script (target: 4:30)

Speak in your own words; these are beats, not lines to read.

## 0:00 - 0:30 | The problem and the surprise
- The brief said "company data". The dataset was actually an internet-wide network scan (one record per IP/port), not a company list.
- I checked timestamps first: single ~12-minute snapshot, so no trend claims anywhere in the product.
- So I built CyberSignal: rank businesses by verifiable external security exposure.

## 0:30 - 1:30 | The live app (cybersignal-web.vercel.app)
- Dashboard: 417 attributed accounts, tiers computed in dbt, click CRITICAL to filter.
- Open duolingo.com: AI Sales Brief, then "Why am I seeing this" with the cited finding highlighted, then the per-asset evidence table.
- Say plainly: every score traces to a CVE, port or tag. The LLM never sets the score.

## 1:30 - 2:30 | Rules vs LLM split
- Rules: CVEs, risky ports, EOL software, self-signed certs, domain filtering, provider_role.
- LLM, two jobs only: classify an org name as infra vs business; write the sales narrative.
- Narratives are pre-generated offline, so the web app makes zero LLM calls and cost is predictable.

## 2:30 - 3:30 | AI scaffolding (show the repo)
- skills/ (2 SKILL.md), prompts/ (versioned), evals/ (labelled sets + one-command harness with --compare-to).
- Run `python evals/risk_narrative/run_eval.py` live. Explain the metrics: citation validity, critical-finding coverage, fabricated CVE/port check.
- Traces page: every call logged with model, prompt version, latency, cost.

## 3:30 - 4:15 | How I built it with Claude Code
- Real bugs caught by running things: setup script silently skipping statements, org classifier re-asking the LLM about the same org (1,046 calls down to 497 on the same slice), dbt schema naming, Snowflake VARIANT parsing.
- Say honestly: several were tool gotchas I verified rather than already knew.

## 4:15 - 4:30 | Known weakness
- Citation checks catch fabricated CVEs/ports, not subtle overclaiming in prose. A judge pass would cost another call per account; I documented it instead of pretending it's solved.
- Disclose: if the numbers shown are mock mode, say so on camera.
