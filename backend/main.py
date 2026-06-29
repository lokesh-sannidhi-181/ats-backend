from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from docx import Document
import pdfplumber
import asyncio
import spacy
import os
import io
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def load_spacy_model():
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        return spacy.blank("en")


nlp = load_spacy_model()


def get_cors_origins() -> list[str]:
    raw = os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    if raw.strip() == "*":
        return ["*"]
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────
# Keyword Bank
# ─────────────────────────────────────────
KEYWORD_BANK = {
    "programming_languages": [
        "python", "javascript", "typescript", "java", "c++", "c#", "go",
        "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "perl"
    ],
    "frontend": [
        "react", "angular", "vue", "html", "css", "sass", "tailwind",
        "bootstrap", "redux", "nextjs", "webpack", "vite", "jquery"
    ],
    "backend": [
        "fastapi", "django", "flask", "nodejs", "express", "spring",
        "laravel", "rails", "graphql", "rest", "api", "microservices", "grpc"
    ],
    "databases": [
        "sql", "postgresql", "mysql", "mongodb", "redis", "sqlite",
        "elasticsearch", "cassandra", "dynamodb", "firebase", "oracle"
    ],
    "devops_cloud": [
        "docker", "kubernetes", "aws", "azure", "gcp", "ci/cd", "jenkins",
        "github actions", "terraform", "ansible", "linux", "nginx", "helm"
    ],
    "data_ai": [
        "machine learning", "deep learning", "tensorflow", "pytorch",
        "scikit-learn", "pandas", "numpy", "data analysis", "nlp",
        "computer vision", "llm", "ai", "neural network", "huggingface",
        "langchain", "openai", "reinforcement learning", "data science"
    ],
    "soft_skills": [
        "leadership", "communication", "teamwork", "problem solving",
        "critical thinking", "project management", "agile", "scrum",
        "mentoring", "collaboration", "time management"
    ],
    "tools": [
        "git", "github", "jira", "confluence", "figma", "postman",
        "vs code", "linux", "bash", "excel", "tableau", "power bi",
        "notion", "slack", "trello"
    ],
    "testing": [
        "unit testing", "integration testing", "pytest", "jest",
        "selenium", "cypress", "tdd", "bdd", "qa", "testing"
    ],
    "security": [
        "oauth", "jwt", "ssl", "encryption", "cybersecurity",
        "penetration testing", "firewall", "authentication"
    ]
}

ALL_KEYWORDS = [kw for kws in KEYWORD_BANK.values() for kw in kws]

ACTION_VERBS = [
    "led", "managed", "built", "designed", "developed", "created",
    "implemented", "delivered", "improved", "optimized", "launched",
    "architected", "scaled", "automated", "reduced", "increased",
    "collaborated", "mentored", "deployed", "integrated", "migrated",
    "refactored", "streamlined", "coordinated", "established"
]

EDUCATION_DEGREES = [
    "b.tech", "b.e", "bachelor", "m.tech", "master", "mba", "phd",
    "doctorate", "b.sc", "m.sc", "bca", "mca", "diploma", "associate"
]

SECTION_HEADERS = [
    "experience", "education", "skills", "projects", "summary",
    "objective", "certifications", "achievements", "publications",
    "languages", "interests", "awards", "volunteer"
]

EXPERIENCE_PATTERNS = {
    "senior": ["senior", "lead", "principal", "staff", "architect", "manager", "head", "director"],
    "mid": ["mid", "intermediate", "engineer", "developer", "analyst", "specialist"],
    "junior": ["junior", "entry", "intern", "trainee", "fresher", "graduate"]
}


# ─────────────────────────────────────────
# Pydantic Models
# ─────────────────────────────────────────
class ContactInfo(BaseModel):
    email: str
    phone: str
    linkedin: str
    github: str


class SkillBreakdown(BaseModel):
    programming_languages: list[str]
    frontend: list[str]
    backend: list[str]
    databases: list[str]
    devops_cloud: list[str]
    data_ai: list[str]
    soft_skills: list[str]
    tools: list[str]
    testing: list[str]
    security: list[str]


class ResumeAnalysis(BaseModel):
    ats_score: int
    match_score: int
    experience_level: str
    contact_info: ContactInfo
    skill_breakdown: SkillBreakdown
    skills_found: list[str]
    missing_keywords: list[str]
    matched_requirements: list[str]
    missing_requirements: list[str]
    sections_found: list[str]
    sections_missing: list[str]
    action_verbs_used: list[str]
    keyword_density: float
    strengths: list[str]
    weaknesses: list[str]
    suggestions: list[str]
    overall_verdict: str


