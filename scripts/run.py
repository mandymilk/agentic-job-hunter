"""Single entrypoint — reads the runtime you chose in inbox/input.md and routes
to the matching way of running the SAME 4-step flow (map → source → ingest →
rank). The approach is identical everywhere; only the driver differs.

    python scripts/run.py                 # route based on inbox/input.md
    python scripts/run.py --runtime api   # override the runtime once

Runtimes:
  copilot  VS Code / GitHub Copilot — run the `job-hunter` agent (this script
           just prints the exact next step).
  claude   Claude Code — open the repo and say "run the job hunt" (CLAUDE.md
           drives it). This script prints the next step.
  codex    Codex — open the repo and say "run the job hunt" (AGENTS.md drives
           it). This script prints the next step.
  api      Headless — this script runs the whole flow itself using an
           OpenAI-compatible API (needs OPENAI_API_KEY).

Track-only: never auto-applies.
"""
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ats_fetch  # noqa: E402
import build_html  # noqa: E402
import make_search_links  # noqa: E402
import score as score_mod  # noqa: E402
from lib import (limits, load_input, read, register_job, write)  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _placeholder_resume(resume):
    return len(resume.strip()) < 40


def _print_agent_steps(runtime):
    where = {
        "copilot": ("VS Code / GitHub Copilot",
                    "Open the Chat view, pick the **job-hunter** agent, and send "
                    "\"run the job hunt\". (Or run the prompts in order: map → "
                    "source → ingest → rank.)"),
        "claude": ("Claude Code",
                   "Open this repo in Claude Code and say \"run the job hunt\". "
                   "CLAUDE.md tells it exactly what to do."),
        "codex": ("Codex",
                  "Open this repo in Codex and say \"run the job hunt\". "
                  "AGENTS.md tells it exactly what to do."),
    }[runtime]
    print(f"\nRuntime: {runtime} ({where[0]})\n")
    print("Next step:")
    print(" ", where[1])
    print("\nWhen it finishes, open output/ranking.html in your browser.")


# --- API (headless) runtime ----------------------------------------------

