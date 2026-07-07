# agentic-job-hunter — run guide (Claude Code & Codex)

This file lets **Claude Code** and **Codex** run the job hunt the same way the
Copilot `job-hunter` agent does. The canonical rules, scoring rubric, data
formats, and compliance policy live in
[.github/copilot-instructions.md](.github/copilot-instructions.md) — read it first
and follow it exactly. **Track-only: never auto-apply, never suggest it.**

## When the user says "run the job hunt"

1. Read `inbox/input.md`. The **Résumé** is everything below the
   `--- PASTE RESUME BELOW THIS LINE ---` marker; if it's empty, stop and ask the
   user to paste it. The **Preferences** section drives targeting. (`runtime:` is
   just how the user launched you — ignore it while executing.)
2. Run the four steps in order, pausing to summarize after each. Each step has a
   detailed prompt in `.github/prompts/`:
   - **map** → `.github/prompts/map.prompt.md` → writes `data/companies.md`.
   - **source** → `.github/prompts/source.prompt.md` → registers jobs with
     `python scripts/ats_fetch.py <kind> <slug> --senior --save --company "<Company>"`
     and generates search links with `python scripts/make_search_links.py`.
   - **ingest** → `.github/prompts/ingest.prompt.md` → only if `inbox/jobs.md`
     has pasted jobs.
   - **rank** → `.github/prompts/rank.prompt.md` → score each job against the
     résumé, then `python scripts/build_html.py`.
3. Tell the user to open `output/ranking.html` (ranked table + an **Advanced**
   panel of LinkedIn/Indeed/Google search links).

## Scripts (stdlib Python, run from repo root)

| script | purpose |
|--------|---------|
| `scripts/ats_fetch.py` | read Greenhouse/Lever/Ashby/SmartRecruiters/Workday; `--save` registers roles |
| `scripts/make_search_links.py` | build LinkedIn/Indeed/Google search links from preferences |
| `scripts/build_html.py` | build `output/ranking.html` |
| `scripts/run.py` | headless runner for the `api` runtime |

Be honest about weak fits (skills > seniority > location > salary). Read only
companies' own career sites / public ATS; never scrape LinkedIn/Indeed — generate
search links instead.
