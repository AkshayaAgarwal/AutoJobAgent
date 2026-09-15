#!/usr/bin/env python3
"""
Resume Parser - Extract key information from a resume (PDF, DOCX, or TXT).

Returns a dict:
    name, email, phone, linkedin, github,
    skills (list), technical_stack (list),
    experience_years (int), companies (list), summary (str)

Design notes / fixes over the previous version:
- Technical skills use WORD-BOUNDARY matching so "Java" no longer matches
  inside "JavaScript" and "Go" no longer matches inside "Google".
- Skills section detection also recognises headings like "CORE COMPETENCIES",
  "TECHNICAL SKILLS", "TECH STACK", not just the literal word "skills".
- LinkedIn / GitHub are extracted as clean URLs, not the whole contact line.
- Companies are pulled from the EXPERIENCE section using the common
  "Job Title | Company   Dates" resume pattern, with noise filtered out.
- Phone matching is stricter to avoid grabbing random digit runs.
"""

import os
import re
import sys
from pathlib import Path


# --- canonical technical skills. Each entry: (canonical_name, regex_pattern) ---
# Patterns are matched case-insensitively with word boundaries where sensible.
TECH_SKILLS = [
    ("Python", r"python"),
    ("JavaScript", r"javascript|(?<![a-z])js(?![a-z])"),
    ("TypeScript", r"typescript"),
    ("Java", r"\bjava\b(?!script)"),
    ("C#", r"c#|c\s?sharp"),
    ("C++", r"c\+\+"),
    ("Go", r"\bgo(?:lang)?\b"),
    ("Rust", r"\brust\b"),
    ("PHP", r"\bphp\b"),
    ("Ruby", r"\bruby\b"),
    ("React", r"react(?:\.js)?"),
    ("Next.js", r"next\.?js"),
    ("Vue", r"\bvue(?:\.js)?\b"),
    ("Angular", r"\bangular\b"),
    ("Node.js", r"node\.?js"),
    ("Express", r"\bexpress(?:\.js)?\b"),
    ("Django", r"\bdjango\b"),
    ("FastAPI", r"fastapi"),
    ("Flask", r"\bflask\b"),
    (".NET", r"\.net\b"),
    ("SQL", r"\bsql\b"),
    ("PostgreSQL", r"postgre(?:sql)?"),
    ("MySQL", r"\bmysql\b"),
    ("MongoDB", r"mongo(?:db)?"),
    ("Redis", r"\bredis\b"),
    ("Elasticsearch", r"elasticsearch"),
    ("Databricks", r"databricks"),
    ("AWS", r"\baws\b|amazon web services"),
    ("Azure", r"\bazure\b"),
    ("GCP", r"\bgcp\b|google cloud"),
    ("Docker", r"\bdocker\b"),
    ("Kubernetes", r"\bkubernetes\b|\bk8s\b"),
    ("Terraform", r"terraform"),
    ("Git", r"\bgit\b"),
    ("CI/CD", r"ci/?cd"),
    ("REST", r"\brest(?:ful)?\b"),
    ("GraphQL", r"graphql"),
    ("gRPC", r"\bgrpc\b"),
    ("Microservices", r"microservices?"),
    ("Machine Learning", r"machine learning|\bml\b"),
    ("NLP", r"\bnlp\b|natural language processing"),
    ("LLM", r"\bllms?\b"),
    ("OpenAI API", r"openai(?:\s+api)?"),
    ("Claude", r"\bclaude\b"),
    ("GPT", r"\bgpt\b"),
    ("LangChain", r"langchain"),
    ("LlamaIndex", r"llama\s?index"),
    ("HuggingFace", r"hugging\s?face"),
    ("RAG", r"\brag\b"),
    ("Agentic AI", r"agentic"),
    ("Prompt Engineering", r"prompt engineering"),
    ("Streamlit", r"streamlit"),
    ("Material UI", r"material ui|\bmui\b"),
    ("D3.js", r"d3\.?js"),
    ("Highcharts", r"highcharts"),
    ("Chart.js", r"chart\.?js"),
    ("Pandas", r"\bpandas\b"),
    ("NumPy", r"\bnumpy\b"),
    ("PyTorch", r"pytorch"),
    ("TensorFlow", r"tensorflow"),
]