class CandidateResult(BaseModel):
    rank: int
    filename: str
    ats_score: int
    match_score: int
    experience_level: str
    skills_found: list[str]
    skill_breakdown: SkillBreakdown
    matched_requirements: list[str]
    missing_requirements: list[str]
    skill_gap: list[str]
    action_verbs_used: list[str]
    sections_found: list[str]
    suggestions: list[str]
    overall_verdict: str
    status: str


# ─────────────────────────────────────────
# Text Extraction
# ─────────────────────────────────────────
def extract_text_from_pdf(file_bytes: bytes) -> str:
    text = ""
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def extract_text_from_docx(file_bytes: bytes) -> str:
    document = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in document.paragraphs if p.text.strip())


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    if filename.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    if filename.lower().endswith(".docx"):
        return extract_text_from_docx(file_bytes)
    raise HTTPException(status_code=400, detail="Only PDF and DOCX resumes are supported")


# ─────────────────────────────────────────
# Extraction Functions
# ─────────────────────────────────────────
def extract_contact_info(text: str) -> ContactInfo:
    email_match = re.search(r"[\w.+-]+@[\w-]+\.\w+", text)
    phone_match = re.search(
        r"(\+?\d{1,3}[\s\-\.]?)?"
        r"(\(?\d{3}\)?[\s\-\.]?)"
        r"(\d{3}[\s\-\.]?\d{4})"
        r"|\+?\d{1,3}[\s\-]?\d{10}",
        text,
    )
    linkedin_match = re.search(r"linkedin\.com/in/[\w-]+", text, re.IGNORECASE)
    github_match = re.search(r"github\.com/[\w-]+", text, re.IGNORECASE)

    return ContactInfo(
        email=email_match.group() if email_match else "",
        phone=phone_match.group() if phone_match else "",
        linkedin=linkedin_match.group() if linkedin_match else "",
        github=github_match.group() if github_match else "",
    )


def detect_experience_level(text: str) -> str:
    text_lower = text.lower()

    # Method 1 — explicit years mentioned
    years_match = re.search(
        r"(\d+)\+?\s*years?\s*(of)?\s*(experience|exp)", text_lower
    )
    if years_match:
        years = int(years_match.group(1))
        if years >= 7:
            return "Senior"
        elif years >= 3:
            return "Mid-Level"
        else:
            return "Junior"

    # Method 2 — check junior FIRST (most specific)
    junior_keywords = [
        "intern", "internship", "trainee", "fresher",
        "graduate", "final year", "final-year",
        "entry level", "entry-level", "student",
        "b.tech", "b.e", "bca", "undergraduate"
    ]
    if any(kw in text_lower for kw in junior_keywords):
        return "Junior"

    # Method 3 — check senior (specific titles only)
    senior_keywords = [
        "senior", "lead engineer", "lead developer",
        "principal", "staff engineer", "architect",
        "engineering manager", "head of", "director"
    ]
    if any(kw in text_lower for kw in senior_keywords):
        return "Senior"

    # Method 4 — mid level (only if no junior/senior found)
    mid_keywords = [
        "mid-level", "mid level", "associate engineer",
        "associate developer", "software engineer ii",
        "developer ii", "analyst ii"
    ]
    if any(kw in text_lower for kw in mid_keywords):
        return "Mid-Level"

    # Method 5 — years of experience in education/work
    if re.search(r"20(1[5-9]|2[0-1]).*20(1[8-9]|2[0-4])", text_lower):
        return "Mid-Level"

    return "Not Specified"



def detect_sections(text: str) -> tuple[list[str], list[str]]:
    text_lower = text.lower()
    found = [s.title() for s in SECTION_HEADERS if s in text_lower]
    missing = [s.title() for s in SECTION_HEADERS if s not in text_lower]
    return found, missing


def detect_action_verbs(text: str) -> list[str]:
    text_lower = text.lower()
    return [v for v in ACTION_VERBS if re.search(rf"\b{v}\b", text_lower)]


