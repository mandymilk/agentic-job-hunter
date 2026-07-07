"""Generate ready-to-click manual search links (LinkedIn / Indeed / Google).

Reads inbox/input.md for target titles + locations, and (optionally)
data/companies.md for companies tagged `walled`/`manual`, then writes
data/manual-search-links.md.

These are just pre-filled SEARCH URLs the user opens themselves — the tool does
not scrape LinkedIn/Indeed (they are bot-walled and their ToS forbids it). The
same links are also embedded in output/ranking.html under "Advanced".

CLI: python scripts/make_search_links.py
"""
import os
import sys
import urllib.parse as up

from lib import preferences_text, read, search_links, search_terms, write

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def company_site(company, title):
    q = up.quote_plus(f'{company} careers "{title}"')
    return f"https://www.google.com/search?q={q}"


def walled_companies():
    path = os.path.join(ROOT, "data", "companies.md")
    if not os.path.exists(path):
        return []
    out = []
    for line in read(path).splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) >= 7 and cells[-2] in ("walled", "manual"):
            out.append(cells[1])
    return out


def main():
    titles, locations = search_terms(preferences_text(ROOT))
    lines = ["# Manual search links",
             "",
             "_Generated from your preferences. These open pre-filled searches on "
             "LinkedIn / Indeed / Google — paste any promising JD into "
             "`inbox/jobs.md`, then run the ingest step._",
             ""]
    lines.append("## By title × location\n")
    for t in titles:
        lines.append(f"### {t}")
        for loc in locations:
            L = search_links(t, loc)
            lines.append(
                f"- **{loc}** — "
                f"[LinkedIn]({L['linkedin']}) · "
                f"[Indeed]({L['indeed']}) · "
                f"[Google Jobs]({L['google']})"
            )
        lines.append("")
    walled = walled_companies()
    if walled:
        lines.append("## Walled / manual companies (search their roles directly)\n")
        for co in walled:
            links = " · ".join(f"[{t}]({company_site(co, t)})" for t in titles[:3])
            lines.append(f"- **{co}** — {links}")
        lines.append("")
    write(os.path.join(ROOT, "data", "manual-search-links.md"), "\n".join(lines))
    print(f"Wrote data/manual-search-links.md ({len(titles)} titles × {len(locations)} locations"
          + (f", {len(walled)} walled companies" if walled else "") + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