# Words that look like companies but are noise when scanning the experience block.
COMPANY_NOISE = {
    "the", "and", "with", "using", "within", "across", "for", "from", "of",
    "present", "current", "remote", "hybrid", "onsite", "on-site",
    "australia", "india", "sponsorship", "required", "no sponsorship required",
    "gmail", "gmail.com", "linkedin", "github", "professional experience",
    "professional summary", "core competencies", "education", "certifications",
    "key projects", "personal project",
}

MONTHS = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"


def _clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def _extract_name(lines):
    """First non-empty line that looks like a person's name (2-4 capitalised words)."""
    for line in lines[:6]:
        t = line.strip()
        if not t:
            continue
        if any(x in t.lower() for x in ["@", "http", "linkedin", "github", "|", "+", "·"]):
            continue
        words = t.split()
        if 1 < len(words) <= 4 and len(t) < 50:
            # mostly alphabetic
            if sum(c.isalpha() or c.isspace() for c in t) / len(t) > 0.8:
                return t.title() if t.isupper() else t
    return ""


def _extract_contact(text):
    email = ""
    m = re.search(r"[\w.\-+]+@[\w.\-]+\.\w+", text)
    if m:
        email = m.group(0)

    linkedin = ""
    m = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-/]+", text, re.I)
    if m:
        linkedin = m.group(0).rstrip("/.,)")

    github = ""
    m = re.search(r"(?:https?://)?(?:www\.)?github\.com/[\w\-/]+", text, re.I)
    if m:
        github = m.group(0).rstrip("/.,)")

    # Phone: require a plausible phone shape (optional +, 8-15 digits with separators),
    # and skip anything that is really a year range or a visa subclass number.
    phone = ""
    for cand in re.findall(r"\+?\d[\d\s().\-]{7,}\d", text):
        digits = re.sub(r"\D", "", cand)
        if 8 <= len(digits) <= 15 and not re.fullmatch(r"(19|20)\d{2}", digits):
            phone = _clean(cand)
            break

    return email, phone, linkedin, github


def _section(text, start_headings, end_headings):
    """
    Return the slice of text between a start heading and the next end heading.

    Headings must appear at the START of a line (optionally with surrounding
    whitespace/punctuation). This prevents body words like "experience"
    appearing mid-sentence from prematurely ending a section.
    """
    def heading_group(headings):
        return r"|".join(r"[ \t]*%s[ \t]*:?[ \t]*" % h for h in headings)

    start_pat = r"(?im)^(?:%s)$" % heading_group(start_headings)
    start = re.search(start_pat, text)
    if not start:
        return ""
    rest = text[start.end():]
    end_pat = r"(?im)^(?:%s)$" % heading_group(end_headings)
    end = re.search(end_pat, rest)
    return rest[:end.start()] if end else rest


def _extract_skills(text):
    """Free-text skills from a competencies/skills section (comma/·/| separated)."""
    block = _section(
        text,
        [r"technical skills", r"core competencies", r"tech stack", r"\bskills\b"],
        [r"professional experience", r"experience", r"education",
         r"projects", r"certifications", r"summary"],
    )
    if not block:
        return []
    # split on common resume separators
    tokens = re.split(r"[·|,\n;•]", block)
    skills = []
    for tok in tokens:
        t = _clean(tok)
        # drop the category labels like "AI / ML:" and overly long phrases
        t = re.sub(r"^[A-Za-z /&]+:", "", t).strip()
        if 1 < len(t) <= 40 and not t.lower().startswith(("http", "www")):
            skills.append(t)
    # de-dupe preserving order
    seen, out = set(), []
    for s in skills:
        k = s.lower()
        if k not in seen:
            seen.add(k)
            out.append(s)
    return out[:30]


