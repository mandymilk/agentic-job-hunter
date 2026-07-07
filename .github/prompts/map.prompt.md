---
mode: agent
description: Map resume + preferences to a reputable target-company list, with a scrapeability tier and source per company.
---

Read `inbox/input.md`: the **Résumé** is everything below the
`--- PASTE RESUME BELOW THIS LINE ---` marker, and the **Preferences** section is
above it. If the résumé is empty/placeholder, STOP and ask the user to paste it.

Produce a **target company list** and write it to `data/companies.md` (keep the
header; one row per company):

`| company | tier | source | fit (why it matches you) | url | status |`

Rules:
1. **Reputability bar** — only public companies, well-known/established companies,
   or startups that recently raised from a famous investor (a16z, Sequoia,
   Benchmark, Accel, Lightspeed, Tiger, Index, GV, etc.). No obscure startups.
2. **Fit** — pick companies that match the resume + preferences (industries,
   role archetypes, locations). Honor **Blocked companies** (never list them) and
   **Preferred/seed companies** (always include if reputable).
3. **Resolve the source** for each company:
   - Find its official careers page or public ATS. Set `source` to the ATS + slug
     when known (`greenhouse:<slug>`, `lever:<slug>`, `ashby:<slug>`,
     `smartrecruiters:<slug>`, `workday:<tenant>:<site>`), else the careers URL.
   - Set `tier`: `ats` if a public ATS JSON exists; `browser` if it's JS/DOM or a
     page-fetched API; `walled` if bot-protected (Cloudflare/DataDome/signed);
     `manual` if you can't find an official source.
   - You may verify an ATS slug quickly with `scripts/ats_fetch.py <kind> <slug>`.
4. Set `status` to `pending` for all new rows.

Aim for ~20–40 well-chosen companies. Summarize the list and the tier breakdown.
