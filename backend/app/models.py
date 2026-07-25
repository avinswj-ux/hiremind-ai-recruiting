from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Decision(str, Enum):
    pending = "pending"
    shortlist = "shortlist"
    interview = "interview"
    reject = "reject"
    hold = "hold"


class JobCreate(BaseModel):
    title: str
    department: str = ""
    location: str = "香港 / 远程"
    description: str = ""
    requirements: list[str] = Field(default_factory=list)
    must_have: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    min_years: float = 0
    keywords: list[str] = Field(default_factory=list)


class Job(JobCreate):
    id: str
    created_at: str
    status: str = "open"


class ParsedResume(BaseModel):
    name: str = "未知候选人"
    email: str = ""
    phone: str = ""
    location: str = ""
    years_experience: float = 0
    education: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience_summary: list[str] = Field(default_factory=list)
    raw_text_preview: str = ""


class ScoreBreakdown(BaseModel):
    skill_match: float = 0
    experience_match: float = 0
    education_match: float = 0
    keyword_coverage: float = 0
    overall: float = 0


class AnalysisReport(BaseModel):
    summary: str = ""
    recommendation: str = ""  # strong_yes | yes | maybe | no
    match_score: float = 0
    breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    strengths: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    interview_focus: list[str] = Field(default_factory=list)
    provider: str = "rules"


class Candidate(BaseModel):
    id: str
    job_id: str
    filename: str
    original_name: str
    uploaded_at: str
    status: str = "parsed"  # uploaded | parsing | parsed | failed
    decision: Decision = Decision.pending
    decision_note: str = ""
    decided_at: Optional[str] = None
    decided_by: str = ""
    parsed: ParsedResume = Field(default_factory=ParsedResume)
    report: Optional[AnalysisReport] = None
    error: str = ""


class DecisionUpdate(BaseModel):
    decision: Decision
    note: str = ""
    decided_by: str = "hr"


class Stats(BaseModel):
    total_candidates: int = 0
    pending: int = 0
    shortlist: int = 0
    interview: int = 0
    reject: int = 0
    hold: int = 0
    avg_score: float = 0
    jobs_open: int = 0
    high_match: int = 0  # score >= 75


class Store(BaseModel):
    jobs: list[Job] = Field(default_factory=list)
    candidates: list[Candidate] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)