def _chat(messages, json_mode=True):
    key = os.environ["OPENAI_API_KEY"]
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    body = {"model": model, "messages": messages, "temperature": 0.2}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request(
        f"{base}/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["choices"][0]["message"]["content"]


COMPANIES_HEADER = read(os.path.join(ROOT, "data", "companies.md")).split("| company", 1)[0] \
    if os.path.exists(os.path.join(ROOT, "data", "companies.md")) else "# Target Company List\n\n"


def _api_map(inp):
    """Ask the model for a reputable target-company list with public ATS slugs."""
    cap = limits(ROOT)["max_companies"]
    sys_msg = (
        "You map a candidate to reputable target companies to source jobs from. "
        "Only public/well-known companies or startups funded by famous investors. "
        "For each, give the public ATS you can read as source in the form "
        "'greenhouse:<slug>', 'lever:<slug>', 'ashby:<slug>', "
        "'smartrecruiters:<slug>', or 'workday:<tenant>:<site>'. If unknown, use "
        "tier 'walled'. Return STRICT JSON: {\"companies\":[{\"company\":str,"
        "\"tier\":\"ats\"|\"walled\",\"source\":str,\"fit\":str,\"url\":str}]} "
        f"with up to {cap} companies. Prefer the candidate's seed/preferred companies.")
    user = f"PREFERENCES:\n{inp['preferences']}\n\nRESUME:\n{inp['resume']}"
    data = json.loads(_chat([{"role": "system", "content": sys_msg},
                             {"role": "user", "content": user}]))
    companies = data.get("companies", [])[:cap]
    rows = ["| company | tier | source | fit (why it matches you) | url | status |",
            "|---------|------|--------|--------------------------|-----|--------|"]
    for c in companies:
        rows.append(f"| {c.get('company','')} | {c.get('tier','walled')} | "
                    f"{c.get('source','')} | {c.get('fit','')} | {c.get('url','')} | pending |")
    write(os.path.join(ROOT, "data", "companies.md"), COMPANIES_HEADER + "\n".join(rows) + "\n")
    print(f"  map: wrote {len(companies)} companies (cap {cap})")


def _api_source():
    """Source ATS companies straight into the registry (idempotent)."""
    max_roles = limits(ROOT)["max_roles_per_company"]
    path = os.path.join(ROOT, "data", "companies.md")
    lines = read(path).splitlines()
    scraped = 0
    for i, line in enumerate(lines):
        c = [x.strip() for x in line.split("|")]
        if len(c) < 7 or c[1] in ("company", "") or set(c[1]) == {"-"}:
            continue
        company, tier, source, status = c[1], c[2], c[3], c[6]
        if tier != "ats" or ":" not in source:
            continue
        kind, *slug = source.split(":")
        fetch = ats_fetch.FETCHERS.get(kind)
        if not fetch:
            continue
        try:
            jobs = [j for j in fetch(*slug) if ats_fetch.is_senior(j["title"])]
        except Exception as ex:  # noqa
            print(f"  source: {company} ({source}) failed: {ex}")
            continue
        n = 0
        for j in jobs:
            if n >= max_roles:
                break
            if not (j.get("description") or "").strip():
                continue
            register_job(ROOT, company, j["title"], j["location"], j["url"],
                         j["description"], source_site=kind)
            n += 1
        lines[i] = "| " + " | ".join(c[1:6] + [f"scraped:{n}" if n else "no-matches"]) + " |"
        scraped += n
        print(f"  source: {company} → {n} roles")
    write(path, "\n".join(lines) + "\n")
    print(f"  source: {scraped} roles registered total (cap {max_roles}/company)")


def _api_ingest():
    """Deterministically ingest structured blocks from inbox/jobs.md.
    Each block: 'URL:' + 'Description:' (+ optional 'Company:' / 'Title:')."""
    path = os.path.join(ROOT, "inbox", "jobs.md")
    if not os.path.exists(path):
        return
    text = read(path)
    blocks = [b for b in re.split(r"\n-{3,}\n", text) if "Description:" in b or "URL:" in b]
    added = 0
    for b in blocks:
        m_url = re.search(r"URL:\s*(\S+)", b)
        m_desc = re.search(r"Description:\s*(.+)", b, re.S)
        m_co = re.search(r"Company:\s*(.+)", b)
        m_ti = re.search(r"Title:\s*(.+)", b)
        url = m_url.group(1).strip() if m_url else ""
        desc = m_desc.group(1).strip() if m_desc else ""
        if not desc:
            continue
        company = m_co.group(1).strip() if m_co else (
            re.sub(r"^https?://(www\.)?", "", url).split(".")[0].split("/")[0] or "Unknown")
        title = m_ti.group(1).strip() if m_ti else desc.split("\n")[0][:80]
        register_job(ROOT, company, title, "", url, desc, source_site="paste")
        added += 1
    if added:
        print(f"  ingest: {added} pasted job(s) registered")


def _run_api():
    inp = load_input(ROOT)
    if _placeholder_resume(inp["resume"]):
        print("Your résumé looks empty. Paste it into inbox/input.md under the "
              "marker, then re-run.")
        return 1
    if not os.environ.get("OPENAI_API_KEY"):
        print("api runtime needs OPENAI_API_KEY (optionally OPENAI_MODEL / "
              "OPENAI_BASE_URL). Export it and re-run, or switch runtime to "
              "copilot/claude/codex.")
        return 2
    print("Running headless pipeline (api runtime)…")
    # map only if the registry has no companies yet
    comp = os.path.join(ROOT, "data", "companies.md")
    has_rows = os.path.exists(comp) and any(
        len([x for x in l.split("|")]) >= 7 and l.split("|")[1].strip() not in ("company", "")
        and set(l.split("|")[1].strip()) != {"-"} for l in read(comp).splitlines())
    if not has_rows:
        _api_map(inp)
    else:
        print("  map: companies.md already populated — skipping")
    _api_source()
    _api_ingest()
    make_search_links.main()
    score_mod.main([])   # scores stale/new jobs via the API
    build_html.main()
    print("\nDone. Open output/ranking.html in your browser.")
    return 0


def main(argv):
    runtime = None
    if "--runtime" in argv:
        i = argv.index("--runtime")
        runtime = argv[i + 1] if i + 1 < len(argv) else None
    if not runtime:
        runtime = load_input(ROOT)["runtime"]

    if runtime == "api":
        return _run_api()
    if runtime in ("copilot", "claude", "codex"):
        _print_agent_steps(runtime)
        return 0
    print(f"Unknown runtime '{runtime}'. Set runtime to one of: copilot, claude, "
          f"codex, api in inbox/input.md.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
