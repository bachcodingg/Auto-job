"""Scrapers for LinkedIn (public guest endpoints), Jobly.fi and Duunitori.fi.

Every scraper yields dicts with: source, ext_id, url, title, company, location, posted.
Descriptions are fetched separately via fetch_description().
"""
import json
import random
import re
import time
from urllib.parse import quote_plus, urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9,fi;q=0.6,de;q=0.5",
}


class Http:
    def __init__(self, delay=1.2):
        self.s = requests.Session()
        self.s.headers.update(HEADERS)
        self.delay = delay

    def get(self, url, tries=4):
        for attempt in range(tries):
            time.sleep(self.delay + random.random() * 0.5)
            try:
                r = self.s.get(url, timeout=30)
            except requests.RequestException as e:
                print(f"    ! network error {e.__class__.__name__}, retrying")
                continue
            if r.status_code == 200:
                return r.text
            if r.status_code in (429, 999) or r.status_code >= 500:
                wait = 5 * (attempt + 1) ** 2
                print(f"    ! HTTP {r.status_code}, backing off {wait}s")
                time.sleep(wait)
                continue
            return None  # 400/404 etc.: give up on this URL
        return None


def _txt(el):
    return el.get_text(" ", strip=True) if el else ""


# ---------------------------------------------------------------- LinkedIn
def linkedin_search(http, keyword, location, pages=3, days=30):
    for page in range(pages):
        url = ("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
               f"?keywords={quote_plus(keyword)}&location={quote_plus(location)}"
               f"&f_TPR=r{days * 86400}&start={page * 10}")
        html = http.get(url)
        if not html:
            return
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("div.base-card[data-entity-urn]")
        if not cards:
            return
        for c in cards:
            jid = c["data-entity-urn"].rsplit(":", 1)[-1]
            t = c.select_one("time")
            yield {
                "source": "linkedin", "ext_id": jid,
                "url": f"https://www.linkedin.com/jobs/view/{jid}/",
                "title": _txt(c.select_one(".base-search-card__title")),
                "company": _txt(c.select_one(".base-search-card__subtitle")),
                "location": _txt(c.select_one(".job-search-card__location")),
                "posted": t.get("datetime", "") if t else "",
            }
        if len(cards) < 10:
            return


def linkedin_description(http, job):
    html = http.get(f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job['ext_id']}")
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    desc = _txt(soup.select_one(".show-more-less-html__markup"))
    crit = {}
    for li in soup.select(".description__job-criteria-item"):
        k, v = _txt(li.select_one("h3")), _txt(li.select_one("span"))
        if k:
            crit[k] = v
    extra = " | ".join(f"{k}: {v}" for k, v in crit.items())
    return f"{desc}\n\n[{extra}]" if extra else desc


# ---------------------------------------------------------------- Jobly
def jobly_search(http, keyword, pages=3):
    for page in range(pages):
        url = f"https://www.jobly.fi/en/jobs?search={quote_plus(keyword)}" + (f"&page={page}" if page else "")
        html = http.get(url)
        if not html:
            return
        soup = BeautifulSoup(html, "html.parser")
        nodes = soup.select("article.node-job")
        if not nodes:
            return
        for n in nodes:
            link = n.select_one("a.recruiter-job-link")
            href = urljoin("https://www.jobly.fi", n.get("about") or (link and link.get("href")) or "")
            jid = (n.get("id") or "").replace("node-", "") or href
            title = _txt(n.select_one("h2")) or (link and link.get("title")) or ""
            company = _txt(n.select_one(".recruiter-company-profile-job-organization"))
            loc = _txt(n.select_one(".location")) or _txt(n.select_one("[class*=location]"))
            date = _txt(n.select_one(".date"))
            if not (company and loc):
                # Fallback: teaser text order is title, date, company, location.
                parts = [p for p in n.get_text("|", strip=True).split("|") if p and p != "Bookmark job"]
                if title in parts:
                    parts = parts[parts.index(title) + 1:]
                date = date or (parts[0].rstrip(",") if parts else "")
                company = company or (parts[1] if len(parts) > 1 else "")
                loc = loc or (parts[2] if len(parts) > 2 else "")
            yield {"source": "jobly", "ext_id": jid, "url": href, "title": title,
                   "company": company, "location": loc, "posted": date.strip(" ,")}


