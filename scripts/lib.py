"""Shared helpers (stdlib only)."""
import datetime
import hashlib
import html as _html
import os
import re
import urllib.parse as _up


def slugify(*parts: str) -> str:
    s = "-".join(p for p in parts if p)
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)


def sha1_8(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def strip_html(h: str) -> str:
    if not h:
        return ""
    h = _html.unescape(h)  # decode entities first so escaped tags become real tags
    h = h.replace("\u00a0", " ").replace("&nbsp;", " ")  # some boards double-escape
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", h, flags=re.S | re.I)
    h = re.sub(r"<br\s*/?>", "\n", h, flags=re.I)
    h = re.sub(r"</(p|li|div|h[1-6])>", "\n", h, flags=re.I)
    h = re.sub(r"<li[^>]*>", "- ", h, flags=re.I)
    h = re.sub(r"<[^>]+>", "", h)
    return re.sub(r"\n{3,}", "\n\n", h).strip()


SENIOR_RE = re.compile(
    r"head of product|principal|lead product|product lead|staff product|"
    r"product director|director[, ].*product|group product|VP.*product|"
    r"head of growth|chief product|GPM|director of product",
    re.I,
)
JUNIOR_RE = re.compile(r"\bintern\b|graduate|working student|apprentice|junior|entry", re.I)


def is_senior(title: str) -> bool:
    return bool(SENIOR_RE.search(title or "")) and not JUNIOR_RE.search(title or "")


def matches_any(text: str, terms) -> bool:
    text = (text or "").lower()
    return any(t.lower() in text for t in terms if t)


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path: str, text: str) -> None:
    import os

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


# --- Single input file (runtime + preferences + resume) ------------------
# The user fills ONE file (inbox/input.md): pick a runtime, edit preferences,
# and paste their resume below the marker. The resume is parsed out on its own
# so editing preferences/runtime never changes resume_hash (never re-scores).

RESUME_MARKER = "--- PASTE RESUME BELOW THIS LINE ---"
RUNTIMES = ("copilot", "claude", "codex", "api")


def _input_path(root):
    return os.path.join(root, "inbox", "input.md")


def load_input(root):
    """Parse inbox/input.md into {runtime, preferences, resume, raw}."""
    path = _input_path(root)
    text = read(path) if os.path.exists(path) else ""
    m = re.search(r"^\s*[-*]?\s*(?:\*\*)?runtime(?:\*\*)?\s*[:=]\s*`?([a-zA-Z]+)", text, re.M)
    runtime = m.group(1).lower() if m else "copilot"
    if runtime not in RUNTIMES:
        runtime = "copilot"
    head, _, tail = text.partition(RESUME_MARKER)
    resume = tail.strip()
    m2 = re.search(r"##[^\n]*preferences[^\n]*\n(.*?)(?=\n##\s|\Z)", head, re.S | re.I)
    preferences = (m2.group(1).strip() if m2 else head.strip())
    return {"runtime": runtime, "resume": resume, "preferences": preferences, "raw": text}


def resume_text(root):
    return load_input(root)["resume"]


def resume_hash(root):
    return sha1_8(resume_text(root))


def preferences_text(root):
    return load_input(root)["preferences"]


def profile_hash(root):
    """Hash of the whole candidate profile (résumé + preferences). Scoring uses
    both, so this is what decides whether a job needs re-scoring."""
    d = load_input(root)
    return sha1_8(d["resume"] + "\n\n[PREFERENCES]\n" + d["preferences"])


def _int_after(label, text, default):
    m = re.search(rf"{label}[^\d]*(\d+)", text, re.I)
    return int(m.group(1)) if m else default


def limits(root):
    """Optional run caps from Preferences (to bound runtime/cost), with defaults.
    - max_companies: how many companies to target/source.
    - max_roles_per_company: how many senior roles to register per company."""
    prefs = preferences_text(root)
    return {
        "max_companies": _int_after(r"Max companies", prefs, 30),
        "max_roles_per_company": _int_after(r"Max roles per company", prefs, 10),
    }


# --- Manual search links (LinkedIn / Indeed / Google) --------------------
# Shared by make_search_links.py and the Advanced panel in build_html.py.

def _list_after(label, text):
    """Pull comma/bullet items following a '**Label:**' or '- **Label:**' line."""
    m = re.search(rf"{label}[:*\s]*([^\n]+(?:\n\s+[^\n-][^\n]+)*)", text, re.I)
    if not m:
        return []
    raw = re.sub(r"\s+", " ", m.group(1))
    return [t.strip(" .;") for t in re.split(r"[,/]", raw) if t.strip(" .;")]


