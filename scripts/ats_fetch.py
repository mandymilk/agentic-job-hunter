"""Fetch job postings from public ATS boards (stdlib only).

Supported: greenhouse, lever, ashby, smartrecruiters, workday.
Each fetcher returns a list of dicts: {title, location, url, description}.

CLI:
    python scripts/ats_fetch.py greenhouse stripe
    python scripts/ats_fetch.py lever nium --senior
    python scripts/ats_fetch.py ashby ramp
    python scripts/ats_fetch.py smartrecruiters Wise
    python scripts/ats_fetch.py workday nvidia nvidia External

    # register matched roles straight into the registry (idempotent,
    # collision-safe ids; keeps first_seen; re-runs never duplicate):
    python scripts/ats_fetch.py greenhouse stripe --senior --save --company Stripe
    python scripts/ats_fetch.py greenhouse stripe --json   # machine-readable

Compliance: only official public ATS endpoints. Track-only; never auto-apply.
"""
import json
import os
import sys
import urllib.request

from lib import is_senior, register_job, strip_html

UA = {"User-Agent": "Mozilla/5.0 (agentic-job-hunter; +https://github.com)"}


def _get(url, method="GET", data=None):
    headers = dict(UA)
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=25) as r:
        return json.load(r)


def greenhouse(slug):
    d = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true")
    out = []
    for j in d.get("jobs", []):
        out.append({
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
            "description": strip_html(j.get("content", "")),
        })
    return out


def lever(slug):
    d = _get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
    out = []
    for p in d:
        body = strip_html(p.get("description", ""))
        for L in p.get("lists", []):
            body += "\n\n" + L.get("text", "") + ":\n" + strip_html(L.get("content", ""))
        out.append({
            "title": p.get("text", ""),
            "location": (p.get("categories") or {}).get("location", ""),
            "url": p.get("hostedUrl", ""),
            "description": body.strip(),
        })
    return out


def ashby(slug):
    d = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true")
    out = []
    for j in d.get("jobs", []):
        out.append({
            "title": j.get("title", ""),
            "location": j.get("location", ""),
            "url": j.get("jobUrl", ""),
            "description": strip_html(j.get("descriptionHtml", j.get("descriptionPlain", ""))),
        })
    return out


def smartrecruiters(slug):
    out = []
    base = f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
    d = _get(base + "?limit=100")
    for p in d.get("content", []):
        loc = p.get("location", {})
        detail_url = f"{base}/{p.get('id')}"
        try:
            det = _get(detail_url)
            jd = det.get("jobAd", {}).get("sections", {})
            desc = "\n\n".join(
                strip_html((v or {}).get("text", "")) for v in jd.values() if isinstance(v, dict)
            )
        except Exception:
            desc = ""
        out.append({
            "title": p.get("name", ""),
            "location": ", ".join(filter(None, [loc.get("city"), loc.get("country")])),
            "url": (p.get("ref") or "").replace("api.smartrecruiters.com/v1/companies",
                                                "jobs.smartrecruiters.com") or
                   f"https://jobs.smartrecruiters.com/{slug}/{p.get('id')}",
            "description": desc,
        })
    return out


def workday(tenant, site, host=None):
    host = host or tenant
    url = f"https://{host}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    out = []
    offset = 0
    while True:
        d = _get(url, method="POST", data={"limit": 20, "offset": offset, "searchText": ""})
        posts = d.get("jobPostings", [])
        if not posts:
            break
        for p in posts:
            out.append({
                "title": p.get("title", ""),
                "location": p.get("locationsText", ""),
                "url": f"https://{host}.wd1.myworkdayjobs.com/{site}{p.get('externalPath','')}",
                "description": "",  # detail needs a second call per posting
            })
        offset += 20
        if offset >= d.get("total", 0):
            break
    return out


FETCHERS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "smartrecruiters": smartrecruiters,
    "workday": workday,
}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    kind = argv[0]
    rest = argv[1:]
    senior_only = "--senior" in rest
    save = "--save" in rest
    as_json = "--json" in rest

    company = None
    pos = []
    i = 0
    while i < len(rest):
        a = rest[i]
        if a == "--company":
            company = rest[i + 1] if i + 1 < len(rest) else None
            i += 2
            continue
        if not a.startswith("--"):
            pos.append(a)
        i += 1

    jobs = FETCHERS[kind](*pos)
    if senior_only:
        jobs = [j for j in jobs if is_senior(j["title"])]

    if as_json:
        print(json.dumps(jobs, ensure_ascii=False, indent=2))
        return 0

    if save:
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        company = company or (pos[0] if pos else kind)
        counts = {"new": 0, "updated": 0, "unchanged": 0, "skipped": 0}
        for j in jobs:
            if not (j.get("description") or "").strip():
                counts["skipped"] += 1
                print(f"  [skipped, no JD] {j['title']}")
                continue
            jid, action = register_job(root, company, j["title"], j["location"],
                                       j["url"], j["description"], source_site=kind)
            counts[action] += 1
            print(f"  [{action}] {jid}")
        print(f"{kind}:{pos[0] if pos else ''} → "
              + ", ".join(f"{k}:{v}" for k, v in counts.items()))
        return 0

    print(f"{len(jobs)} roles from {kind}:{pos[0] if pos else ''}")
    for j in jobs:
        print(f"  - {j['title']}  |  {j['location']}  |  {j['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