def get_skill_breakdown(text: str) -> SkillBreakdown:
    return SkillBreakdown(
        programming_languages=find_keywords_in_text(text, KEYWORD_BANK["programming_languages"]),
        frontend=find_keywords_in_text(text, KEYWORD_BANK["frontend"]),
        backend=find_keywords_in_text(text, KEYWORD_BANK["backend"]),
        databases=find_keywords_in_text(text, KEYWORD_BANK["databases"]),
        devops_cloud=find_keywords_in_text(text, KEYWORD_BANK["devops_cloud"]),
        data_ai=find_keywords_in_text(text, KEYWORD_BANK["data_ai"]),
        soft_skills=find_keywords_in_text(text, KEYWORD_BANK["soft_skills"]),
        tools=find_keywords_in_text(text, KEYWORD_BANK["tools"]),
        testing=find_keywords_in_text(text, KEYWORD_BANK["testing"]),
        security=find_keywords_in_text(text, KEYWORD_BANK["security"]),
    )


def calculate_keyword_density(text: str, skills_found: list[str]) -> float:
    word_count = len(re.findall(r"\w+", text))
    if word_count == 0:
        return 0.0
    return round((len(skills_found) / word_count) * 100, 2)


# ─────────────────────────────────────────
# NLP Functions
# ─────────────────────────────────────────
def extract_keywords_with_spacy(text: str) -> list[str]:
    doc = nlp(text.lower())
    keywords = set()

    try:
        for chunk in doc.noun_chunks:
            clean = chunk.text.strip()
            if 2 <= len(clean.split()) <= 4:
                keywords.add(clean)
    except Exception:
        pass

    for ent in getattr(doc, "ents", []):
        if ent.label_ in ("ORG", "PRODUCT", "GPE", "WORK_OF_ART"):
            keywords.add(ent.text.lower().strip())

    for token in doc:
        if token.pos_ in ("NOUN", "PROPN") and not token.is_stop and len(token.text) > 2:
            keywords.add(token.lemma_.lower().strip())

    return list(keywords)


def find_keywords_in_text(text: str, keyword_list: list[str]) -> list[str]:
    normalized = text.lower()
    return [
        kw for kw in keyword_list
        if re.search(rf"\b{re.escape(kw)}\b", normalized)
    ]


def calculate_similarity_score(text1: str, text2: str) -> int:
    if not text1.strip() or not text2.strip():
        return 0
    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=1000,
        )
        matrix = vectorizer.fit_transform([text1, text2])
        score = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
        return min(99, int(score * 100))
    except Exception:
        return 0


# ─────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────
def calculate_ats_score(
    resume_text: str,
    skills_found: list[str],
    word_count: int,
    sections_found: list[str],
    action_verbs: list[str],
    contact_info: ContactInfo,
) -> int:
    score = 0

    score += min(30, len(skills_found) * 2)

    if word_count >= 500:
        score += 15
    elif word_count >= 300:
        score += 10
    elif word_count >= 150:
        score += 5

    score += min(20, len(sections_found) * 3)

    if contact_info.email:
        score += 3
    if contact_info.phone:
        score += 3
    if contact_info.linkedin:
        score += 2
    if contact_info.github:
        score += 2

    score += min(10, len(action_verbs))

    qty_matches = re.findall(
        r"\b\d+%|\b\d+x\b|\$\d+|\b\d+\s*(years|months|people|users|projects|clients|teams)\b",
        resume_text,
    )
    score += min(10, len(qty_matches) * 2)

    if any(deg in resume_text.lower() for deg in EDUCATION_DEGREES):
        score += 5

    return min(99, score)


# ─────────────────────────────────────────
# Feedback Generation
# ─────────────────────────────────────────
def generate_verdict(ats_score: int, match_score: int, job_description: str) -> str:
    if job_description:
        if match_score >= 75 and ats_score >= 70:
            return "Excellent candidate — strong ATS score and high JD match."
        elif match_score >= 50 and ats_score >= 50:
            return "Good candidate — meets many requirements but has some gaps."
        elif ats_score >= 60:
            return "Decent resume but low job description match — consider other roles."
        else:
            return "Resume needs significant improvement for this role."
    else:
        if ats_score >= 80:
            return "Excellent resume — well structured and keyword rich."
        elif ats_score >= 60:
            return "Good resume — minor improvements needed."
        elif ats_score >= 40:
            return "Average resume — needs more keywords and detail."
        else:
            return "Weak resume — significant improvements required."


