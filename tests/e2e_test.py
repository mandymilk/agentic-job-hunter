#!/usr/bin/env python3
"""End-to-end loop test for the job-hunter pipeline.

Runs the full headless flow (map -> source -> linkedin -> ingest -> rank -> html)
against an ISOLATED temp root (via the AJH_ROOT override), so it never touches
your real data/, output/, or inbox/. The three external boundaries — the LLM
(map + scoring), the ATS fetchers, and the LinkedIn CLI — are stubbed so the run
is deterministic, offline, and free.

Scenarios:
  1. synthetic — a made-up résumé + preferences, LinkedIn sourcing SUCCEEDS.
  2. real      — YOUR real inbox/input.md + inbox/jobs.md, LinkedIn SUCCEEDS.
  3. fallback  — LinkedIn returns HTTP 451 (blocked) -> falls back to search links.

Run:  python3 tests/e2e_test.py      (exit 0 = all passed)
"""
import importlib
import json
import os
import shutil
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(REPO, "scripts")
MODS = ["lib", "ats_fetch", "score", "make_search_links", "linkedin_source",
        "build_html", "run"]

SYN_INPUT = """# Input

## Runtime
runtime: api

## Preferences
- **Target titles / role archetypes:** Product Manager, Principal Product Manager, Head of Product
- **Seniority:** Principal / Head
- **Locations:** Singapore, Remote
- **Blocked companies (never surface):** EvilCorp
- **Max companies (cap the hunt):** 30
- **Max roles per company:** 10

## Résumé
--- PASTE RESUME BELOW THIS LINE ---
Jane Doe — 12 years in product management. Launched a 0->1 loyalty program from
scratch. Managed a team of 8 PMs. Scaled a marketplace from 1M to 10M users. Deep
payments/fintech domain. Owned strategy and roadmap under ambiguity.
"""

SYN_JOBS = """## Job
URL: https://pasted.example.com/job/9
Description: Group Product Manager, Payments. Requires managing a team of PMs and 0->1 launches.
---
"""


# --- harness -------------------------------------------------------------

def _write(root, rel, text):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def _load(root):
    """Import all pipeline modules fresh, bound to `root` via AJH_ROOT."""
    os.environ["AJH_ROOT"] = root
    os.environ["OPENAI_API_KEY"] = "test-key-stub"  # stubbed; no real call is made
    for m in MODS:
        sys.modules.pop(m, None)
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    return {m: importlib.import_module(m) for m in MODS}


def _stub(mods, linkedin="ok"):
    run, score, ats, li = mods["run"], mods["score"], mods["ats_fetch"], mods["linkedin_source"]

    run._chat = lambda messages, json_mode=True: json.dumps(
        {"companies": [{"company": "TestCo", "tier": "ats",
                        "source": "greenhouse:testco", "fit": "strong",
                        "url": "https://testco.example.com"}]})

    score.call_openai = lambda resume, jd, prefs: {
        "score": 72, "why": "stub why", "matched": "stub matched",
        "gaps": "stub gaps", "summary": "Stub tailored résumé summary for this role."}

    ats.FETCHERS = dict(ats.FETCHERS, greenhouse=lambda slug: [{
        "title": "Head of Product", "location": "Remote",
        "url": "https://testco.example.com/jobs/1",
        "description": ("0->1 product leader building from scratch, managing a "
                        "team of PMs, scaling 1M to 10M users, payments domain, "
                        "owns strategy and roadmap.")}])

    if linkedin == "ok":
        li.search = lambda q, loc, age: ([{
            "id": "555", "title": "Principal Product Manager", "company": "LI Corp",
            "location": "Remote", "url": "https://www.linkedin.com/jobs/view/555"}], None)
        li.detail = lambda jid: {
            "description": "Principal PM for AI products; sets strategy and roadmap.",
            "company": "LI Corp"}
    elif linkedin == "blocked":
        li._run_cli = lambda args: (None, "blocked")


def _rows(mods):
    _, rows = mods["lib"].parse_index(mods["run"].ROOT)
    return rows


def _results(root):
    d = os.path.join(root, "data", "results")
    return [f for f in os.listdir(d) if f.endswith(".md")] if os.path.isdir(d) else []


# --- scenarios -----------------------------------------------------------

