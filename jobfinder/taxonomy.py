"""Skill taxonomy and career-path definitions used to read both the CV and job ads.

Each skill maps to regex aliases (matched case-insensitively on word boundaries).
Paths group skills into the directions the CV points towards.
"""
import re

SKILLS = {
    # Languages
    "Python": [r"python"],
    "TypeScript": [r"typescript", r"\bts\b"],
    "JavaScript": [r"javascript", r"\bjs\b", r"ecmascript"],
    "Java": [r"java(?!\s*script)"],
    "C": [r"\bc\b(?![+#])"],
    "C++": [r"c\+\+", r"\bcpp\b"],
    "C#": [r"c#", r"\.net\b", r"dotnet"],
    "Go": [r"\bgolang\b", r"\bgo\b(?=\s*(?:,|/|and|or|\)|lang))"],
    "Rust": [r"\brust\b"],
    "Kotlin": [r"kotlin"],
    "Swift": [r"\bswift\b"],
    "Scala": [r"\bscala\b"],
    "SQL": [r"\bsql\b"],
    "Bash": [r"\bbash\b", r"shell script"],
    "PowerShell": [r"powershell"],
    "HTML/CSS": [r"\bhtml5?\b", r"\bcss3?\b", r"tailwind", r"\bsass\b"],
    # Frontend
    "React": [r"\breact(?:\.js|js)?\b(?!\s*native)"],
    "React Native": [r"react\s*native"],
    "Next.js": [r"next\.?js"],
    "Angular": [r"angular"],
    "Vue": [r"\bvue(?:\.js)?\b"],
    "Flutter": [r"flutter"],
    # Backend
    "Node.js": [r"node\.?js", r"\bnode\b"],
    "Express": [r"express(?:\.js)?\b"],
    "Django": [r"django"],
    "FastAPI": [r"fastapi"],
    "Flask": [r"\bflask\b"],
    "Spring": [r"spring\s*boot", r"spring framework", r"\bspring\b(?!\s+classes)"],
    "REST APIs": [r"\brest(?:ful)?\b", r"\bapis?\b"],
    "GraphQL": [r"graphql"],
    "Microservices": [r"micro-?services?"],
    "PostgreSQL": [r"postgres(?:ql)?"],
    "MySQL": [r"mysql", r"mariadb"],
    "MongoDB": [r"mongo(?:db)?"],
    "Redis": [r"\bredis\b"],
    "Kafka": [r"\bkafka\b"],
    "Auth (JWT/OAuth)": [r"\bjwt\b", r"oauth", r"openid", r"cognito", r"keycloak"],
    # AI / ML / Data
    "LLMs / GenAI": [r"\bllms?\b", r"large language model", r"generative ai", r"gen\s?ai", r"\bgpt\b", r"prompt engineering", r"\brag\b", r"langchain", r"\bagents?\b(?=.{0,20}ai)"],
    "Machine Learning": [r"machine learning", r"\bml\b", r"koneoppi", r"maschinelles lernen"],
    "Deep Learning": [r"deep learning", r"neural network", r"pytorch", r"tensorflow", r"\bkeras\b"],
    "scikit-learn": [r"scikit-?learn", r"sklearn", r"xgboost", r"random forest"],
    "Computer Vision": [r"computer vision", r"opencv", r"\byolo\b", r"object detection"],
    "NLP / Search": [r"\bnlp\b", r"natural language", r"search engine", r"elasticsearch", r"opensearch", r"vector search", r"semantic search", r"recommend(?:er|ation)"],
    "Data Analysis": [r"pandas", r"numpy", r"data analy", r"matplotlib", r"seaborn", r"statistic"],
    "Data Engineering": [r"\betl\b", r"data pipeline", r"airflow", r"\bspark\b", r"databricks", r"snowflake", r"\bdbt\b"],
    "Data Visualization": [r"plotly", r"\bdash\b", r"power ?bi", r"tableau", r"grafana", r"dashboard"],
    # DevOps / Cloud
    "Docker": [r"docker", r"container"],
    "Kubernetes": [r"kubernetes", r"\bk8s\b", r"\bhelm\b", r"openshift"],
    "CI/CD": [r"ci\s*/\s*cd", r"continuous integration", r"continuous delivery", r"github actions", r"jenkins", r"gitlab ci", r"azure devops"],
    "AWS": [r"\baws\b", r"amazon web services", r"\bs3\b", r"lambda", r"cloudwatch"],
    "Azure": [r"\bazure\b"],
    "GCP": [r"\bgcp\b", r"google cloud"],
    "Terraform / IaC": [r"terraform", r"infrastructure as code", r"\biac\b", r"ansible", r"pulumi", r"cloudformation"],
    "Linux": [r"\blinux\b", r"\bunix\b"],
    "Monitoring": [r"monitoring", r"observability", r"prometheus", r"datadog", r"cloudwatch"],
    # Quality / practice
    "Testing": [r"\bpytest\b", r"unit test", r"test automation", r"\bjest\b", r"cypress", r"playwright", r"selenium", r"\btdd\b", r"automated test"],
    "Code Quality / Static Analysis": [r"static analysis", r"code quality", r"refactor", r"code smell", r"sonarqube", r"software metrics", r"clean code"],
    "Git": [r"\bgit\b", r"github", r"gitlab"],
    "Agile": [r"\bagile\b", r"scrum", r"kanban"],
    "Embedded": [r"embedded", r"firmware", r"\brtos\b", r"microcontroller"],
    "Mobile": [r"\bandroid\b", r"\bios\b", r"mobile app"],
    "Security": [r"cyber ?security", r"penetration", r"\bsiem\b", r"\bsoc\b"],
    "SAP / ERP": [r"\bsap\b", r"\berp\b", r"\babap\b"],
}

PATHS = {
    "Full-stack / Frontend": ["React", "TypeScript", "JavaScript", "Next.js", "Node.js", "Express", "HTML/CSS", "REST APIs", "Angular", "Vue"],
    "Backend / API": ["Python", "Django", "FastAPI", "Flask", "Node.js", "REST APIs", "PostgreSQL", "SQL", "Auth (JWT/OAuth)", "Microservices", "Java", "Spring"],
    "AI / ML Engineering": ["LLMs / GenAI", "Machine Learning", "Deep Learning", "scikit-learn", "Computer Vision", "NLP / Search", "Python", "Data Analysis"],
    "DevOps / Cloud / Platform": ["Docker", "Kubernetes", "CI/CD", "AWS", "Azure", "GCP", "Terraform / IaC", "Linux", "Monitoring", "Bash"],
    "Developer Tooling / Software Quality": ["Code Quality / Static Analysis", "Testing", "Java", "Python", "LLMs / GenAI", "CI/CD", "Git"],
    "Data Engineering / Analytics": ["Data Engineering", "SQL", "Python", "Data Analysis", "Data Visualization", "PostgreSQL"],
}

_COMPILED = {k: [re.compile(r"(?<![\w])" + p if not p.startswith(r"\b") else p, re.I) for p in v] for k, v in SKILLS.items()}


def count_skills(text: str) -> dict:
    """Return {skill: occurrence count} for every skill mentioned in text."""
    out = {}
    for skill, pats in _COMPILED.items():
        n = sum(len(p.findall(text)) for p in pats)
        if n:
            out[skill] = n
    return out