def _extract_tech_stack(text):
    found = []
    for canonical, pattern in TECH_SKILLS:
        if re.search(pattern, text, re.IGNORECASE):
            found.append(canonical)
    return found


def _extract_experience_years(text):
    patterns = [
        r"(\d+)\+?\s*years?\s*(?:of\s*)?(?:commercial|professional)?\s*experience",
        r"experience\s*(?:of\s*)?(\d+)\+?\s*years?",
        r"with\s+(\d+)\+?\s*years?",
        r"(\d+)\+?\s*years?\s+in\b",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return 0


def _extract_companies(text):
    """
    Pull employers from the EXPERIENCE section.
    Handles the common pattern:  <Job Title> | <Company>   <Dates>
    e.g. "AI Full Stack Engineer | Fractal Analytics   Jul 2024 - Present"
    """
    block = _section(
        text,
        [r"professional experience", r"work experience", r"employment", r"experience"],
        [r"education", r"key projects", r"projects", r"certifications",
         r"additional information", r"skills"],
    )
    if not block:
        block = text

    companies = []
    for line in block.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        # take the part after the last '|', then cut off any date tail
        after = line.split("|")[-1]
        after = re.split(MONTHS + r"|\b(19|20)\d{2}\b|\t", after)[0]
        cand = _clean(after)
        low = cand.lower()
        if not cand or low in COMPANY_NOISE:
            continue
        if "@" in cand or "http" in low or low.startswith("www"):
            continue
        # a company name is short-ish and mostly letters
        if 2 <= len(cand) <= 45 and re.search(r"[A-Za-z]", cand):
            companies.append(cand)

    # de-dupe preserving order
    seen, out = set(), []
    for c in companies:
        k = c.lower()
        if k not in seen:
            seen.add(k)
            out.append(c)
    return out[:6]


def _extract_summary(text):
    block = _section(
        text,
        [r"professional summary", r"\bsummary\b", r"\bprofile\b", r"\babout\b"],
        [r"core competencies", r"technical skills", r"experience",
         r"education", r"skills"],
    )
    return _clean(block)[:400]


def parse_text_resume(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    email, phone, linkedin, github = _extract_contact(text)

    return {
        "name": _extract_name(lines),
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "github": github,
        "skills": _extract_skills(text),
        "technical_stack": _extract_tech_stack(text),
        "experience_years": _extract_experience_years(text),
        "companies": _extract_companies(text),
        "summary": _extract_summary(text),
    }


def parse_pdf_resume(filepath):
    try:
        import pdfplumber
        text = ""
        with pdfplumber.open(filepath) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        return parse_text_resume(text)
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return None


def parse_docx_resume(filepath):
    try:
        from docx import Document
        doc = Document(filepath)
        parts = [p.text for p in doc.paragraphs]
        # include table cells too (many resumes keep contact/skills in tables)
        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    parts.append(cell.text)
        return parse_text_resume("\n".join(parts))
    except Exception as e:
        print(f"Error reading DOCX: {e}")
        return None


def parse_resume(resume_path):
    if not os.path.exists(resume_path):
        print("Resume file not found")
        return None
    ext = Path(resume_path).suffix.lower()
    print(f"Parsing resume: {resume_path}")
    if ext == ".pdf":
        return parse_pdf_resume(resume_path)
    elif ext == ".docx":
        return parse_docx_resume(resume_path)
    elif ext == ".txt":
        return parse_text_resume(Path(resume_path).read_text(encoding="utf-8"))
    else:
        print("Unsupported format")
        return None


if __name__ == "__main__":
    import json
    data = parse_resume(sys.argv[1])
    if data:
        print(json.dumps(data, indent=2, ensure_ascii=False))