# Job Finder: software jobs in Helsinki, Espoo & Munich ranked my CV

## How it works
1. **CV analysis** (`jobfinder/cv.py`): reads `CV_VoGiaBach (1).docx` and scores each skill from 0 to 1.
   Skills you used in projects or work count for more than skills you only listed. It also scores your
   affinity for six career paths (Full-stack, Backend, AI/ML, DevOps/Cloud, Dev Tooling/Quality, Data).
2. **Scraping** (`jobfinder/sources.py`):
   - LinkedIn public job search, all 3 cities, posted in the last 30 days
   - Jobly.fi, filtered to Helsinki/Espoo
   - Duunitori.fi, Helsinki and Espoo areas

   Non-software titles are dropped. The full description of each job is fetched once and cached in `output/jobs.sqlite`.
3. **Matching** (`jobfinder/scoring.py`): score = 100 × fit × level × experience × language
   - fit: 70% skill fit (the skills the ad asks for, weighted by how strong each is on your CV, and smoothed
     when an ad names few skills) plus 30% path fit (the ad's main career path compared with your affinity for it)
   - level: student, Werkstudent or intern 1.0 · trainee or junior 0.95 · unspecified 0.8 · senior, lead or architect 0.45.
     Master's thesis and doctoral positions are penalised further.
   - experience: ×0.75 if the ad asks for 3–4 years, ×0.5 if it asks for 5 or more
   - language: ×0.55 if fluent Finnish or German is required (yours is A2), ×0.92 if it is only "a plus",
     ×0.8 if the ad itself is written in Finnish or German
   - Each job lists what drove its score: matched skills, gaps (skills the ad wants that your CV lacks) and red flags.
4. **Optional AI pass** (`--llm`): Claude reads your full CV against the top N ads. It returns a realistic
   fit score, hard blockers, selling points to emphasise, and gaps to address. That score is blended
   with the rule score (60/40).
5. **Output**: `output/report.html` (filter by city, source, path, level, new-only and search) and `output/jobs_ranked.csv`.
   Jobs first seen today get a **new** badge.

## Usage
Put your CV (.docx) in this folder and set `cv_path` in `config.json`. CVs are git-ignored, so they never get pushed.
```
pip install -r requirements.txt
python run.py               # scrape, rank, open the report
python run.py --offline     # re-rank the cached jobs (e.g. after editing your CV or config.json)
python run.py --profile     # show what the system read from your CV
python run.py --llm         # add Claude's assessment (set ANTHROPIC_API_KEY first)
```

Daily automation (Windows Task Scheduler, runs at 08:00):
```
schtasks /Create /SC DAILY /ST 08:00 /TN "JobFinder" /TR "\"D:\TUM\Master\newest document\job finder\run_daily.bat\" --no-open"
```

## Tuning
Everything is in `config.json`: search keywords per city, pages per query, score weights, your language levels,
the LLM model and top-N. Skills and career paths are defined in `jobfinder/taxonomy.py`.

## Notes
- LinkedIn's public endpoints sometimes rate-limit (HTTP 429). The scraper backs off and continues.
  If that happens, lower `pages_per_query` or run less often.
- Scrape responsibly and for personal use only. The boards' HTML can change, so if a source suddenly
  returns 0 jobs, its selectors in `sources.py` need updating.
