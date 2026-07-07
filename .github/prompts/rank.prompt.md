---
mode: agent
description: Score every job against the resume (incremental) and build the visual ranking.html.
---

Compute `resume_hash` = first 8 chars of sha1 of the **candidate profile** in
`inbox/input.md` — i.e. the résumé (below the `--- PASTE RESUME BELOW THIS LINE ---`
marker) **plus the Preferences section**, since scoring uses both. In Python:
`python -c "import sys;sys.path.insert(0,'scripts');from lib import profile_hash;print(profile_hash('.'))"`.

Decide which jobs need (re)evaluation: a job needs scoring if it has no
`data/results/<id>.md`, or its registry `jd_hash` differs from the one in its
result, or the current `resume_hash` differs from the one in its result.
Otherwise **reuse** the existing result.

For each job needing evaluation, read `data/jobs/details/<id>.md` and judge fit
using the rubric in `.github/copilot-instructions.md`: weigh genuine skills
overlap first, then seniority, then location & work mode, then salary. Judge
**skills/seniority against the résumé** and **location/work-mode/salary against the
Preferences**. Write `data/results/<id>.md`:

```
# <id>

- score: <n>/100
- jd_hash: <hash>
- resume_hash: <hash>
- evaluated: <today>

**Why:** <1–2 sentences>
**Matched:** <skills the candidate genuinely has>
**Gaps:** <or "none obvious">
**Tailored summary:** <3–5 sentence pitch — never invent experience>
```

(Alternatively, run `python scripts/score.py` if `OPENAI_API_KEY` is set.)

Then build the visual output: run `python scripts/build_html.py`
(writes `output/ranking.html`). Give the user a short summary: how many were newly
scored vs reused, the top pick, and tell them to open `output/ranking.html`.
