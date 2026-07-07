"""Optional headless scorer.

By default, matching is done by the Copilot agent (the /rank prompt) — no API
key needed. This script is the OPTIONAL path for running the pipeline outside the
agent: if OPENAI_API_KEY is set it scores every job whose evaluation is missing
or stale (resume or JD changed) and writes data/results/<id>.md.

CLI:
    python scripts/score.py            # score stale/new jobs (needs OPENAI_API_KEY)
    python scripts/score.py --list     # just list what needs scoring

Env: OPENAI_API_KEY, optional OPENAI_MODEL (default gpt-4o-mini),
     optional OPENAI_BASE_URL (default https://api.openai.com/v1).
"""
import glob
import json
import os
import re
import sys
import urllib.request

from lib import (preferences_text, profile_hash, read, resume_text, sha1_8,
                 write)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DETAILS = os.path.join(ROOT, "data", "jobs", "details")
RESULTS = os.path.join(ROOT, "data", "results")
TODAY = __import__("datetime").date.today().isoformat()

RUBRIC = (
    "You are an expert technical recruiter. Score the fit of ONE job for THIS candidate "
    "from 0-100 using, in priority order: genuine skills/tech overlap (no superficial keyword "
    "matches) > seniority & scope > location & work mode > salary if stated. Judge location, "
    "work mode and salary against the candidate's stated PREFERENCES; judge skills and "
    "seniority against their RESUME. Be honest — weak fits must score low. Never invent "
    "experience the candidate does not have. "
    "Return STRICT JSON: {\"score\":int, \"why\":str, \"matched\":str, \"gaps\":str, "
    "\"summary\":str} where summary is a 3-5 sentence tailored pitch."
)


def needs_scoring():
    rh = profile_hash(ROOT)
    todo = []
    for p in glob.glob(os.path.join(DETAILS, "*.md")):
        jid = os.path.splitext(os.path.basename(p))[0]
        jd_hash = sha1_8(read(p))
        res = os.path.join(RESULTS, jid + ".md")
        if os.path.exists(res):
            t = read(res)
            if re.search(rf"resume_hash:\s*{rh}", t) and re.search(rf"jd_hash:\s*{jd_hash}", t):
                continue
        todo.append((jid, p, jd_hash))
    return rh, todo


def call_openai(resume, jd, preferences):
    key = os.environ["OPENAI_API_KEY"]
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    base = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": RUBRIC},
            {"role": "user", "content": f"CANDIDATE PREFERENCES:\n{preferences}\n\n"
                                        f"CANDIDATE RESUME:\n{resume}\n\nJOB:\n{jd}"},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    return json.loads(d["choices"][0]["message"]["content"])


def write_result(jid, jd_hash, rh, e):
    md = (f"# {jid}\n\n- score: {e['score']}/100\n- jd_hash: {jd_hash}\n"
          f"- resume_hash: {rh}\n- evaluated: {TODAY}\n\n"
          f"**Why:** {e['why']}\n\n**Matched:** {e['matched']}\n\n"
          f"**Gaps:** {e['gaps']}\n\n**Tailored summary:** {e['summary']}\n")
    write(os.path.join(RESULTS, jid + ".md"), md)


def main(argv):
    rh, todo = needs_scoring()
    if "--list" in argv:
        print(f"resume_hash={rh}; {len(todo)} job(s) need scoring:")
        for jid, _, _ in todo:
            print("  -", jid)
        return 0
    if not os.environ.get("OPENAI_API_KEY"):
        print(f"{len(todo)} job(s) need scoring but OPENAI_API_KEY is not set.")
        print("Use the Copilot agent (/rank) to score them, or export OPENAI_API_KEY.")
        return 0
    resume = resume_text(ROOT)
    preferences = preferences_text(ROOT)
    for jid, path, jd_hash in todo:
        try:
            e = call_openai(resume, read(path), preferences)
            write_result(jid, jd_hash, rh, e)
            print(f"  scored {jid}: {e['score']}")
        except Exception as ex:  # noqa
            print(f"  FAILED {jid}: {ex}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