def generate_strengths(
    skills_found: list[str],
    word_count: int,
    resume_text: str,
    match_score: int,
    action_verbs: list[str],
    contact_info: ContactInfo,
    sections_found: list[str],
) -> list[str]:
    strengths = []
    if len(skills_found) >= 10:
        strengths.append(f"Excellent technical breadth — {len(skills_found)} relevant skills detected.")
    elif len(skills_found) >= 5:
        strengths.append(f"Good skill set with {len(skills_found)} relevant keywords found.")
    if word_count >= 500:
        strengths.append("Resume has strong detail and length — ideal for ATS parsing.")
    if len(action_verbs) >= 5:
        strengths.append(f"Uses {len(action_verbs)} strong action verbs showing real impact.")
    if contact_info.github:
        strengths.append("GitHub profile included — shows practical coding experience.")
    if contact_info.linkedin:
        strengths.append("LinkedIn profile present — adds professional credibility.")
    if re.search(r"\b\d+%|\b\d+x\b|\$\d+", resume_text):
        strengths.append("Quantified achievements found — ATS systems rank these highly.")
    if len(sections_found) >= 5:
        strengths.append("Well-structured resume with all key sections present.")
    if match_score >= 70:
        strengths.append("Strong alignment with job description requirements.")
    if not strengths:
        strengths.append("Resume has a basic structure — needs improvement.")
    return strengths


def generate_weaknesses(
    skills_found: list[str],
    word_count: int,
    resume_text: str,
    missing_requirements: list[str],
    action_verbs: list[str],
    contact_info: ContactInfo,
    sections_missing: list[str],
) -> list[str]:
    weaknesses = []
    if len(skills_found) < 4:
        weaknesses.append("Very few technical keywords — ATS will rank this low.")
    if word_count < 250:
        weaknesses.append("Resume too short — add more detail about experience and projects.")
    if not re.search(r"\b\d+%|\b\d+x\b|\$\d+", resume_text):
        weaknesses.append("No quantified achievements — add numbers and impact metrics.")
    if len(action_verbs) < 3:
        weaknesses.append("Weak action verbs — use words like 'Led', 'Built', 'Optimized'.")
    if not contact_info.github:
        weaknesses.append("No GitHub link — add it to showcase your projects.")
    if not contact_info.linkedin:
        weaknesses.append("No LinkedIn profile — important for professional visibility.")
    critical = ["experience", "skills", "education"]
    missing_critical = [s for s in critical if s.title() in sections_missing]
    if missing_critical:
        weaknesses.append(f"Missing critical sections: {', '.join(missing_critical)}.")
    if len(missing_requirements) > 5:
        weaknesses.append("Missing several key job requirements — resume needs tailoring.")
    if not weaknesses:
        weaknesses.append("Resume is solid — minor tweaks can push it to the next level.")
    return weaknesses


def generate_suggestions(
    missing_requirements: list[str],
    missing_keywords: list[str],
    word_count: int,
    resume_text: str,
    contact_info: ContactInfo,
    sections_missing: list[str],
    skill_breakdown: SkillBreakdown,
) -> list[str]:
    suggestions = []

    if missing_requirements:
        suggestions.append(
            f"Add these JD-specific keywords: {', '.join(missing_requirements[:4])}."
        )
    if not contact_info.github:
        suggestions.append("Add your GitHub URL — it significantly boosts technical credibility.")
    if not contact_info.linkedin:
        suggestions.append("Add your LinkedIn URL — recruiters always check it.")
    if word_count < 400:
        suggestions.append("Expand resume to 400+ words — add project details and achievements.")
    if not re.search(r"\b\d+%|\b\d+x\b|\$\d+", resume_text):
        suggestions.append("Quantify impact: e.g. 'Reduced load time by 40%', 'Led team of 5'.")
    if not skill_breakdown.testing:
        suggestions.append("Add testing skills (pytest, Jest, TDD) — highly valued by employers.")
    if not skill_breakdown.devops_cloud:
        suggestions.append("Add cloud/DevOps skills (Docker, AWS) — essential for modern roles.")
    if "Projects" in sections_missing:
        suggestions.append("Add a Projects section with 2-3 personal or academic projects.")
    if missing_keywords:
        suggestions.append(
            f"General ATS keywords to add: {', '.join(missing_keywords[:3])}."
        )
    suggestions.append("Tailor your resume for each job — match keywords from the JD directly.")

    return suggestions[:7]


