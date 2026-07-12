"""Build a self-contained visual ranking (output/ranking.html).

Reads data/jobs/index.md (registry), data/results/<id>.md (evaluations), and
data/jobs/details/<id>.md (full JD), then writes a single clickable HTML file
with a sortable/filterable table where each row expands to the full evaluation.

CLI: python scripts/build_html.py
"""
import glob
import html as _html
import json
import os
import re
import sys

from lib import preferences_text, read, search_links, search_terms

ROOT = os.environ.get("AJH_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX = os.path.join(ROOT, "data", "jobs", "index.md")
RESULTS = os.path.join(ROOT, "data", "results")
DETAILS = os.path.join(ROOT, "data", "jobs", "details")
OUT = os.path.join(ROOT, "output", "ranking.html")


def parse_index():
    rows = {}
    for line in read(IDX).splitlines() if os.path.exists(IDX) else []:
        c = [x.strip() for x in line.split("|")]
        if len(c) >= 9 and c[1] not in ("id", "") and set(c[1]) != {"-"}:
            rows[c[1]] = {
                "id": c[1], "company": c[2], "title": c[3], "location": c[4],
                "url": c[5], "status": c[8],
            }
    return rows


def section(text, label):
    m = re.search(rf"\*\*{label}:?\*\*\s*(.+?)(?=\n\*\*|\Z)", text, re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def parse_result(path):
    t = read(path)
    score = re.search(r"score:\s*(\d+)", t)
    return {
        "score": int(score.group(1)) if score else 0,
        "why": section(t, "Why"),
        "matched": section(t, "Matched"),
        "gaps": section(t, "Gaps"),
        "summary": section(t, "Tailored summary"),
    }


def jd_text(job_id):
    p = os.path.join(DETAILS, job_id + ".md")
    if not os.path.exists(p):
        return ""
    t = read(p)
    i = t.find("## Description")
    return (t[i + len("## Description"):] if i >= 0 else t).strip()[:6000]


def collect():
    idx = parse_index()
    jobs = []
    for path in glob.glob(os.path.join(RESULTS, "*.md")):
        jid = os.path.splitext(os.path.basename(path))[0]
        if jid == "ranking":
            continue
        meta = idx.get(jid, {"id": jid, "company": "", "title": jid,
                             "location": "", "url": "", "status": "new"})
        r = parse_result(path)
        jobs.append({**meta, **r, "jd": jd_text(jid)})
    jobs.sort(key=lambda j: j["score"], reverse=True)
    return jobs


TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Job Ranking</title>
<style>
:root{--bg:#0f1216;--card:#171c22;--fg:#e6e8eb;--mut:#8b97a5;--line:#262c34;--acc:#4f8cff}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg)}
header{padding:20px 24px;border-bottom:1px solid var(--line)}
h1{margin:0 0 4px;font-size:19px}.sub{color:var(--mut);font-size:13px}
.controls{display:flex;gap:8px;flex-wrap:wrap;padding:14px 24px;border-bottom:1px solid var(--line)}
input,select{background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:8px 10px;font-size:13px}
input#q{flex:1;min-width:200px}
table{width:100%;border-collapse:collapse}
th,td{padding:10px 14px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--mut);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.03em;cursor:pointer;user-select:none}
tr.row{cursor:pointer}tr.row:hover{background:#1b2129}
.badge{display:inline-block;min-width:34px;text-align:center;padding:3px 8px;border-radius:20px;font-weight:700;color:#06121f}
.detail td{background:#12161b;color:var(--fg)}
.detail h3{margin:2px 0 6px;font-size:13px;color:var(--acc)}
.detail .blk{margin:0 0 12px}.detail .lab{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.03em;margin-bottom:2px}
.jd{white-space:pre-wrap;max-height:340px;overflow:auto;background:#0c0f13;border:1px solid var(--line);border-radius:8px;padding:12px;font-size:13px;color:#c7cdd4}
a{color:var(--acc)}.apply{display:inline-block;margin:6px 0;padding:7px 12px;background:var(--acc);color:#06121f;border-radius:8px;text-decoration:none;font-weight:600}
.pill{font-size:11px;color:var(--mut);border:1px solid var(--line);border-radius:20px;padding:1px 8px}
.hidden{display:none}
.legend{display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;color:var(--mut);font-size:12px}
.legend span{display:inline-flex;align-items:center;gap:5px}
.legend i{width:10px;height:10px;border-radius:3px;display:inline-block}
#count{margin-left:auto;align-self:center;white-space:nowrap}
.adv{padding:16px 24px;border-top:1px solid var(--line)}
.adv summary{cursor:pointer;color:var(--acc);font-weight:600;font-size:14px}
.adv .advnote{color:var(--mut);font-size:12px;margin:8px 0 14px;max-width:70ch}
.adv .advrole{margin:0 0 12px}
.adv .advt{display:inline-block;min-width:210px;font-weight:600}
.adv .advloc{display:inline-block;margin:2px 14px 2px 0;color:var(--mut);font-size:13px}
footer{padding:16px 24px;color:var(--mut);font-size:12px;border-top:1px solid var(--line)}
</style></head><body>
<header><h1>__TITLE__</h1><div class="sub">__SUB__</div>
  <div class="legend">
    <span><i style="background:#37d67a"></i>80+ strong</span>
    <span><i style="background:#9fd356"></i>70+ good</span>
    <span><i style="background:#f2c94c"></i>60+ fair</span>
    <span><i style="background:#f2994a"></i>50+ weak</span>
    <span><i style="background:#eb5757"></i>&lt;50 poor</span>
  </div>
</header>
<div class="controls">
  <input id="q" placeholder="Search title, company, location…">
  <select id="loc"><option value="">All locations</option></select>
  <select id="min"><option value="0">Any score</option><option value="80">80+</option>
    <option value="70">70+</option><option value="60">60+</option></select>
  <span id="count" class="pill"></span>
</div>
<table id="t"><thead><tr>
  <th data-k="rank">#</th><th data-k="score">Score</th><th data-k="title">Role</th>
  <th data-k="company">Company</th><th data-k="location">Location</th>
</tr></thead><tbody></tbody></table>
<section class="adv"><details>
  <summary>Advanced — search LinkedIn / Indeed / Google directly</summary>
  __ADVANCED__
</details></section>
<footer>Track-only. Nothing here is auto-submitted. Generated by agentic-job-hunter on __GENERATED__.</footer>
<script>
const JOBS = __DATA__;
const tb = document.querySelector('#t tbody');
const color = s => s>=80?'#37d67a':s>=70?'#9fd356':s>=60?'#f2c94c':s>=50?'#f2994a':'#eb5757';
function esc(x){return (x||'').replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]))}
let sortK='score', sortDir=-1;
function fill(){
  const q=document.getElementById('q').value.toLowerCase();
  const loc=document.getElementById('loc').value;
  const mn=+document.getElementById('min').value;
  let rows=JOBS.filter(j=>j.score>=mn
    && (!loc||j.location===loc)
    && (!q||(j.title+j.company+j.location).toLowerCase().includes(q)));
  rows.sort((a,b)=>{const x=a[sortK],y=b[sortK];return ((x>y)-(x<y))*sortDir});
  tb.innerHTML='';
  rows.forEach((j,i)=>{
    const tr=document.createElement('tr');tr.className='row';
    tr.innerHTML=`<td>${i+1}</td>
      <td><span class="badge" style="background:${color(j.score)}">${j.score}</span></td>
      <td>${esc(j.title)}</td><td>${esc(j.company)}</td>
      <td>${esc(j.location)}</td>`;
    const det=document.createElement('tr');det.className='detail hidden';
    det.innerHTML=`<td colspan="5">
      ${j.url?`<a class="apply" href="${j.url}" target="_blank" rel="noopener">Open posting ↗</a>`:''}
      ${blk('Why',j.why)}${blk('Matched',j.matched)}${blk('Gaps',j.gaps)}${blk('Tailored summary',j.summary)}
      ${j.jd?`<div class="lab">Full JD</div><div class="jd">${esc(j.jd)}</div>`:''}</td>`;
    tr.onclick=()=>det.classList.toggle('hidden');
    tb.appendChild(tr);tb.appendChild(det);
  });
  document.getElementById('count').textContent=rows.length+' / '+JOBS.length+' shown';
}
function blk(l,v){return v?`<div class="blk"><div class="lab">${l}</div><div>${esc(v)}</div></div>`:''}
function opts(id,vals){const s=document.getElementById(id);[...new Set(vals)].filter(Boolean).sort()
  .forEach(v=>{const o=document.createElement('option');o.value=o.textContent=v;s.appendChild(o)})}
opts('loc',JOBS.map(j=>j.location));
document.querySelectorAll('th').forEach(th=>th.onclick=()=>{const k=th.dataset.k;
  if(k==='rank')return; sortDir=(sortK===k)?-sortDir:-1; sortK=k; fill();});
['q','loc','min'].forEach(id=>document.getElementById(id).oninput=fill);
fill();
</script></body></html>"""


def advanced_html():
    """Build the Advanced panel: pre-filled LinkedIn/Indeed/Google searches from
    the user's preferences, so they can cover boards we don't auto-source."""
    titles, locs = search_terms(preferences_text(ROOT))
    e = _html.escape
    parts = ['<p class="advnote">Pre-filled searches you open yourself — we never '
             'scrape these boards. Found something? Paste its JD into '
             '<code>inbox/jobs.md</code> and re-run to score it.</p>']
    for t in titles:
        cells = [f'<span class="advt">{e(t)}</span>']
        for loc in locs:
            L = search_links(t, loc)
            cells.append(
                f'<span class="advloc">{e(loc)}: '
                f'<a target="_blank" rel="noopener" href="{e(L["linkedin"])}">LinkedIn</a> · '
                f'<a target="_blank" rel="noopener" href="{e(L["indeed"])}">Indeed</a> · '
                f'<a target="_blank" rel="noopener" href="{e(L["google"])}">Google</a></span>'
            )
        parts.append(f'<div class="advrole">{"".join(cells)}</div>')
    return "\n".join(parts)


def main():
    jobs = collect()
    top = jobs[0] if jobs else None
    sub = (f"{len(jobs)} roles ranked · "
           f"top pick: {top['title']} @ {top['company']} ({top['score']})" if top
           else "No scored jobs yet — run the match step.")
    html = (TEMPLATE
            .replace("__TITLE__", "Your job ranking")
            .replace("__SUB__", sub)
            .replace("__GENERATED__", __import__("datetime").date.today().isoformat())
            .replace("__ADVANCED__", advanced_html())
            .replace("__DATA__", json.dumps(jobs, ensure_ascii=False)))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {OUT} ({len(jobs)} jobs)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
