"""Read the CV (.docx) and derive a skill-strength profile and career-path affinities."""
import re
import zipfile
from dataclasses import dataclass, field

from .taxonomy import PATHS, count_skills

# Sections whose mentions count as hands-on evidence (weighted higher than a skills list).
EVIDENCE_SECTIONS = ("PROJECTS", "WORK EXPERIENCE", "SUMMARY")


@dataclass
class Profile:
    name: str
    text: str
    strengths: dict                 # skill -> 0..1
    paths: dict                     # path -> 0..1 (normalised, best = 1)
    level: str = "student"          # student / junior
    notes: list = field(default_factory=list)

    def top_skills(self, n=12):
        return sorted(self.strengths.items(), key=lambda kv: -kv[1])[:n]


def read_docx_text(path) -> str:
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf8")
    paras = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", xml, re.S):
        t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
        if t.strip():
            paras.append(t.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">"))
    return "\n".join(paras)


def _split_sections(text):
    sections, current = {}, "HEADER"
    for line in text.splitlines():
        s = line.strip()
        if s and s.upper() == s and len(s) < 40 and re.search(r"[A-Z]{4}", s):
            current = s.strip()
            continue
        sections.setdefault(current, []).append(line)
    return {k: "\n".join(v) for k, v in sections.items()}


def build_profile(path) -> Profile:
    text = read_docx_text(path)
    sections = _split_sections(text)
    evidence = "\n".join(v for k, v in sections.items() if any(e in k for e in EVIDENCE_SECTIONS))

    total = count_skills(text)
    hands_on = count_skills(evidence)
    strengths = {}
    for skill, n in total.items():
        # Listed once in the skills table ~0.37; every hands-on mention (projects/work) adds evidence.
        score = 0.35 + 0.10 * min(hands_on.get(skill, 0), 5) + 0.02 * min(n, 10)
        strengths[skill] = round(min(score, 1.0), 2)
    if re.search(r"python\s*\(primary\)", text, re.I):
        strengths["Python"] = 1.0

    raw_paths = {}
    for p, skills in PATHS.items():
        vals = sorted((strengths.get(s, 0) for s in skills), reverse=True)[:6]
        raw_paths[p] = sum(vals) / len(vals)
    best = max(raw_paths.values()) or 1
    paths = {p: round(v / best, 2) for p, v in sorted(raw_paths.items(), key=lambda kv: -kv[1])}

    notes = []
    if re.search(r"\[[^\]]*fill in[^\]]*\]", text, re.I):
        notes.append("Your CV still contains a template placeholder ('[... fill in what you actually built]') in the FPT Retail entry. Remove it before applying.")

    name = text.splitlines()[0].strip().title() if text else "Candidate"
    level = "student" if re.search(r"student|werkstudent|internship|b\.sc", text, re.I) else "junior"
    return Profile(name=name, text=text, strengths=strengths, paths=paths, level=level, notes=notes)
