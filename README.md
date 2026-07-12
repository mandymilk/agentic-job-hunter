# agentic-job-hunter

**English** · [简体中文](README.zh-CN.md)

Turn your résumé into a **ranked, clickable shortlist of jobs** from reputable
companies — with ready-to-click search links for everything we can't auto-source.

- **No-code:** paste a résumé, run the agent, open an HTML file.
- **Honest matching:** scored against *your* résumé **and your preferences** — it
  matches the JD's **actual requirements**, not just tech keywords (e.g. a *"0→1
  launch"* ask is checked against whether you've built something from scratch; a
  *"manage a team of PMs"* ask against real people-management), then seniority,
  location, and salary. Weak fits rank low, and only what changed gets re-scored.
- **Compliant & track-only:** reads companies' own career sites and public ATS
  boards, plus LinkedIn's public jobs-guest board for **personal use only** (needs
  [`bun`](https://bun.sh)); generates search links for Indeed/other aggregators
  instead of scraping them. **Never auto-applies.**

## Quickstart — you only do 2 things

Everything you edit lives in **one file**: [`inbox/input.md`](inbox/input.md).

1. **Edit `inbox/input.md`:**
   - Set `runtime:` to how you want to run it (`copilot` · `claude` · `codex` · `api`).
   - Edit the **Preferences** (titles, locations, industries, blocked companies…).
   - **Paste your résumé** below the `--- PASTE RESUME BELOW THIS LINE ---` marker.

   _(Want to try it instantly? Copy [`samples/input.sample.md`](samples/input.sample.md)
   to `inbox/input.md`.)_
2. **Run it** the way that matches your `runtime` (see the table below). Not sure?
   Run `python scripts/run.py` — it reads your choice and tells you the exact next step.

Then open **`output/ranking.html`**: a ranked, filterable table (click a row for the
full evaluation + JD) with an **Advanced** panel of ready-to-click LinkedIn / Indeed /
Google searches.

### Run it — pick your runtime

| `runtime:` | How to run | What drives it |
|------------|-----------|----------------|
| `copilot` | In VS Code, open Copilot Chat, choose the **`job-hunter`** agent, say *"run the job hunt"* | [`.github/`](.github) prompts + agent |
| `claude`  | Open this repo in **Claude Code**, say *"run the job hunt"* | [`CLAUDE.md`](CLAUDE.md) |
| `codex`   | Open this repo in **Codex**, say *"run the job hunt"* | [`AGENTS.md`](AGENTS.md) |
| `api`     | Headless: `export OPENAI_API_KEY=…` then `python scripts/run.py` | [`scripts/run.py`](scripts/run.py) |

The **approach is identical** everywhere — the same 4-step flow (map → source →
ingest → rank). Only the driver differs.

## Your flow, step by step

1. **Set up** — in `inbox/input.md`: choose a `runtime`, fill in **Preferences**,
   and paste your **résumé** below the marker.
2. **map** — the agent builds a *strategic* target-company list → `data/companies.md`
   (see the strategy below).
3. **source** — reads each company's **public ATS** and registers the senior roles
   that fit; for boards it can't read, it generates ready-to-click search links.
4. **ingest** *(optional)* — normalizes any jobs you pasted into `inbox/jobs.md`
   (e.g. from LinkedIn/Indeed — see below).
5. **rank** — scores every job against *your* résumé and builds
   **`output/ranking.html`**.
6. **review & iterate** — open the HTML, sort/filter, click a row for the full
   evaluation + JD, and use the **Advanced** panel to search other boards. Paste
   more jobs or tweak preferences and re-run — only what changed is re-scored.

### 🎯 The target-company list is a *strategy*, not a scrape

The **map** step doesn't dump random companies — it builds a deliberate shortlist
in `data/companies.md`:

- **Reputability bar** — only public/well-known companies, or startups recently
  backed by a top-tier investor (a16z, Sequoia, Benchmark, Accel, Lightspeed,
  Tiger, Index, GV…). No obscure names.
- **Fit to *you*** — matched to your résumé + preferences (industries, role
  archetypes, locations). It always includes your **preferred/seed companies** and
  never surfaces your **blocked** ones.
- **A readable source per company** — each row is tagged with a `tier`
  (`ats` · `browser` · `walled` · `manual`) and a `source` (e.g. `greenhouse:stripe`)
  so sourcing knows exactly how to read it.
- **Bounded runtime** — set **`Max companies`** and **`Max roles per company`** in
  your preferences to cap how much gets sourced and scored (defaults: 30 and 10).
  This matters most for the `api` runtime, where each job costs one scoring call.

Edit `data/companies.md` freely to steer the hunt, then re-run `source` → `rank`.

### 📋 Found a job on LinkedIn / Indeed? Paste it and it still gets scored

We never scrape LinkedIn/Indeed/aggregators — but you can bring any job to the
matcher yourself. Open **`inbox/jobs.md`**, paste the posting, and run **ingest**
(the `api` runtime does this automatically). It's then scored against your résumé
and ranked right alongside the auto-sourced roles, with the same honest rubric.

```
## Job
URL: https://www.linkedin.com/jobs/view/1234567890
Description: <paste the full job description here>
---
```

Tip: URL-only is fine for a scrapeable company career page (ingest will fetch the
JD); walled aggregators like LinkedIn need the full **Description** pasted. The
**Advanced** panel in `output/ranking.html` gives you pre-filled LinkedIn / Indeed /
Google searches to find these quickly.

### ⏭️ Already have a target list? Skip sourcing entirely

If you already know the jobs you want, you don't need the **map** and **source**
steps at all. Just paste each posting into **`inbox/jobs.md`** (block format above),
then run only **ingest → rank**. Every pasted job is scored against your résumé +
preferences and gets its own **tailored résumé summary** — same output, without the
company-finding steps.

## How it works

```
                    ┌─ Preferences ─┐
inbox/input.md ─────┤               ├─▶ map ──▶ data/companies.md (tier + source per company)
   (runtime +       └─ Résumé ──────┘             │
    prefs + résumé)                      source ──┼─▶ readable boards → data/jobs/ registry
                                                  └─▶ walled/aggregators → data/manual-search-links.md
                                        │ (you paste JDs) ▶ inbox/jobs.md ─▶ ingest
                                        ▼
                          rank ──▶ data/results/ + output/ranking.html
```

The agent orchestrates; deterministic work is done by stdlib Python in `scripts/`:

| script | what it does |
|--------|--------------|
| `run.py` | single entrypoint — reads `runtime:` and routes (runs the flow for `api`) |
| `ats_fetch.py` | read Greenhouse / Lever / Ashby / SmartRecruiters / Workday boards (`--save` registers roles) |
| `linkedin_source.py` | source LinkedIn's **public jobs-guest** board (personal-use; needs [`bun`](https://bun.sh)) |
| `make_search_links.py` | generate LinkedIn / Indeed / Google search links from prefs |
| `browser_fetch.py` | *optional* Playwright helper for JS/DOM boards (`pip install playwright`) |
| `score.py` | *optional* headless scoring with `OPENAI_API_KEY` (agent does this by default) |
| `build_html.py` | build the visual `output/ranking.html` |

Run any script from the repo root, e.g.:

```bash
python scripts/run.py                         # route based on inbox/input.md
python scripts/ats_fetch.py greenhouse stripe --senior --save --company Stripe
python scripts/linkedin_source.py             # personal-use; needs bun
python scripts/make_search_links.py
python scripts/build_html.py
```

`--save` registers matched roles straight into the registry with idempotent,
collision-safe ids (re-runs never duplicate; same-title roles are disambiguated by
location); add `--json` for machine-readable output.

## Matching without the agent (optional)

The `api` runtime (`python scripts/run.py` with `OPENAI_API_KEY` set) runs the whole
flow headlessly. To only re-score, run `python scripts/score.py` then
`python scripts/build_html.py`.

## Compliance & safety

Reads companies' **own** career sites and **public ATS** endpoints. It does **not**
bypass anti-bot challenges. **LinkedIn is the one deliberate exception:**
`scripts/linkedin_source.py` reads LinkedIn's **public jobs-guest** board via the
vendored `tools/linkedin-cli/` (needs [`bun`](https://bun.sh)) — this is
**personal-use only**, since automated access is against LinkedIn's ToS, so keep
volume low and non-commercial (it self-skips when `bun` is absent). For Indeed and
other aggregators it still only generates **search links**. **Track-only:** nothing
is ever auto-submitted. The optional `browser_fetch.py` is for company career sites
only; you accept ToS/fragility risk.

Your résumé stays local. MIT licensed — see [LICENSE](LICENSE).
