"""Source jobs from LinkedIn's PUBLIC jobs-guest board into the registry.

This is a thin Python wrapper around the vendored TypeScript CLI in
`tools/linkedin-cli/` (copied from the ai-job-search project). It only *sources*
jobs: it searches title x location from your Preferences, pulls each posting's
full JD, and registers matches with the SAME idempotent `register_job` used by
`ats_fetch.py`. It does NOT touch scoring/ranking — `score.py` and
`build_html.py` read the registry and are unaffected.

    ⚠️  PERSONAL USE ONLY. This reads LinkedIn's public job pages; automated
        access is against LinkedIn's Terms of Service. Keep volume low, do not
        use it commercially or for bulk collection. Run it on your own
        responsibility. (agentic-job-hunter otherwise avoids scraping walled
        aggregators — this source is the one deliberate, opt-outable exception.)

Requires `bun` on PATH (https://bun.sh). If bun is missing it prints how to fall
back to `make_search_links.py` and exits non-zero without failing the run.

CLI:
    python scripts/linkedin_source.py                 # search prefs, register senior roles
    python scripts/linkedin_source.py --jobage 7      # only postings from the last 7 days
    python scripts/linkedin_source.py --limit 5       # cap roles registered per title x location
    python scripts/linkedin_source.py --json          # preview matches, do not register
"""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib import (is_senior, limits, preferences_text, register_job,  # noqa: E402
                 search_terms)

ROOT = os.environ.get("AJH_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = os.path.join(ROOT, "tools", "linkedin-cli", "src", "cli.ts")

ALERT = (
    "\n  ⚠️  LinkedIn source — PERSONAL USE ONLY. Automated access to LinkedIn's\n"
    "     public pages is against their Terms of Service. Keep volume low and\n"
    "     non-commercial. Skip this step (use make_search_links.py instead) if\n"
    "     you'd rather not.\n"
)


def _bun():
    return shutil.which("bun")


def _run_cli(args):
    """Run the vendored CLI. Returns (data, error) where error is None on
    success, else a short reason: 'timeout' | 'blocked' (HTTP 451) | 'failed'."""
    try:
        out = subprocess.run(["bun", "run", CLI, *args, "--format", "json"],
                             capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None, "timeout"
    except OSError:
        return None, "failed"
    blob = (out.stdout or "") + (out.stderr or "")
    if "451" in blob or "Unavailable_For_Legal_Reasons" in blob:
        return None, "blocked"
    if out.returncode != 0:
        return None, "failed"
    try:
        return json.loads(out.stdout), None
    except json.JSONDecodeError:
        return None, "failed"


def search(query, location, jobage):
    """Return (cards, error). error is None on success, else a reason string."""
    args = ["search", "-l", location]
    if query:
        args += ["-q", query]
    if jobage:
        args += ["--jobage", str(jobage)]
    data, err = _run_cli(args)
    return ((data or {}).get("results", []) if data else []), err


def detail(job_id):
    data, _ = _run_cli(["detail", str(job_id)])
    return data or {}


def _fallback(reason):
    """The original method: generate ready-to-click search links so the user
    still gets LinkedIn/Indeed/Google coverage when live sourcing is unavailable."""
    import make_search_links  # local import avoids any import cycle
    print(f"  linkedin unavailable ({reason}) → falling back to search links "
          f"(make_search_links.py)")
    make_search_links.main()


def main(argv, fallback=True):
    as_json = "--json" in argv
    if not _bun():
        sys.stderr.write(
            "bun not found on PATH — the LinkedIn CLI needs it (https://bun.sh).\n"
            "Skipping LinkedIn sourcing.\n")
        if fallback and not as_json:
            _fallback("bun-not-installed")
        return 0

    jobage = None
    per_search = limits(ROOT)["max_roles_per_company"]
    i = 0
    while i < len(argv):
        if argv[i] == "--jobage" and i + 1 < len(argv):
            jobage = int(argv[i + 1]); i += 2; continue
        if argv[i] == "--limit" and i + 1 < len(argv):
            per_search = int(argv[i + 1]); i += 2; continue
        i += 1

    sys.stderr.write(ALERT)
    titles, locations = search_terms(preferences_text(ROOT))

    preview, counts = [], {"new": 0, "updated": 0, "unchanged": 0, "skipped": 0}
    errors = set()
    seen = set()  # dedupe by job id so a role hit by multiple searches is fetched once
    for title in titles:
        for loc in locations:
            cards, err = search(title, loc, jobage)
            if err:
                errors.add(err)
                continue
            cards = [c for c in cards if is_senior(c.get("title", ""))]
            for card in cards[:per_search]:
                jid_src = str(card.get("id", ""))
                if jid_src and jid_src in seen:
                    continue
                seen.add(jid_src)
                det = detail(card.get("id", ""))
                desc = (det.get("description") or "").strip()
                company = card.get("company") or det.get("company") or "LinkedIn"
                if as_json:
                    preview.append({"company": company, "title": card.get("title", ""),
                                    "location": card.get("location", ""),
                                    "url": card.get("url", ""), "has_jd": bool(desc)})
                    continue
                if not desc:
                    counts["skipped"] += 1
                    print(f"  [skipped, no JD] {card.get('title','')}")
                    continue
                jid, action = register_job(
                    ROOT, company, card.get("title", ""), card.get("location", ""),
                    card.get("url", ""), desc, source_site="linkedin")
                counts[action] += 1
                print(f"  [{action}] {jid}")

    if as_json:
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    registered = counts["new"] + counts["updated"] + counts["unchanged"]
    print("linkedin → " + ", ".join(f"{k}:{v}" for k, v in counts.items()))
    # Fall back to the original method when live sourcing yielded nothing usable
    # (every search errored/blocked, or the board returned no senior matches).
    if registered == 0 and fallback:
        reason = ", ".join(sorted(errors)) if errors else "no matches"
        _fallback(reason)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