def jobly_description(http, job):
    html = http.get(job["url"])
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    return _txt(soup.select_one(".field--name-body")) or _txt(soup.select_one("article"))


# ---------------------------------------------------------------- Duunitori
def duunitori_search(http, keyword, area, pages=3):
    for page in range(1, pages + 1):
        url = f"https://duunitori.fi/tyopaikat?haku={quote_plus(keyword)}&alue={quote_plus(area)}"
        if page > 1:
            url += f"&sivu={page}"
        html = http.get(url)
        if not html:
            return
        soup = BeautifulSoup(html, "html.parser")
        boxes = soup.select("div.job-box")
        if not boxes:
            return
        for b in boxes:
            a = b.select_one("a.job-box__hover")
            if not a:
                continue
            posted = _txt(b.select_one(".job-box__job-posted")).replace("Julkaistu", "").strip()
            yield {
                "source": "duunitori", "ext_id": a.get("data-id") or a["href"],
                "url": urljoin("https://duunitori.fi", a["href"]),
                "title": _txt(b.select_one(".job-box__title")) or _txt(a),
                "company": a.get("data-company", ""),
                "location": _txt(b.select_one(".job-box__job-location")).rstrip(" –"),
                "posted": posted,
            }
        if len(boxes) < 20:
            return


def duunitori_description(http, job):
    html = http.get(job["url"])
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    for sc in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(sc.string or "")
        except ValueError:
            continue
        if isinstance(data, dict) and data.get("@type") == "JobPosting" and data.get("description"):
            return BeautifulSoup(data["description"], "html.parser").get_text(" ", strip=True)
    return _txt(soup.select_one(".description-box")) or _txt(soup.select_one(".description--jobentry"))


DESCRIPTION_FETCHERS = {
    "linkedin": linkedin_description,
    "jobly": jobly_description,
    "duunitori": duunitori_description,
}


def city_of(location, cities):
    """Return the configured city a location string belongs to, or None."""
    loc = (location or "").lower()
    for city, cfg in cities.items():
        if any(m in loc for m in cfg["match"]):
            return city
    return None


def collect(cfg):
    """Run every enabled search and return de-duplicated job stubs tagged with a city."""
    http = Http(cfg.get("request_delay_seconds", 1.2))
    cities, src = cfg["cities"], cfg["sources"]
    seen = {}

    def add(job, city_hint=None):
        city = city_of(job["location"], cities) or city_hint
        if not city or not job["title"]:
            return
        job["city"] = city
        seen.setdefault((job["source"], job["ext_id"]), job)

    if src["linkedin"]["enabled"]:
        for city, ccfg in cities.items():
            for kw in cfg["keywords"][city]:
                before = len(seen)
                for j in linkedin_search(http, kw, ccfg["linkedin"], src["linkedin"]["pages_per_query"],
                                         src["linkedin"]["posted_within_days"]):
                    # LinkedIn already filters by location; accept region-level results ("Finland", remote)
                    # only when they don't name another city.
                    add(j, city if not re.search(r",", j["location"]) or city_of(j["location"], cities) else None)
                print(f"  linkedin  {city:<9} '{kw}': +{len(seen) - before}")

    if src["jobly"]["enabled"]:
        for kw in src["jobly"]["keywords"]:
            before = len(seen)
            for j in jobly_search(http, kw, src["jobly"]["pages_per_query"]):
                add(j)
            print(f"  jobly     '{kw}': +{len(seen) - before}")

    if src["duunitori"]["enabled"]:
        for city, ccfg in cities.items():
            if not ccfg.get("duunitori"):
                continue
            for kw in src["duunitori"]["keywords"]:
                before = len(seen)
                for j in duunitori_search(http, kw, ccfg["duunitori"], src["duunitori"]["pages_per_query"]):
                    add(j)
                print(f"  duunitori {city:<9} '{kw}': +{len(seen) - before}")

    return list(seen.values()), http
