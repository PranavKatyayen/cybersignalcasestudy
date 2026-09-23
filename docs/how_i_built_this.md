# How I built this

## Dev loop and tools

I ran this as the architect and reviewer.  I set the direction, requirements and constraints, and worked with Claude Code as my review and recommendation partner. It wrote most of the TypeScript for UI and some big python files. Next challenged was to understand the real data first, decide the design, have a small piece built, run it against real data, review the actual output, correct, repeat. Nothing counted as done until I had seen it working on the deployed app and in the traces.

## What I owned

- **Design constraints.** . What platform do we use? Real AI models only, no mock output, free tiers only, the 30,000-record sample as the final dataset, a chat assistant, prompt v1 versus v2, and the full request text in every trace.
- **The platform, hands-on.** I provisioned Snowflake (warehouse, database, schemas), created the repository, set up the Vercel project and its environment variables, and created the Gemini and Groq accounts and keys. I did not need AI for any of that.
- **Review and product calls.** I sent the first UI back and, after using the app, directed paging, search, filters, CSV export, the plain-language "why" tags and the billed-versus-paid cost view. I checked the build against the brief's criteria and asked what to improve.

## Where AI saved the most time

- **Reading the raw data.** It gave me idea what’s inside the 11+ GB file and scan out the useful part, which ruled out any trend feature early. Means in data strategy AI helped me.
- **Bugs found by measuring:** a setup script that silently skipped 6 of 12 SQL statements; repeated model calls for the same organization name (1,046 down to 497); scoring before attributing, which cut model calls by about 70%.
- **Eval design for free text.** Real-model runs showed v1 briefs claiming "data theft" (56.5% clean, 100% in v2).

## Where it cost more than doing it by hand

•	The first pass used an offline stand-in for the model. I rejected it and had real models wired in, which cost about a day.
•	Free-tier limits, underestimated twice (a daily token cap, and limits that charge for the requested reply size). That cost hours and forced design changes: resumable jobs, smaller replies, provider fallback.
•	Repository and deployment plumbing: Vercel created a second repository and early commits carried the wrong identity; I caught both and had them corrected. All deployment I had to lookout.
•	The ranking looked fine until I reviewed it: ISP and hosting machines sat at the top until a rule removed 106 such accounts, and the documents had to be regenerated to match.


## One weakness I would flag

The quality evidence is thinner than the product looks. The labelled sets are small (25 and 23 examples), the v2 prompts were written after seeing v1's failures on those same sets, and the brief check is keyword-based. The score also measures need only, not fit. Next steps: a held-out eval set and an LLM judge, then fit scoring once firmographic data is available.
