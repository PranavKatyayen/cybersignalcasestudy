# Planning: what I chose to build, and why

## The data decides the product

The supplied file is internet-scan data (one record per IP and port: banner, organization, location, software, CVEs), not a company list. I inspected a 30,000-record sample of the ~11 GB file before designing anything. Two findings shaped the product:

1. **It is a single ~12-minute snapshot** (14 September 2026). There is no history, so the product never claims a trend such as "exposure is getting worse".
2. **The usable signal is externally visible security exposure**, not company size, industry or funding. That gives *need* signals (a known CVE, end-of-life software, an exposed remote-access port), not *fit* or *intent* signals.

So the product is **CyberSignal: external exposure intelligence for a security sales team**.

## Use cases chosen

| # | The rep's question | What the product does | Rules or AI |
|---|---|---|---|
| 1 | Who do I call first? | A ranked, tiered list (CRITICAL to LOW) with search, country and confidence filters, paging and CSV export | Rules |
| 2 | Why this account? | The verified findings behind each score (CVEs, ports, end-of-life software) and how sure we are the business owns them | Rules |
| 3 | What do I say? | A 2-3 sentence brief and a suggested opening question, citing its evidence | AI, checked by code |
| 4 | Can I slice my list in plain words? | A chat assistant: the AI turns a question into filters; fixed SQL fetches the accounts; the answer uses only those rows | AI, guarded |

Each is a daily rep task and none needs data this file lacks. Cases 1-2 must be stable and explainable, so they are rules; cases 3-4 are language problems, where AI earns its cost.

## Considered and left out

- **Trends and "change over time":** one snapshot cannot support them.
- **Fit scoring (size, industry) and AI-set scores:** fit is not in the data (the first extension if enrichment existed); AI-set scores are unstable and impossible to explain to a rep.
- **The full 11 GB file, and auto-written emails:** the same rules would give a longer list, not a different product; emails carry more risk than value at this stage.

## How this maps to B2B prospecting practice

Sales teams define an ideal customer profile, score accounts on **fit** (size, industry) and on **signals** (buying or intent activity), tier them, and use territory filters to decide who sees what ([Gradient Works](https://www.gradient.works/resources/b2b-account-prioritization), [Demandbase](https://www.demandbase.com/faq/intent-signals/)).

| Common practice | What CyberSignal does | Honest gap |
|---|---|---|
| Account scoring | A deterministic exposure score from verifiable findings | Scores need, not fit: no company size or industry in the data |
| Buying signals | A known CVE, end-of-life software or an exposed remote-access port is a concrete reason to open a conversation | These are need signals, not intent signals |
| Tiering | CRITICAL, HIGH, MEDIUM, LOW from score thresholds, computed in dbt | Severity only, not fit times need |
| Territory filters | Country, confidence and keyword filters on the dashboard and in the chat | No industry or size segments |
| Outreach prioritisation | A ranked list, the evidence behind each score, and an AI brief with an opening question | No sequencing or multi-touch cadence |

## Success criteria

- A rep can act on an account within about ten seconds.
- Every claim traces to a piece of scan evidence.
- Each AI step has versioned prompts, an eval and a measured cost.
- The whole thing runs on free tiers.
