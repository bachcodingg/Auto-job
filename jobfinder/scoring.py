"""Rule-based CV <-> job matching. Produces a 0-100 score plus human-readable reasons."""
import re

from .taxonomy import PATHS, count_skills

# A title must look like software work to be kept at all.
SE_STRONG = re.compile(
    r"software|developer|development engineer|programm|ohjelmisto|kehittäjä|kehittaja|entwickler|softwareentwicklung|"
    r"devops|\bsre\b|site reliability|full[\s-]?stack|front[\s-]?end|back[\s-]?end|web\b|mobile|"
    r"machine learning|\bml\b|\bai\b|computer vision|deep learning|multimodal|\bnlp\b|\bllm|"
    r"artificial intelligence|data scien|data engineer|mlops|cloud|platform engineer|"
    r"test automation|\bqa\b|python|java|react|typescript|informatik|it[\s-]?trainee|coder|tekoäly", re.I)
SE_WEAK = re.compile(r"engineer|insinööri|ingenieur|trainee|intern|harjoittelija|werkstudent|working student|thesis|abschlussarbeit", re.I)
NOT_SE = re.compile(
    r"mechanical|mekaniikka|konetekniik|electrical|sähkö|electric|hvac|\blvi\b|construction|rakennus|civil|structural|"
    r"process engineer|prosessi|chemical|kemia|sales|myynti|myyjä|vertrieb|account manager|nurse|hoitaja|"
    r"logistic|warehouse|varasto|accountant|kirjanpi|marketing|markkinointi|recruit|rekrytoi|hardware design|"
    r"maintenance|huolto|asentaja|installer|welder|hitsaaja|automation engineer|automaatio|field service|"
    r"business development|partner\s?management|treasury|finance|controller|isännöinti|kiinteistö|\bhr\b|"
    r"puolustusvoim|legal|lawyer|juridi|customer service|asiakaspalvel|teacher|opettaja|"
    r"chemistry|biophys|biolog|business developer|liiketoiminnan kehittäjä", re.I)
MASTERS_ONLY = re.compile(r"master'?s thesis|masterarbeit|diplomityö|master thesis", re.I)
DOCTORAL = re.compile(r"doctoral|\bph\.?d\b|väitöskirja|tohtorikoulutettava|doktorand", re.I)

LEVEL_PATTERNS = [
    ("student", re.compile(r"werkstudent|working student|student|intern(ship)?\b|praktikum|praktikant|harjoittelija|"
                           r"kesätyö|summer (job|trainee)|thesis|abschlussarbeit|masterarbeit|diplomityö|opinnäyte", re.I), 1.0),
    ("trainee/junior", re.compile(r"trainee|junior|graduate|entry[\s-]level|nuorempi|associate|early career|absolvent|berufseinsteiger", re.I), 0.95),
    ("senior+", re.compile(r"senior|\bsr\.?\b|lead\b|principal|staff\b|head of|director|architect|arkkitehti|manager|päällikkö|"
                           r"johtaja|chief|\bvp\b|expert|asiantuntija|kokenut|experienced", re.I), 0.45),
]

# A number of years only counts when "experience" is close by: "3+ years of experience",
# "vähintään 3 vuoden kokemus", "mindestens 3 Jahre Berufserfahrung".
YEARS = re.compile(r"(\d{1,2})\s*(?:\+|[-–]\s*\d{1,2}|to\s*\d{1,2})?\s*\+?\s*"
                   r"(?:years?|yrs|vuo(?:den|tta|si)|jahre?n?)[^.;]{0,40}?(?:experience|kokemus|erfahrung)", re.I)
VAGUE_YEARS = re.compile(r"several years|many years|extensive experience|useamman vuoden|monen vuoden|mehrjährig|langjährig", re.I)
OPTIONAL = re.compile(r"plus|advantage|nice to have|bonus|eduksi|\betu\b|katsotaan|von vorteil|wünschenswert|"
                      r"wäre schön|ideally|preferred", re.I)