def search_terms(preferences):
    """Return (titles, locations) to search, capped to stay usable."""
    titles = _list_after(r"Target titles[^:]*", preferences) or ["Product Manager"]
    locations = _list_after(r"Locations", preferences) or ["Remote"]
    locations = [l for l in locations if "remote" not in l.lower()][:5] or ["Remote"]
    return titles[:6], locations


def search_links(title, loc):
    """Pre-filled SEARCH urls (the user opens these; we never scrape them)."""
    li = _up.urlencode({"keywords": title, "location": loc, "f_TPR": "r604800"})
    ind = _up.urlencode({"q": title, "l": loc, "fromage": "7"})
    goog = _up.quote_plus(f"{title} {loc} jobs")
    return {
        "linkedin": f"https://www.linkedin.com/jobs/search/?{li}",
        "indeed": f"https://www.indeed.com/jobs?{ind}",
        "google": f"https://www.google.com/search?q={goog}&ibp=htl;jobs",
    }


# --- Job registry --------------------------------------------------------

# Idempotent, collision-safe registration shared by ats_fetch/ingest so no
# two postings can ever silently overwrite each other's id.

def _index_path(root):
    return os.path.join(root, "data", "jobs", "index.md")


def _detail_path(root, jid):
    return os.path.join(root, "data", "jobs", "details", jid + ".md")


def parse_index(root):
    """Return (header_lines, row_dicts) from data/jobs/index.md, preserving the
    markdown header/table-header lines separately from data rows."""
    path = _index_path(root)
    header, rows = [], []
    if not os.path.exists(path):
        return header, rows
    for line in read(path).splitlines():
        c = [x.strip() for x in line.split("|")]
        if len(c) >= 9 and c[1] not in ("id", "") and set(c[1]) != {"-"}:
            rows.append({"id": c[1], "company": c[2], "title": c[3],
                         "location": c[4], "url": c[5], "jd_hash": c[6],
                         "first_seen": c[7], "status": c[8]})
        else:
            header.append(line)
    return header, rows

def _cell(v):
    """Make a value safe for a markdown table cell (no pipes/newlines)."""
    return re.sub(r"\s+", " ", str(v if v is not None else "").replace("|", "/")).strip()


def _row_line(r):
    return ("| " + " | ".join(_cell(r[k]) for k in
            ("id", "company", "title", "location", "url", "jd_hash",
             "first_seen", "status")) + " |")


def _unique_id(base, location, taken):
    """A stable, collision-safe id: prefer a location suffix, then a number."""
    if base not in taken:
        return base
    loc = slugify((location or "").split(",")[0])
    jid = slugify(base, loc) if loc else base
    n = 2
    while jid in taken or not jid:
        jid = f"{base}-{loc}-{n}" if loc else f"{base}-{n}"
        n += 1
    return jid


def register_job(root, company, title, location, url, description,
                 source_site="ats", today=None):
    """Idempotently register one posting into the registry.

    Matches an existing posting by url (so re-runs never duplicate), keeps the
    original first_seen, updates the detail file + jd_hash only when the JD
    changed, and generates a collision-safe id for genuinely new postings.
    Returns (id, action) where action is 'new' | 'updated' | 'unchanged'.
    """
    today = today or datetime.date.today().isoformat()
    header, rows = parse_index(root)
    taken = {r["id"] for r in rows}
    existing = next((r for r in rows if url and r["url"] == url), None)

    if existing:
        jid, first_seen, status = existing["id"], existing["first_seen"], existing["status"]
    else:
        jid = _unique_id(slugify(company, title), location, taken)
        first_seen, status = today, "new"

    body = (description or "").strip()
    detail = (
        f"---\nid: {jid}\nurl: {url}\ncompany: {company}\n"
        f"location: {location}\nsource_site: {source_site}\n"
        f"first_seen: {first_seen}\n---\n\n"
        f"## Description\n\n{body or '(No description text available.)'}\n"
    )
    new_hash = sha1_8(detail)
    dpath = _detail_path(root, jid)

    if existing and existing["jd_hash"] == new_hash and os.path.exists(dpath):
        return jid, "unchanged"

    write(dpath, detail)
    if existing:
        existing.update({"company": company, "title": title,
                         "location": location, "url": url, "jd_hash": new_hash})
        action = "updated"
    else:
        rows.append({"id": jid, "company": company, "title": title,
                     "location": location, "url": url, "jd_hash": new_hash,
                     "first_seen": first_seen, "status": status})
        action = "new"

    if not header:  # brand-new registry: seed a minimal table header
        header = ["| id | company | title | location | url | jd_hash | first_seen | status |",
                  "|----|---------|-------|----------|-----|---------|-----------|--------|"]
    write(_index_path(root), "\n".join(header + [_row_line(r) for r in rows]) + "\n")
    return jid, action

