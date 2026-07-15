---
mode: agent
description: Source jobs from readable boards into the registry; generate manual search links for the rest.
---

Read `data/companies.md`. **Re-scrape every readable company on every run** —
work through **all** companies whose `tier` is `ats` or `browser`, not just those
with `status: pending`. Already-scraped companies (`scraped:<N>`) keep getting new
roles posted, so always re-fetch them; `register_job` is idempotent and only adds
new/changed postings, so re-scraping never duplicates. Update each company's
`status` to the fresh `scraped:<N>` / `no-matches` count after the run. Only
`walled` / `manual` tiers are left for manual paste.
Load **Blocked companies** from the Preferences section of `inbox/input.md` and skip them.

For each company, by `tier`:

- **ats** — preview with `scripts/ats_fetch.py <kind> <slug> --senior` (kind/slug
  from `source`); add `--json` to inspect full JD text. When the roles look right,
  register them in one shot with
  `scripts/ats_fetch.py <kind> <slug> --senior --save --company "<Company>"`.
  `--save` is idempotent and collision-safe: it generates a unique id per posting
  (disambiguating same-title roles by location), keeps each job's original
  `first_seen`, updates a detail file + `jd_hash` only when the JD actually
  changed, skips postings with no JD text, and never creates duplicate rows on
  re-runs. To bound runtime, keep at most **Max roles per company** (default ~10)
  per board — pass `--limit <N>` to cap what gets registered. Set the company
  `status` to `scraped:<N>` or `no-matches`.
- **browser** — try `scripts/browser_fetch.py`: `render <url>` for DOM-readable
  boards, or `api <url> <api-substring>` to read the page's own jobs API. Parse
  the matching senior roles and register them (see below). If nothing readable,
  set `walled`. Never forge signed requests or bypass anti-bot challenges.
- **walled** / **manual** — do not scrape. Leave for manual paste.

**LinkedIn (default-on, personal-use).** Independently of the per-company tiers,
run `python scripts/linkedin_source.py` once. It searches your Preferences'
titles × locations against LinkedIn's **public jobs-guest** board (via the
vendored CLI in `tools/linkedin-cli/`, which needs `bun`), pulls each posting's
full JD, and registers senior matches with the same idempotent `register_job`.
⚠️ **Personal use only** — automated access is against LinkedIn's ToS; keep
volume low and non-commercial. If `bun` isn't installed the script skips itself
and tells the user to rely on `make_search_links.py` instead. Preview without
registering via `--json`; cap per search with `--limit <N>`; restrict recency
with `--jobage <days>`. This does **not** change scoring/ranking.

**Register a role manually** (browser/ingest paths, when `--save` isn't used):
- `id = slug(company)-slug(title)` (disambiguate with a location or `-2` suffix if
  it collides — or just call `register_job(...)` from `scripts/lib.py`, which does
  this for you).
- Write `data/jobs/details/<id>.md`: frontmatter (`id`, `url`, `company`,
  `location`, `source_site`, `first_seen` = today) + `## Description` + full JD.
- Add a row to `data/jobs/index.md` with `status: new` and compute
  `jd_hash` = first 8 chars of `shasum data/jobs/details/<id>.md`.

Then generate manual search links: run `python scripts/make_search_links.py`
(writes `data/manual-search-links.md` from preferences + walled companies).

Summarize: companies scraped (+counts), companies now `walled`/`manual`, and tell
the user they can paste JDs from `data/manual-search-links.md` into `inbox/jobs.md`.
