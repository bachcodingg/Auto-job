"""Write the ranked jobs to CSV and a self-contained, filterable HTML report."""
import csv
import html
import json
from datetime import date, datetime

TEMPLATE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Job Matches</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--fg:#1d1d1b;--muted:#6b6b66;--line:#e4e3de;--accent:#2f6fde;--good:#1f8a4c;--mid:#b7791f;--bad:#c0392b;--chip:#eef1f7}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--card:#1e1e1e;--fg:#ececea;--muted:#9a9a94;--line:#2e2e2c;--accent:#7aa5ff;--good:#4cc27e;--mid:#e0a84a;--bad:#ef6b5e;--chip:#26303f}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 64px}h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 10px}
.muted{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.bar{display:flex;align-items:center;gap:8px;font-size:13px;margin:3px 0}.bar span:first-child{width:200px;flex:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar i{display:block;height:8px;border-radius:4px;background:var(--accent)}.bar .track{flex:1;background:var(--line);border-radius:4px}
.controls{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0;position:sticky;top:0;background:var(--bg);padding:8px 0;z-index:2}
select,input{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--card);color:var(--fg)}input{flex:1;min-width:160px}
.job{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin:8px 0;display:grid;grid-template-columns:58px 1fr;gap:12px}
.score{font-size:22px;font-weight:700;text-align:center;line-height:1.1}.score small{display:block;font-size:11px;font-weight:400;color:var(--muted)}
.hi{color:var(--good)}.md{color:var(--mid)}.lo{color:var(--bad)}
.job a{color:var(--fg);font-weight:600;text-decoration:none}.job a:hover{color:var(--accent)}
.meta{font-size:13px;color:var(--muted)}.chips{margin-top:6px;display:flex;flex-wrap:wrap;gap:4px}
.chip{font-size:12px;padding:1px 8px;border-radius:999px;background:var(--chip)}.chip.gap{background:transparent;border:1px dashed var(--line)}.chip.flag{background:transparent;border:1px solid var(--bad);color:var(--bad)}
.chip.new{background:var(--good);color:#fff}details{margin-top:6px;font-size:13px}summary{cursor:pointer;color:var(--accent)}
.llm{margin-top:6px;font-size:13px;border-left:3px solid var(--accent);padding-left:10px}
.note{border-left:3px solid var(--mid);padding:6px 12px;background:var(--card);margin:8px 0;font-size:14px}
@media (max-width:600px){.bar span:first-child{width:130px}}
</style></head><body><main>
<h1>Job matches for __NAME__</h1>
<div class="muted">Generated __WHEN__ · __COUNT__ software jobs in Helsinki, Espoo &amp; Munich · sources: LinkedIn, Jobly, Duunitori</div>
__NOTES__
<h2>What your CV says</h2>
<div class="grid"><div class="card"><b>Strongest skills</b>__SKILLS__</div><div class="card"><b>Career-path affinity</b>__PATHS__</div></div>
<h2>Ranked jobs</h2>
<div class="controls">
<select id="city"><option value="">All cities</option><option>Helsinki</option><option>Espoo</option><option>Munich</option></select>
<select id="src"><option value="">All sources</option><option>linkedin</option><option>jobly</option><option>duunitori</option></select>
<select id="path"><option value="">All paths</option>__PATHOPTS__</select>
<select id="lvl"><option value="">All levels</option><option>student</option><option>trainee/junior</option><option>unspecified</option><option>senior+</option></select>
<label class="muted" style="align-self:center"><input type="checkbox" id="onlynew" style="flex:none;min-width:0"> new only</label>
<input id="q" placeholder="Search title, company, skill...">
</div>
<div id="list"></div><div id="more" class="muted"></div>
</main><script>
const JOBS=__DATA__;
const $=id=>document.getElementById(id), esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
function cls(s){return s>=65?'hi':s>=45?'md':'lo'}
function render(){
 const c=$('city').value,s=$('src').value,p=$('path').value,l=$('lvl').value,n=$('onlynew').checked,q=$('q').value.toLowerCase();
 const rows=JOBS.filter(j=>(!c||j.city===c)&&(!s||j.sources.includes(s))&&(!p||j.path===p)&&(!l||j.level===l)&&(!n||j.is_new)
  &&(!q||(j.title+' '+j.company+' '+j.matched.join(' ')+' '+j.gaps.join(' ')).toLowerCase().includes(q)));
 $('list').innerHTML=rows.slice(0,300).map(j=>`<div class="job"><div class="score ${cls(j.final)}">${Math.round(j.final)}<small>${j.llm?'rule '+Math.round(j.score)+' · AI '+j.llm.fit_score:'match'}</small></div><div>
 <a href="${esc(j.url)}" target="_blank" rel="noopener">${esc(j.title)}</a> ${j.is_new?'<span class="chip new">new</span>':''}
 <div class="meta">${esc(j.company)} · ${esc(j.location)} · ${esc(j.posted||'')} · ${j.sources.join(', ')} · ${esc(j.level)}${j.min_years!=null?' · '+j.min_years+'+ yrs':''}</div>
 <div class="chips">${j.matched.map(x=>`<span class="chip">${esc(x)}</span>`).join('')}${j.gaps.map(x=>`<span class="chip gap" title="not on your CV">${esc(x)}</span>`).join('')}${j.flags.map(x=>`<span class="chip flag">${esc(x)}</span>`).join('')}</div>
 ${j.llm?`<div class="llm">${esc(j.llm.summary)}${j.llm.hard_blockers.length?'<br><b>Blockers:</b> '+j.llm.hard_blockers.map(esc).join('; '):''}<br><b>Emphasise:</b> ${j.llm.strongest_selling_points.map(esc).join('; ')}<br><b>Address:</b> ${j.llm.gaps_to_address.map(esc).join('; ')}</div>`:''}
 <details><summary>Why this score</summary>${j.reasons.map(esc).join(' · ')} · skill fit ${Math.round(j.skill_fit*100)}%${j.partial.length?' · partly on CV: '+j.partial.map(esc).join(', '):''}<p class="muted">${esc((j.description||'').slice(0,1500))}…</p></details>
 </div></div>`).join('')||'<p class="muted">No jobs match these filters.</p>';
 $('more').textContent=rows.length>300?`Showing 300 of ${rows.length}. Narrow the filters to see more.`:`${rows.length} jobs`;
}
['city','src','path','lvl','onlynew','q'].forEach(id=>$(id).addEventListener('input',render));render();
</script></body></html>"""


def _bars(items):
    return "".join(f'<div class="bar"><span title="{html.escape(k)}">{html.escape(k)}</span>'
                   f'<span class="track"><i style="width:{v * 100:.0f}%"></i></span><span>{v:.0%}</span></div>'
                   for k, v in items)


def write(jobs, profile, out_dir):
    today = date.today().isoformat()
    for j in jobs:
        j["is_new"] = j.get("first_seen") == today

    with open(f"{out_dir}/jobs_ranked.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["final", "rule_score", "ai_score", "city", "title", "company", "location", "level", "path",
                    "matched", "gaps", "flags", "sources", "url", "first_seen"])
        for j in jobs:
            w.writerow([j["final"], j["score"], (j.get("llm") or {}).get("fit_score", ""), j["city"], j["title"],
                        j["company"], j["location"], j["level"], j["path"], "; ".join(j["matched"]),
                        "; ".join(j["gaps"]), "; ".join(j["flags"]), ", ".join(j["sources"]), j["url"], j["first_seen"]])

    keep = ("title", "company", "location", "city", "posted", "url", "sources", "score", "final", "skill_fit", "path",
            "level", "min_years", "matched", "partial", "gaps", "flags", "reasons", "llm", "is_new", "description")
    data = [{k: j.get(k) for k in keep} for j in jobs]
    for d in data:
        d["description"] = (d["description"] or "")[:1600]
    notes = "".join(f'<div class="note">{html.escape(n)}</div>' for n in profile.notes)
    page = (TEMPLATE
            .replace("__NAME__", html.escape(profile.name))
            .replace("__WHEN__", datetime.now().strftime("%Y-%m-%d %H:%M"))
            .replace("__COUNT__", str(len(jobs)))
            .replace("__NOTES__", notes)
            .replace("__SKILLS__", _bars(profile.top_skills(14)))
            .replace("__PATHS__", _bars(profile.paths.items()))
            .replace("__PATHOPTS__", "".join(f"<option>{html.escape(p)}</option>" for p in profile.paths))
            .replace("__DATA__", json.dumps(data, ensure_ascii=False).replace("</", "<\\/")))
    path = f"{out_dir}/report.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return path