# ─────────────────────────────────────────
# Core Analysis
# ─────────────────────────────────────────
def analyze_resume_local(resume_text: str, job_description: str = "") -> ResumeAnalysis:
    word_count = len(re.findall(r"\w+", resume_text))

    contact_info = extract_contact_info(resume_text)
    experience_level = detect_experience_level(resume_text)
    sections_found, sections_missing = detect_sections(resume_text)
    action_verbs = detect_action_verbs(resume_text)
    skill_breakdown = get_skill_breakdown(resume_text)
    skills_found = find_keywords_in_text(resume_text, ALL_KEYWORDS)
    missing_keywords = [k for k in ALL_KEYWORDS if k not in skills_found][:10]
    keyword_density = calculate_keyword_density(resume_text, skills_found)

    if job_description:
        jd_spacy_kw = extract_keywords_with_spacy(job_description)
        jd_bank_kw = find_keywords_in_text(job_description, ALL_KEYWORDS)
        all_jd_keywords = list(set(jd_spacy_kw + jd_bank_kw))
    else:
        all_jd_keywords = ALL_KEYWORDS

    matched_requirements = find_keywords_in_text(resume_text, all_jd_keywords)
    missing_requirements = [k for k in all_jd_keywords if k not in matched_requirements][:12]

    ats_score = calculate_ats_score(
        resume_text, skills_found, word_count,
        sections_found, action_verbs, contact_info
    )
    match_score = calculate_similarity_score(resume_text, job_description) if job_description else 0

    strengths = generate_strengths(
        skills_found, word_count, resume_text,
        match_score, action_verbs, contact_info, sections_found
    )
    weaknesses = generate_weaknesses(
        skills_found, word_count, resume_text,
        missing_requirements, action_verbs, contact_info, sections_missing
    )
    suggestions = generate_suggestions(
        missing_requirements, missing_keywords, word_count,
        resume_text, contact_info, sections_missing, skill_breakdown
    )
    verdict = generate_verdict(ats_score, match_score, job_description)

    return ResumeAnalysis(
        ats_score=ats_score,
        match_score=match_score,
        experience_level=experience_level,
        contact_info=contact_info,
        skill_breakdown=skill_breakdown,
        skills_found=skills_found,
        missing_keywords=missing_keywords,
        matched_requirements=matched_requirements[:15],
        missing_requirements=missing_requirements,
        sections_found=sections_found,
        sections_missing=sections_missing,
        action_verbs_used=action_verbs,
        keyword_density=keyword_density,
        strengths=strengths,
        weaknesses=weaknesses,
        suggestions=suggestions,
        overall_verdict=verdict,
    )


# ─────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────
@app.post("/analyze")
async def analyze_resume(
    file: UploadFile = File(...),
    job_description: str = Form(default="")
):
    try:
        contents = await file.read()
        resume_text = extract_text_from_file(contents, file.filename)
        result = analyze_resume_local(resume_text, job_description)
        return result.model_dump()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


async def analyze_single(file: UploadFile, job_description: str) -> dict:
    try:
        contents = await file.read()
        resume_text = extract_text_from_file(contents, file.filename)
        result = analyze_resume_local(resume_text, job_description)
        skill_gap = result.missing_requirements if job_description else result.missing_keywords
        return {
            "filename": file.filename,
            "ats_score": result.ats_score,
            "match_score": result.match_score,
            "experience_level": result.experience_level,
            "skills_found": result.skills_found,
            "skill_breakdown": result.skill_breakdown.model_dump(),
            "matched_requirements": result.matched_requirements,
            "missing_requirements": result.missing_requirements,
            "skill_gap": skill_gap,
            "action_verbs_used": result.action_verbs_used,
            "sections_found": result.sections_found,
            "suggestions": result.suggestions,
            "overall_verdict": result.overall_verdict,
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as exc:
        return {
            "filename": file.filename,
            "ats_score": 0,
            "match_score": 0,
            "experience_level": "Unknown",
            "skills_found": [],
            "skill_breakdown": {},
            "matched_requirements": [],
            "missing_requirements": [],
            "skill_gap": [],
            "action_verbs_used": [],
            "sections_found": [],
            "suggestions": [],
            "overall_verdict": "Analysis failed",
            "status": f"failed: {str(exc)}"
        }


@app.post("/analyze-bulk")
async def analyze_bulk(
    files: list[UploadFile] = File(...),
    job_description: str = Form(default="")
):
    if len(files) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 resumes allowed")

    tasks = [analyze_single(f, job_description) for f in files]
    results = await asyncio.gather(*tasks)

    sorted_results = sorted(
        results,
        key=lambda x: (x["match_score"], x["ats_score"]),
        reverse=True,
    )

    ranked = [{"rank": i + 1, **r} for i, r in enumerate(sorted_results)]
    return {"total": len(ranked), "candidates": ranked}


@app.get("/models")
async def list_models():
    return {"message": "Running fully local — no API keys needed!"}
