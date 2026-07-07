---
mode: agent
description: Source jobs from readable boards into the registry; generate manual search links for the rest.
---

Read `data/companies.md`. Work through companies whose `status` is `pending`.
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