LANG_REQUIRED = {
    "finnish": re.compile(
        r"(fluent|excellent|native|good|strong|professional|proficient|working)[^.]{0,30}finnish|"
        r"finnish[^.]{0,25}(is|are) (required|mandatory|a must|needed)|"
        r"(sujuva|erinomainen|hyvä|vahva|moitteeton)[^.]{0,20}suomen kiel|suomen kielen[^.]{0,30}(taito|osaaminen)", re.I),
    "german": re.compile(
        r"(fließend|fliessend|sehr gute|gute|verhandlungssicher|exzellente)[^.]{0,25}deutsch|"
        r"deutsch[^.]{0,25}(fließend|verhandlungssicher|c1|muttersprach|in wort und schrift)|"
        r"(fluent|excellent|native|good|strong|business)[^.]{0,30}german|german[^.]{0,25}(c1|b2|required|mandatory|a must|fluent)", re.I),
}

FI_WORDS = re.compile(r"\b(ja|on|sekä|meillä|tehtävä|haemme|työ|kanssa|osaamista|olet|että)\b", re.I)
DE_WORDS = re.compile(r"\b(und|die|der|wir|für|mit|ist|bei|deine|du|sie|unsere|bist)\b", re.I)

PATH_LABEL_HINTS = {
    "AI / ML Engineering": re.compile(r"machine learning|\bml\b|\bai\b|data scien|llm|genai|computer vision|nlp|tekoäly", re.I),
    "DevOps / Cloud / Platform": re.compile(r"devops|\bsre\b|cloud|platform|infrastructure|reliability", re.I),
    "Full-stack / Frontend": re.compile(r"full[\s-]?stack|front[\s-]?end|web|react|ui\b", re.I),
    "Backend / API": re.compile(r"back[\s-]?end|api|python developer|java developer", re.I),
    "Developer Tooling / Software Quality": re.compile(r"\bqa\b|test|quality|tooling|developer experience", re.I),
    "Data Engineering / Analytics": re.compile(r"data engineer|analytics|\bbi\b|data platform", re.I),
}


CORE_TECH = {"Python", "Java", "TypeScript", "JavaScript", "C++", "C#", "Go", "React", "Node.js", "Docker",
             "Kubernetes", "CI/CD", "Machine Learning", "LLMs / GenAI", "SQL", "Git", "REST APIs", "AWS", "Azure"}


def is_software_job(title, desc=None):
    """Clearly-software titles pass; generic ones ("Trainee", "Engineer") need a tech-heavy description."""
    if SE_STRONG.search(title):
        return not (NOT_SE.search(title) and not re.search(r"software|ohjelmisto|entwickler|web developer|full[\s-]?stack",
                                                            title, re.I))
    if not SE_WEAK.search(title) or NOT_SE.search(title):
        return False
    if desc is None:
        return True  # undecided until the description has been fetched
    return len(CORE_TECH & set(count_skills(desc))) >= 3


def detect_level(title, desc):
    for name, pat, mult in LEVEL_PATTERNS:
        if pat.search(title):
            return name, mult
    # Fall back to LinkedIn's seniority criterion if present.
    m = re.search(r"Seniority level: ([^|\]]+)", desc or "")
    if m:
        s = m.group(1).lower()
        if "intern" in s:
            return "student", 1.0
        if "entry" in s:
            return "trainee/junior", 0.95
        if any(k in s for k in ("mid-senior", "director", "executive")):
            return "senior+", 0.5
    return "unspecified", 0.8


def detect_language(desc):
    words = max(len(desc.split()), 1)
    fi, de = len(FI_WORDS.findall(desc)) / words, len(DE_WORDS.findall(desc)) / words
    if fi > 0.03 and fi > de:
        return "fi"
    if de > 0.05:
        return "de"
    return "en"


