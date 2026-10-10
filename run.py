"""Find software jobs in Helsinki, Espoo and Munich and rank them against the CV.

    python run.py              # scrape + rank + report
    python run.py --llm        # also ask Claude to assess the top N (needs ANTHROPIC_API_KEY)
    python run.py --offline    # re-rank what is already cached, no scraping
    python run.py --profile    # just print what the CV analysis found
"""
import argparse
import json
import os
import re
import sys
import webbrowser
from pathlib import Path

from jobfinder import report, scoring
from jobfinder.cv import build_profile
from jobfinder.sources import DESCRIPTION_FETCHERS, Http, city_of, collect
from jobfinder.storage import Store

ROOT = Path(__file__).parent


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def merge_duplicates(jobs):
    """Same title + company in the same city from several boards -> one entry listing all sources."""
    merged = {}
    for j in jobs:
        company = re.sub(r"\b(oy|oyj|ab|gmbh|ag|se)\b", "", norm(j["company"])).strip()
        key = (norm(j["title"]), company, j["city"])
        # Boards spell companies differently ("VTT" vs "Teknologian tutkimuskeskus VTT").
        twin = next((k for k in merged if k[0] == key[0] and k[2] == key[2] and company and k[1]
                     and (company in k[1] or k[1] in company)), None)
        key = twin or key
        if key in merged:
            m = merged[key]
            m["sources"] = sorted(set(m["sources"]) | {j["source"]})
            if not m.get("description") and j.get("description"):
                m["description"] = j["description"]
        else:
            j["sources"] = [j["source"]]
            merged[key] = j
    return list(merged.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "config.json"))
    ap.add_argument("--llm", action="store_true", help="re-rank top jobs with Claude")
    ap.add_argument("--offline", action="store_true", help="skip scraping, use cached jobs")
    ap.add_argument("--profile", action="store_true", help="print CV analysis and exit")
    ap.add_argument("--no-open", action="store_true", help="don't open the report in a browser")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    os.chdir(ROOT)
    Path(cfg["output_dir"]).mkdir(exist_ok=True)

    profile = build_profile(cfg["cv_path"])
    print(f"CV: {profile.name}")
    print("  strongest skills: " + ", ".join(f"{s} {v:.0%}" for s, v in profile.top_skills(10)))
    print("  career paths:     " + ", ".join(f"{p} {v:.0%}" for p, v in profile.paths.items()))
    for n in profile.notes:
        print("  NOTE: " + n)
    if args.profile:
        return

    store = Store(cfg["db_path"])
    if args.offline:
        rows = store.db.execute("SELECT source, ext_id, url, title, company, location, city, posted FROM jobs").fetchall()
        stubs = [dict(zip(("source", "ext_id", "url", "title", "company", "location", "city", "posted"), r)) for r in rows]
        http = None
    else:
        print("\nSearching job boards...")
        stubs, http = collect(cfg)

    jobs = [j for j in stubs if scoring.is_software_job(j["title"])]
    print(f"\n{len(stubs)} postings found, {len(jobs)} look like software roles.")
    for j in jobs:
        store.upsert(j)

    if http:
        missing = [j for j in jobs if not j.get("description")][: cfg["max_detail_fetches_per_run"]]
        print(f"Fetching {len(missing)} job descriptions (cached ones are reused)...")
        for i, j in enumerate(missing, 1):
            j["description"] = DESCRIPTION_FETCHERS[j["source"]](http, j) or ""
            if j["description"]:
                store.set_description(j)
            if i % 25 == 0:
                print(f"  {i}/{len(missing)}")

    jobs = [j for j in jobs if scoring.is_software_job(j["title"], j.get("description") or None)]
    jobs = merge_duplicates(jobs)
    for j in jobs:
        j.update(scoring.score_job(j, profile, cfg))
        j["final"] = j["score"]
    jobs.sort(key=lambda j: -j["score"])

    if args.llm:
        from jobfinder import llm
        llm.enrich(jobs, profile, cfg, store)
    blend = cfg["llm"]["blend"]
    for j in jobs:
        if j.get("llm"):
            j["final"] = round(blend * j["llm"]["fit_score"] + (1 - blend) * j["score"], 1)
    jobs.sort(key=lambda j: -j["final"])

    path = report.write(jobs, profile, cfg["output_dir"])
    print(f"\nTop 10:")
    for j in jobs[:10]:
        print(f"  {j['final']:5.1f}  {j['city']:<8} {j['title'][:55]:<55} @ {j['company'][:28]}")
    print(f"\nReport: {Path(path).resolve()}")
    print(f"CSV:    {(Path(cfg['output_dir']) / 'jobs_ranked.csv').resolve()}")
    if not args.no_open:
        webbrowser.open(Path(path).resolve().as_uri())


if __name__ == "__main__":
    sys.exit(main())
