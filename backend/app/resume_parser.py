from __future__ import annotations

import re
from pathlib import Path

from .models import ParsedResume


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            parts = []
            for page in reader.pages:
                parts.append(page.extract_text() or "")
            return "\n".join(parts)
        except Exception as exc:
            return f"[PDF 解析失败: {exc}]"
    if suffix in {".docx", ".doc"}:
        try:
            from docx import Document

            doc = Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as exc:
            return f"[DOCX 解析失败: {exc}]"
    return path.read_text(encoding="utf-8", errors="ignore")


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(?:\+?86[-\s]?)?1[3-9]\d{9}|(?:\+?852[-\s]?)?[569]\d{3}[-\s]?\d{4}")
YEAR_RE = re.compile(r"(\d+(?:\.\d+)?)\s*年|(\d+)\+?\s*years?", re.I)

SKILL_LEXICON = [
    "Python", "Java", "JavaScript", "TypeScript", "Go", "Golang", "Rust", "C++", "C#",
    "React", "Vue", "Angular", "Next.js", "Node.js", "FastAPI", "Django", "Flask",
    "Spring", "MySQL", "PostgreSQL", "MongoDB", "Redis", "Kafka", "Docker", "Kubernetes",
    "AWS", "Azure", "GCP", "Linux", "Git", "CI/CD", "机器学习", "深度学习", "LLM",
    "Prompt", "LangChain", "OpenAI", "数据分析", "SQL", "Tableau", "Power BI",
    "产品经理", "项目管理", "PMP", "Scrum", "Agile", "Figma", "UI", "UX",
    "招聘", "HR", "薪酬", "绩效", "培训", "组织发展", "沟通", "英语", "粤语", "普通话",
]


def _guess_name(lines: list[str], text: str) -> str:
    for line in lines[:8]:
        s = line.strip()
        if not s or len(s) > 20:
            continue
        if EMAIL_RE.search(s) or PHONE_RE.search(s):
            continue
        if re.search(r"简历|履历|curriculum|resume|个人|联系", s, re.I):
            continue
        if re.match(r"^[\u4e00-\u9fff·]{2,8}$", s):
            return s
        if re.match(r"^[A-Za-z][A-Za-z\s\.\-]{1,30}$", s):
            return s.strip()
    m = re.search(r"(?:姓名|Name)[:：\s]*([^\n，,|]{2,20})", text, re.I)
    if m:
        return m.group(1).strip()
    return "未知候选人"


def _years(text: str) -> float:
    years = []
    for m in YEAR_RE.finditer(text):
        val = m.group(1) or m.group(2)
        try:
            y = float(val)
            if 0 < y <= 40:
                years.append(y)
        except ValueError:
            pass
    # also count work date ranges roughly
    ranges = re.findall(r"(20\d{2})\s*[-–—至到]\s*(20\d{2}|至今|现在|present)", text, re.I)
    span = 0.0
    for a, b in ranges:
        end = 2026 if re.search(r"至|今|现|present", b, re.I) else int(b)
        start = int(a)
        if 1980 <= start <= end <= 2030:
            span = max(span, end - start)
    if years:
        return max(max(years), span)
    return span


def _education(text: str) -> list[str]:
    edu = []
    for pat in [
        r"((?:清华|北大|港大|港中文|港科大|复旦|交大|浙大|中大|南大|武大|哈工大)[^\n]{0,40})",
        r"((?:本科|硕士|博士|学士|MBA|研究生|大专)[^\n]{0,50})",
        r"((?:Bachelor|Master|Ph\.?D|University)[^\n]{0,60})",
    ]:
        for m in re.finditer(pat, text, re.I):
            s = re.sub(r"\s+", " ", m.group(1)).strip()
            if s and s not in edu:
                edu.append(s[:80])
    return edu[:6]


def _skills(text: str) -> list[str]:
    found = []
    lower = text.lower()
    for skill in SKILL_LEXICON:
        if skill.lower() in lower or skill in text:
            if skill not in found:
                found.append(skill)
    # free-form bullets after 技能
    block = re.search(r"(?:技能|Skills|专业技能)[:：]?\s*([^\n]{0,300})", text, re.I)
    if block:
        parts = re.split(r"[,，、/|；;]\s*", block.group(1))
        for p in parts:
            p = p.strip()
            if 1 < len(p) <= 20 and p not in found:
                found.append(p)
    return found[:30]


def _experience_bullets(text: str) -> list[str]:
    lines = [ln.strip("•-·* \t") for ln in text.splitlines()]
    bullets = []
    for ln in lines:
        if 12 <= len(ln) <= 120 and re.search(r"负责|主导|完成|优化|搭建|管理|设计|开发|提升|实现", ln):
            bullets.append(ln)
        if len(bullets) >= 8:
            break
    if not bullets:
        # fallback: non-empty medium lines
        for ln in lines:
            if 20 <= len(ln) <= 100:
                bullets.append(ln)
            if len(bullets) >= 5:
                break
    return bullets


def parse_resume_text(text: str) -> ParsedResume:
    text = (text or "").replace("\x00", " ").strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    email_m = EMAIL_RE.search(text)
    phone_m = PHONE_RE.search(text)
    loc = ""
    lm = re.search(r"(?:现居|地点|Location|城市)[:：\s]*([^\n，,]{2,30})", text, re.I)
    if lm:
        loc = lm.group(1).strip()
    elif re.search(r"香港|Hong Kong", text, re.I):
        loc = "香港"
    elif re.search(r"深圳|上海|北京|广州|杭州", text):
        m = re.search(r"深圳|上海|北京|广州|杭州", text)
        loc = m.group(0) if m else ""

    return ParsedResume(
        name=_guess_name(lines, text),
        email=email_m.group(0) if email_m else "",
        phone=phone_m.group(0) if phone_m else "",
        location=loc,
        years_experience=round(_years(text), 1),
        education=_education(text),
        skills=_skills(text),
        experience_summary=_experience_bullets(text),
        raw_text_preview=text[:2000],
    )


def parse_resume_file(path: Path) -> ParsedResume:
    return parse_resume_text(extract_text(path))
