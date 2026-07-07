"""OPTIONAL advanced scraper for JS-rendered / API-driven career sites.

This mirrors the browser techniques used to read boards that plain HTTP can't
(render the page, or capture the JSON the page itself fetches). It is OPTIONAL
and requires Playwright:

    pip install playwright && playwright install chromium

Compliance note: use only on companies' OWN career sites. Do NOT point this at
LinkedIn/Indeed/aggregators or at sites protected by anti-bot challenges
(Cloudflare/DataDome) — those forbid automated access; use manual search links
instead. Track-only; never auto-apply. You accept ToS/fragility risk when using
this module.

CLI:
    python scripts/browser_fetch.py render https://careers.example.com/jobs
    python scripts/browser_fetch.py api   https://careers.example.com/jobs  /api/jobs
"""
import sys


def _page():
    try:
        from playwright.sync_api import sync_playwright  # noqa
    except ImportError:
        print("Playwright not installed. Run: pip install playwright && "
              "playwright install chromium")
        sys.exit(2)
    return sync_playwright


def render(url, wait_ms=5000):
    """Return the rendered inner text of a page (for DOM-readable boards)."""
    with _page()() as p:
        b = p.chromium.launch()
        pg = b.new_page(user_agent="Mozilla/5.0 (agentic-job-hunter)")
        pg.goto(url, wait_until="domcontentloaded")
        pg.wait_for_timeout(wait_ms)
        text = pg.evaluate("() => document.body.innerText")
        b.close()
        return text


def capture_api(url, contains, wait_ms=6000):
    """Navigate `url` and return the first JSON response whose URL contains
    `contains` — i.e. read the API the page fetches itself, without forging
    signed requests."""
    with _page()() as p:
        b = p.chromium.launch()
        pg = b.new_page(user_agent="Mozilla/5.0 (agentic-job-hunter)")
        box = {"body": None}

        def on_resp(r):
            if contains in r.url and box["body"] is None:
                try:
                    box["body"] = r.text()
                except Exception:
                    pass

        pg.on("response", on_resp)
        pg.goto(url, wait_until="domcontentloaded")
        pg.wait_for_timeout(wait_ms)
        b.close()
        return box["body"]


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    if argv[0] == "render":
        print(render(argv[1])[:4000])
    elif argv[0] == "api":
        print((capture_api(argv[1], argv[2]) or "NO_MATCHING_RESPONSE")[:4000])
    else:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
