---
mode: agent
description: Normalize jobs pasted into inbox/jobs.md into the registry (no scoring).
---

Read `inbox/jobs.md`. If empty/placeholder, STOP and tell the user how to paste.
Load **Blocked companies** from the Preferences section of `inbox/input.md`.

For each job block (blocks separated by a line of three dashes):
1. If `Description` is empty but a `URL` is given for a scrapeable company career
   page, fetch the JD (`scripts/ats_fetch.py` or `scripts/browser_fetch.py`).
   If you can't get real JD text (walled aggregator), SKIP and flag it.
2. Infer `company` and `title`. Skip Blocked companies.
3. `id = slug(company)-slug(title)`. If new, write `data/jobs/details/<id>.md`
   (frontmatter + `## Description` + full JD) and add an `data/jobs/index.md` row
   with `status: new`; compute `jd_hash`. If it exists and the JD changed,
   overwrite the detail file (keep original `first_seen`).

When every block is registered, reset `inbox/jobs.md` to its template comment.
Report which ids were added/updated/skipped.