def scenario_full(name, input_md, jobs_md):
    """Run the whole api pipeline and assert every stage produced output."""
    root = tempfile.mkdtemp(prefix=f"ajh-e2e-{name}-")
    try:
        _write(root, "inbox/input.md", input_md)
        _write(root, "inbox/jobs.md", jobs_md)
        mods = _load(root)
        _stub(mods, linkedin="ok")

        rc = mods["run"]._run_api()
        assert rc == 0, f"_run_api returned {rc}"

        companies = os.path.join(root, "data", "companies.md")
        assert os.path.exists(companies), "companies.md not written (map failed)"
        assert "TestCo" in open(companies).read(), "map company missing"

        rows = _rows(mods)
        titles = " ".join(r["title"] for r in rows)
        assert len(rows) >= 3, f"expected >=3 registered jobs, got {len(rows)}"
        assert "Head of Product" in titles, "ATS source did not register"
        assert "Principal Product Manager" in titles, "LinkedIn source did not register"

        res = _results(root)
        assert len(res) >= len(rows), f"scored {len(res)} of {len(rows)} jobs"

        html_path = os.path.join(root, "output", "ranking.html")
        assert os.path.exists(html_path), "ranking.html not built"
        html = open(html_path).read()
        assert len(html) > 800, "ranking.html looks empty"
        assert "Head of Product" in html and "Principal Product Manager" in html, \
            "ranking.html missing job rows"

        links = os.path.join(root, "data", "manual-search-links.md")
        assert os.path.exists(links), "search links (fallback coverage) not generated"

        print(f"  PASS  {name}: {len(rows)} jobs, {len(res)} scored, ranking.html built")
        return True
    except AssertionError as e:
        print(f"  FAIL  {name}: {e}")
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def scenario_real(name):
    """Same pipeline, but driven by the user's REAL input.md + jobs.md."""
    real_input = os.path.join(REPO, "inbox", "input.md")
    real_jobs = os.path.join(REPO, "inbox", "jobs.md")
    if not os.path.exists(real_input):
        print(f"  SKIP  {name}: inbox/input.md not found")
        return True
    input_md = open(real_input, encoding="utf-8").read()
    marker = "--- PASTE RESUME BELOW THIS LINE ---"
    resume = input_md.split(marker, 1)[1].strip() if marker in input_md else ""
    if len(resume) < 40:
        print(f"  SKIP  {name}: no résumé pasted in inbox/input.md")
        return True
    jobs_md = open(real_jobs, encoding="utf-8").read() if os.path.exists(real_jobs) else ""

    root = tempfile.mkdtemp(prefix=f"ajh-e2e-{name}-")
    try:
        _write(root, "inbox/input.md", input_md)
        _write(root, "inbox/jobs.md", jobs_md)
        mods = _load(root)
        _stub(mods, linkedin="ok")

        rc = mods["run"]._run_api()
        assert rc == 0, f"_run_api returned {rc}"

        rows = _rows(mods)
        assert len(rows) >= 1, "no jobs registered from real input"
        res = _results(root)
        assert len(res) >= 1, "no jobs scored from real input"
        html_path = os.path.join(root, "output", "ranking.html")
        assert os.path.exists(html_path) and os.path.getsize(html_path) > 800, \
            "ranking.html not built from real input"

        print(f"  PASS  {name}: {len(rows)} jobs, {len(res)} scored, ranking.html built")
        return True
    except AssertionError as e:
        print(f"  FAIL  {name}: {e}")
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def scenario_fallback(name):
    """LinkedIn blocked (HTTP 451) -> must fall back to generated search links."""
    root = tempfile.mkdtemp(prefix=f"ajh-e2e-{name}-")
    try:
        _write(root, "inbox/input.md", SYN_INPUT)
        mods = _load(root)
        _stub(mods, linkedin="blocked")

        rc = mods["linkedin_source"].main([], fallback=True)
        assert rc == 0, f"linkedin_source.main returned {rc}"

        links = os.path.join(root, "data", "manual-search-links.md")
        assert os.path.exists(links), "fallback did not generate search links"
        assert len(_rows(mods)) == 0, "blocked LinkedIn should register 0 jobs"

        print(f"  PASS  {name}: blocked -> search-links fallback generated, 0 jobs registered")
        return True
    except AssertionError as e:
        print(f"  FAIL  {name}: {e}")
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def scenario_refresh(name):
    """Running the pipeline twice must REFRESH the company list (merge): keep
    existing companies + manual curation, and add newly-found ones — never skip."""
    root = tempfile.mkdtemp(prefix=f"ajh-e2e-{name}-")
    try:
        _write(root, "inbox/input.md", SYN_INPUT)
        _write(root, "inbox/jobs.md", SYN_JOBS)
        mods = _load(root)
        _stub(mods, linkedin="ok")

        # Run 1 → map creates TestCo, source scrapes it.
        assert mods["run"]._run_api() == 0, "first run failed"
        comp_path = os.path.join(root, "data", "companies.md")
        assert "TestCo" in open(comp_path).read(), "run 1 did not map TestCo"

        # User manually curates a company; map must preserve it on the next run.
        with open(comp_path, "a", encoding="utf-8") as f:
            f.write("| MyPick | ats | greenhouse:mypick | manual add | https://mypick.example.com | pending |\n")

        # On the re-run the model now surfaces a NEW company.
        mods["run"]._chat = lambda messages, json_mode=True: json.dumps(
            {"companies": [{"company": "FreshCo", "tier": "ats",
                            "source": "greenhouse:freshco", "fit": "new find",
                            "url": "https://freshco.example.com"}]})

        # Run 2 → map must MERGE (not skip, not overwrite).
        assert mods["run"]._run_api() == 0, "second run failed"
        text = open(comp_path).read()
        assert "TestCo" in text, "refresh dropped an existing company"
        assert "MyPick" in text, "refresh wiped manual curation"
        assert "FreshCo" in text, "refresh did not add the newly-found company (map was skipped)"

        print(f"  PASS  {name}: re-run merged (TestCo kept, MyPick curation kept, FreshCo added)")
        return True
    except AssertionError as e:
        print(f"  FAIL  {name}: {e}")
        return False
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main():
    print("Running end-to-end pipeline tests (isolated temp roots)…")
    ok = True
    ok &= scenario_full("synthetic", SYN_INPUT, SYN_JOBS)
    ok &= scenario_real("real-user")
    ok &= scenario_refresh("refresh-merge")
    ok &= scenario_fallback("linkedin-fallback")
    print("\n" + ("ALL TESTS PASSED" if ok else "SOME TESTS FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
