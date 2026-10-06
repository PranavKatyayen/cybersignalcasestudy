# SKILL: technology-discovery

## Purpose
Help build the rule file that tells the pipeline which technologies an account runs. The scan contains many
technology strings (web components, vendor:product identifiers, banner names, HTTP server headers) but no
column that says "this company uses X". This skill looks at the strings that no rule recognises yet and
proposes a canonical technology name, a category and a vendor for each. A person reviews the proposals and
merges them into `app/backend/pipeline/tech_rules.json`. After that, extraction is plain rules: **the model is a
discovery aid, never a runtime dependency.**

## Trigger Conditions
Run this skill when:
- `scripts/export_technologies.py` reports signal values that no rule covers and you want to extend coverage
- The scan sample changes (a bigger file will contain strings the current rules have never seen)

Do NOT run this skill when:
- You only want to refresh the evidence: run `export_technologies.py`, which needs no model
- No real model is available. The script refuses to run in mock mode so nothing misleading is written

## Inputs
| Field | Type | Description |
|---|---|---|
| `allowed_categories` | list[string] | Read from `tech_rules.json`, so the rule file is the single source of truth |
| `items[].kind` | `components` \| `cpe` \| `products` \| `server_headers` | Where the string was found |
| `items[].value` | string | The normalised string, for example `openssl` or `awselb` |
| `items[].records` | int | How many scanned records contained it |
| `items[].example` | string | The original text, for context |

## Outputs
```json
{"items": [{"id": 0, "technology": "OpenSSL", "category": "Security", "vendor": "OpenSSL Project", "keep": true}]}
```
`validate_decisions()` keeps only well-formed answers for ids that were asked about: an unknown category or a
missing name turns `keep` off, and nothing is repaired. Decisions are saved in
`data/curated/tech_rules_proposed.json` with the provider, model and prompt version that made them.

## Dependent Prompt
`prompts/technology_discovery/v1.md`. Model tier: **large** (a one-time judgement over a few hundred strings, where a
wrong answer is worse than a missing one). Run on Gemini; every call goes through `llm_client.py`, so it is traced
and priced like the others.

## Routing Logic After This Skill Runs
1. `python scripts/discover_tech_rules.py --input sample.jsonl` asks the model about strings that are still undecided.
   It is resumable: progress is saved after every batch.
2. `python scripts/discover_tech_rules.py --review` prints every proposal.
3. **A person reviews them.** To reject or correct one, edit its entry in the proposals file (`"rejected": true`, or
   change `technology` / `category`) and add a `review_note`. The original value is kept.
4. `python scripts/discover_tech_rules.py --apply` merges the approved proposals into the `discovered` section of
   `tech_rules.json`. The hand-written `seed` section is never edited by the script.
5. `python scripts/export_technologies.py --input sample.jsonl` regenerates the evidence with no model.

## Example Invocation
Input item:
```json
{"id": 12, "kind": "server_headers", "value": "duo-api", "records": 1, "example": "duo-api"}
```
The model answered `Duo Security (Security)`. **That was wrong:** `duo-api` is the server header of Duolingo's own API,
not the security vendor. Review caught it and the proposal was rejected with a note. It is the reason the review step
exists.

## Evaluation
- Results are measured on the *rules it produced*, not on the model: `evals/technology_extraction/` has 38 labelled
  scan records and a free, model-free harness.
- Run: `python evals/technology_extraction/run_eval.py --label v2_seed_plus_discovered --compare-to results/v1_seed.json`
- **Measured:** seed rules alone F1 95.2% (recall 90.9%); seed plus reviewed discovered rules F1 99.4% (recall 98.9%,
  precision 100% in both). Technologies found grew from 93 to 262 and accounts with at least one technology from 1,925 to
  1,987 of 2,272.
- Discovery itself: 342 strings in 9 calls (about $0.04 at paid rates); the model kept 274 and declined 68 on purpose
  (for example `lego`, `jag`, `gvs`, `ghs`). Review rejected 11 and corrected 25.

## Known Failure Modes (documented, not hidden)
- **Confident wrong guesses on short or vendor-specific strings** (`duo-api`, `sma`, `volt-adc`, `ciscosystems`).
  Mitigation: the review step, and the prompt's "never guess" rule, which already made the model decline the most cryptic ones.
- **One-off device models** (`dahua dh-xvr1a08`) arrive as separate technologies; review rolls them up to the vendor.
- The labelled set is small and was a first pass written by reading banners and hostnames, and the scanner had already
  parsed most fields. It mainly guards normalization, versions and false positives.
- The one miss the eval had (WordPress seen only in a `Link: wp-json` header) is fixed by a `banner_patterns` rule: WordPress now appears in 72 scan records instead of 21 and the eval reaches 100%. The labelled record had also lost that header, so `build_labeled_set.py` now keeps `link:` lines. A 100% on 38 records is a regression guard, not proof of coverage.
