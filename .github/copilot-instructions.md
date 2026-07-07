# agentic-job-hunter — agent instructions

> **Scope:** despite the filename, this is the **canonical spec for every runtime**,
> not just GitHub Copilot. Copilot auto-loads this file; **Claude Code** reaches it
> via [`CLAUDE.md`](../CLAUDE.md) and **Codex** via [`AGENTS.md`](../AGENTS.md)
> (both say "read it first and follow it exactly"); the **`api`** runtime runs the
> same flow in [`scripts/run.py`](../scripts/run.py). The flow, scoring rubric, data
> formats, and compliance rules below apply identically to all of them.

You help a user turn their resume into a ranked, clickable shortlist of jobs from
reputable companies. You orchestrate; Python scripts in `scripts/` do the
deterministic work (fetching, link generation, HTML). **Track-only: never
auto-apply, never suggest auto-applying.**

## The flow (4 steps)
1. **map** — read `inbox/input.md` (Preferences section + the résumé pasted below
   the marker) → write the target company list (`data/companies.md`) with a
   `tier` + `source` per company.
2. **source** — pull jobs from readable boards into the registry; generate
   `data/manual-search-links.md` for the rest.
3. **ingest** — normalize any jobs the user pasted into `inbox/jobs.md`.
4. **rank** — score every job and build `output/ranking.html`.

Each step has a prompt in `.github/prompts/`. The `job-hunter` agent can run them
end to end. The user picks how to run in `inbox/input.md` (`runtime:` =
copilot | claude | codex | api); `python scripts/run.py` routes accordingly.

## Scoring rubric (be honest)
Score each job against the candidate's **résumé + preferences** (both from
`inbox/input.md`). Priority order: **genuine skills/tech overlap** (no superficial
keyword matches) > **seniority & scope** > **location & work mode** > **salary if
stated**. Judge skills/seniority against the résumé; judge location/work-mode/salary
against the preferences. Weak fits must score low. Never invent experience the
candidate lacks. Re-score a job only when its `jd_hash` or the `resume_hash`
(profile hash = résumé + preferences) changed — otherwise reuse its result.

## Compliance
- Read only companies' **own** career sites and **public ATS** boards
  (Greenhouse/Lever/Ashby/SmartRecruiters/Workday). Prefer `scripts/ats_fetch.py`.
- For JS/DOM or page-fetched-API boards, `scripts/browser_fetch.py` (optional,
  Playwright) may render or capture the page's own API response — never forge
  signed requests, never bypass Cloudflare/DataDome challenges.
- **Never** scrape LinkedIn/Indeed/aggregators — generate search links instead
  (`scripts/make_search_links.py`).
- Never fabricate a JD. If you cannot read the real text, flag the company `walled`
  and rely on manual paste.

## Data formats
- `data/jobs/index.md`: `| id | company | title | location | url | jd_hash | first_seen | status |`
- `data/jobs/details/<id>.md`: frontmatter + `## Description` + full JD text.
- `data/results/<id>.md`: header `- score: N/100`, `- jd_hash:`, `- resume_hash:`,
  `- evaluated:` then `**Why:** **Matched:** **Gaps:** **Tailored summary:**`.
- `id = slug(company)-slug(title)`; `jd_hash = first 8 of sha1(detail file)`.

## Running scripts
`cd` to the repo root and run e.g. `python scripts/ats_fetch.py greenhouse stripe --senior`,
`python scripts/make_search_links.py`, `python scripts/build_html.py`.