def score_job(job, profile, cfg):
    title, desc = job["title"], job.get("description") or ""
    text = f"{title}\n{title}\n{desc}"          # title counted twice = emphasis
    found = count_skills(text)
    reasons, flags = [], []

    # --- skill fit: how much of what the job asks for is backed by the CV
    if found:
        weights = {s: (2.0 if s in count_skills(title) else 1.0) * min(n, 3) for s, n in found.items()}
        covered = sum(w * profile.strengths.get(s, 0) for s, w in weights.items())
        # Smooth toward a neutral 0.5 so an ad naming a single skill can't reach a perfect fit.
        skill_fit = (covered + 0.5 * 3) / (sum(weights.values()) + 3)
    else:
        skill_fit = 0.35
    matched = sorted((s for s in found if profile.strengths.get(s, 0) >= 0.6), key=lambda s: -profile.strengths[s])
    partial = [s for s in found if 0 < profile.strengths.get(s, 0) < 0.6]
    gaps = sorted((s for s in found if s not in profile.strengths), key=lambda s: -found[s])

    # --- career-path alignment
    path_hits = {p: sum(min(found.get(s, 0), 3) for s in skills) for p, skills in PATHS.items()}
    for p, rx in PATH_LABEL_HINTS.items():
        if rx.search(title):
            path_hits[p] += 6
    job_path = max(path_hits, key=path_hits.get) if any(path_hits.values()) else None
    path_fit = profile.paths.get(job_path, 0.5) if job_path else 0.5

    # --- seniority / experience
    level, level_mult = detect_level(title, desc)
    if MASTERS_ONLY.search(title):
        level_mult *= 0.7
        flags.append("Master's thesis: needs Master's enrolment")
    elif DOCTORAL.search(title):
        level_mult *= 0.55
        flags.append("doctoral position: needs a Master's degree")
    years = [int(y) for y in YEARS.findall(desc) if 0 < int(y) <= 15]
    min_years = min(years) if years else (3 if VAGUE_YEARS.search(desc) else None)
    years_mult = 1.0
    comfy = cfg["candidate"]["max_comfortable_years"]
    if min_years is not None and min_years > comfy:
        years_mult = 0.75 if min_years <= 4 else 0.5
        flags.append(f"asks for {min_years}+ years of experience")

    # --- language
    lang_mult = 1.0
    ad_lang = detect_language(desc) if desc else "en"
    langs = cfg["candidate"]["languages"]
    for lang, rx in LANG_REQUIRED.items():
        m = rx.search(desc)
        if not m or langs.get(lang, "A1")[0] not in "AB":
            continue
        context = desc[max(0, m.start() - 80): m.end() + 80]
        if OPTIONAL.search(context):
            lang_mult *= 0.92
            flags.append(f"{lang.title()} is a plus")
        else:
            lang_mult *= 0.55
            flags.append(f"requires strong {lang.title()} (you: {langs.get(lang)})")
    if ad_lang == "fi" and not any("Finnish" in f for f in flags):
        lang_mult *= 0.8
        flags.append("ad written in Finnish")
    if ad_lang == "de" and not any("German" in f for f in flags):
        lang_mult *= 0.8
        flags.append("ad written in German")
    if not desc:
        flags.append("no description fetched, title-only score")

    w = cfg["weights"]
    fit = (w["skills"] * skill_fit + w["path"] * path_fit) / (w["skills"] + w["path"])
    score = round(100 * fit * level_mult * years_mult * lang_mult, 1)

    if matched:
        reasons.append("Strong overlap: " + ", ".join(matched[:6]))
    if job_path:
        reasons.append(f"Path: {job_path} (your affinity {path_fit:.0%})")
    reasons.append(f"Level: {level}")

    return {
        "score": score, "skill_fit": round(skill_fit, 2), "path": job_path, "path_fit": path_fit,
        "level": level, "min_years": min_years, "ad_lang": ad_lang,
        "matched": matched, "partial": partial, "gaps": gaps[:8], "flags": flags, "reasons": reasons,
    }
