from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class JobRecord(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(160), index=True)
    department: Mapped[str] = mapped_column(String(100), default="")
    location: Mapped[str] = mapped_column(String(120), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    requirements: Mapped[list[str]] = mapped_column(JSON, default=list)
    must_have: Mapped[list[str]] = mapped_column(JSON, default=list)
    nice_to_have: Mapped[list[str]] = mapped_column(JSON, default=list)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list)
    min_years: Mapped[float] = mapped_column(Float, default=0)
    scoring_weights: Mapped[dict[str, float]] = mapped_column(
        JSON,
        default=lambda: {
            "skill_match": 0.45,
            "experience_match": 0.25,
            "education_match": 0.15,
            "keyword_coverage": 0.15,
        },
    )
    reject_threshold: Mapped[float] = mapped_column(Float, default=45)
    recommend_threshold: Mapped[float] = mapped_column(Float, default=75)
    status: Mapped[str] = mapped_column(String(24), default="open", index=True)
    created_by: Mapped[str] = mapped_column(String(80), default="hr")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )


class UploadBatchRecord(Base):
    __tablename__ = "upload_batches"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    total_files: Mapped[int] = mapped_column(Integer, default=0)
    queued_files: Mapped[int] = mapped_column(Integer, default=0)
    processing_files: Mapped[int] = mapped_column(Integer, default=0)
    completed_files: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_files: Mapped[int] = mapped_column(Integer, default=0)
    failed_files: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    created_by: Mapped[str] = mapped_column(String(80), default="hr")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CandidateRecord(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), default="待解析", index=True)
    normalized_name: Mapped[str] = mapped_column(String(120), default="", index=True)
    email: Mapped[str] = mapped_column(String(180), default="", index=True)
    normalized_phone: Mapped[str] = mapped_column(String(32), default="", index=True)
    location: Mapped[str] = mapped_column(String(100), default="")
    years_experience: Mapped[float] = mapped_column(Float, default=0)
    education: Mapped[list[str]] = mapped_column(JSON, default=list)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    experience_summary: Mapped[list[str]] = mapped_column(JSON, default=list)
    duplicate_of_id: Mapped[str | None] = mapped_column(
        ForeignKey("candidates.id"), index=True
    )
    duplicate_confidence: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(24), default="processing", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )


class ResumeRecord(Base):
    __tablename__ = "resumes"
    __table_args__ = (
        Index("ix_resumes_content_fingerprint", "content_fingerprint"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("upload_batches.id"), index=True)
    original_name: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    content_type: Mapped[str] = mapped_column(String(120), default="")
    size_bytes: Mapped[int] = mapped_column(Integer)
    file_sha256: Mapped[str] = mapped_column(String(64), index=True)
    content_fingerprint: Mapped[str] = mapped_column(String(64), default="")
    raw_text_preview: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[int] = mapped_column(Integer, default=1)
    parse_status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    parse_error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ApplicationRecord(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("candidate_id", "job_id", name="uq_candidate_job"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"), index=True)
    resume_id: Mapped[str] = mapped_column(ForeignKey("resumes.id"))
    stage: Mapped[str] = mapped_column(String(32), default="screening", index=True)
    decision: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    decision_note: Mapped[str] = mapped_column(Text, default="")
    decided_by: Mapped[str] = mapped_column(String(80), default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now_utc, onupdate=now_utc
    )


class AnalysisReportRecord(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id"), index=True
    )
    task_id: Mapped[str] = mapped_column(ForeignKey("processing_tasks.id"))
    match_score: Mapped[float] = mapped_column(Float, index=True)
    recommendation: Mapped[str] = mapped_column(String(32), index=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    strengths: Mapped[list[str]] = mapped_column(JSON, default=list)
    risks: Mapped[list[str]] = mapped_column(JSON, default=list)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    missing_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    interview_focus: Mapped[list[str]] = mapped_column(JSON, default=list)
    provider: Mapped[str] = mapped_column(String(60), default="rules")
    model_version: Mapped[str] = mapped_column(String(100), default="rules-v1")
    scoring_version: Mapped[str] = mapped_column(String(40), default="v1")
    prompt_version: Mapped[str] = mapped_column(String(40), default="v1")
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ProcessingTaskRecord(Base):
    __tablename__ = "processing_tasks"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    batch_id: Mapped[str] = mapped_column(ForeignKey("upload_batches.id"), index=True)
    resume_id: Mapped[str | None] = mapped_column(
        ForeignKey("resumes.id"), index=True, nullable=True
    )
    application_id: Mapped[str | None] = mapped_column(
        ForeignKey("applications.id"), index=True, nullable=True
    )
    task_type: Mapped[str] = mapped_column(String(32), default="resume_pipeline")
    status: Mapped[str] = mapped_column(String(24), default="queued", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3)
    locked_by: Mapped[str] = mapped_column(String(100), default="")
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class DuplicateMatchRecord(Base):
    __tablename__ = "duplicate_matches"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"), index=True)
    matched_candidate_id: Mapped[str] = mapped_column(
        ForeignKey("candidates.id"), index=True
    )
    match_type: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    resolution: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    resolved_by: Mapped[str] = mapped_column(String(80), default="")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AuditEventRecord(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    actor: Mapped[str] = mapped_column(String(80), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[str] = mapped_column(String(40), index=True)
    before: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    after: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    request_id: Mapped[str] = mapped_column(String(60), default="", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
