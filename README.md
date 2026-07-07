# agentic-job-hunter

**English** · [简体中文](README.zh-CN.md)

Turn your résumé into a **ranked, clickable shortlist of jobs** from reputable
companies — with ready-to-click search links for everything we can't auto-source.

- **No-code:** paste a résumé, run the agent, open an HTML file.
- **Honest matching:** scored against *your* résumé (skills > seniority > location
  > salary); weak fits rank low. Re-scores only what changed.
- **Compliant & track-only:** reads companies' own career sites and public ATS
  boards; generates search links for LinkedIn/Indeed instead of scraping them.
  **Never auto-applies.**

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
| `make_search_links.py` | generate LinkedIn / Indeed / Google search links from prefs |
| `browser_fetch.py` | *optional* Playwright helper for JS/DOM boards (`pip install playwright`) |
| `score.py` | *optional* headless scoring with `OPENAI_API_KEY` (agent does this by default) |
| `build_html.py` | build the visual `output/ranking.html` |

Run any script from the repo root, e.g.:

```bash
python scripts/run.py                         # route based on inbox/input.md
python scripts/ats_fetch.py greenhouse stripe --senior --save --company Stripe
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

Reads only companies' **own** career sites and **public ATS** endpoints. Does **not**
scrape LinkedIn/Indeed/aggregators or bypass anti-bot challenges — it generates
search links for those. **Track-only:** nothing is ever auto-submitted. The optional
`browser_fetch.py` is for company career sites only; you accept ToS/fragility risk.

Your résumé stays local. MIT licensed — see [LICENSE](LICENSE).
