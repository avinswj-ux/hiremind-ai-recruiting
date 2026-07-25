from __future__ import annotations

import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, func, select, update
from sqlalchemy.orm import Session

from .audit import record_event
from .config import settings
from .database import create_schema, get_session
from .dedup import find_exact_file_duplicate
from .entities import (
    AnalysisReportRecord,
    ApplicationRecord,
    AuditEventRecord,
    CandidateRecord,
    DuplicateMatchRecord,
    JobRecord,
    ProcessingTaskRecord,
    ResumeRecord,
    UploadBatchRecord,
)
from .file_store import ALLOWED_SUFFIXES, safe_filename, save_upload
from .pipeline import process_batch, refresh_batch_counts
from .schemas import (
    DecisionRequest,
    DuplicateResolutionRequest,
    JobCreateRequest,
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    create_schema()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.1.0",
    description="可追溯的 AI 招聘初筛、批量解析与人工决策 API",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SessionDep = Annotated[Session, Depends(get_session)]


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(10)}"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def mask_email(value: str) -> str:
    if "@" not in value:
        return ""
    name, domain = value.split("@", 1)
    return f"{name[:2]}***@{domain}"


def mask_phone(value: str) -> str:
    return f"***{value[-4:]}" if value else ""


def job_dict(job: JobRecord) -> dict:
    return {
        "id": job.id,
        "title": job.title,
        "department": job.department,
        "location": job.location,
        "description": job.description,
        "requirements": job.requirements,
        "must_have": job.must_have,
        "nice_to_have": job.nice_to_have,
        "keywords": job.keywords,
        "min_years": job.min_years,
        "scoring_weights": job.scoring_weights,
        "reject_threshold": job.reject_threshold,
        "recommend_threshold": job.recommend_threshold,
        "status": job.status,
        "created_by": job.created_by,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def batch_dict(batch: UploadBatchRecord) -> dict:
    finished = batch.completed_files + batch.duplicate_files + batch.failed_files
    progress = round(finished / batch.total_files * 100, 1) if batch.total_files else 0
    return {
        "id": batch.id,
        "job_id": batch.job_id,
        "total_files": batch.total_files,
        "queued_files": batch.queued_files,
        "processing_files": batch.processing_files,
        "completed_files": batch.completed_files,
        "duplicate_files": batch.duplicate_files,
        "failed_files": batch.failed_files,
        "status": batch.status,
        "progress": progress,
        "created_by": batch.created_by,
        "created_at": batch.created_at,
        "completed_at": batch.completed_at,
    }


@app.get("/api/health")
def health(session: SessionDep):
    session.scalar(select(func.count()).select_from(JobRecord))
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": "1.1.0",
        "llm": "deepseek" if settings.deepseek_api_key else "rules-fallback",
        "database": session.bind.dialect.name if session.bind else "unknown",
        "max_batch_files": settings.max_batch_files,
    }


@app.get("/api/stats")
def stats(session: SessionDep, job_id: str | None = None):
    application_query = select(ApplicationRecord)
    if job_id:
        application_query = application_query.where(ApplicationRecord.job_id == job_id)
    applications = list(session.scalars(application_query))
    app_ids = [row.id for row in applications]
    reports = (
        list(
            session.scalars(
                select(AnalysisReportRecord).where(
                    AnalysisReportRecord.application_id.in_(app_ids),
                    AnalysisReportRecord.is_current.is_(True),
                )
            )
        )
        if app_ids
        else []
    )
    scores = [row.match_score for row in reports]
    decisions = {name: 0 for name in ("pending", "shortlist", "interview", "reject", "hold")}
    for row in applications:
        decisions[row.decision] = decisions.get(row.decision, 0) + 1
    return {
        "total_candidates": len(applications),
        "pending": decisions["pending"],
        "shortlist": decisions["shortlist"],
        "interview": decisions["interview"],
        "reject": decisions["reject"],
        "hold": decisions["hold"],
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
        "high_match": sum(score >= 75 for score in scores),
        "open_jobs": session.scalar(
            select(func.count()).select_from(JobRecord).where(JobRecord.status == "open")
        ),
        "active_batches": session.scalar(
            select(func.count())
            .select_from(UploadBatchRecord)
            .where(UploadBatchRecord.status.in_(["queued", "processing"]))
        ),
    }


@app.post("/api/jobs", status_code=201)
def create_job(
    body: JobCreateRequest,
    session: SessionDep,
    actor: str = Query(default="hr", max_length=80),
):
    job = JobRecord(
        id=new_id("job"),
        created_by=actor,
        **body.model_dump(),
    )
    session.add(job)
    record_event(
        session,
        actor=actor,
        action="job.created",
        entity_type="job",
        entity_id=job.id,
        after={"title": job.title, "status": job.status},
    )
    session.commit()
    return job_dict(job)


@app.get("/api/jobs")
def list_jobs(session: SessionDep, status: str | None = None):
    statement = select(JobRecord).order_by(desc(JobRecord.created_at))
    if status:
        statement = statement.where(JobRecord.status == status)
    return [job_dict(job) for job in session.scalars(statement)]


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str, session: SessionDep):
    job = session.get(JobRecord, job_id)
    if not job:
        raise HTTPException(404, "岗位不存在")
    return job_dict(job)


@app.post("/api/upload-batches", status_code=202)
async def create_upload_batch(
    background_tasks: BackgroundTasks,
    session: SessionDep,
    job_id: Annotated[str, Form(...)],
    actor: Annotated[str, Form()] = "hr",
    files: list[UploadFile] = File(...),
):
    if not 1 <= len(files) <= settings.max_batch_files:
        raise HTTPException(
            422, f"单批次需上传 1–{settings.max_batch_files} 份简历"
        )
    job = session.get(JobRecord, job_id)
    if not job or job.status != "open":
        raise HTTPException(404, "岗位不存在或已关闭")

    invalid = [
        file.filename or ""
        for file in files
        if Path(file.filename or "").suffix.lower() not in ALLOWED_SUFFIXES
    ]
    if invalid:
        raise HTTPException(
            422,
            {"message": "存在不支持的文件", "files": invalid[:10]},
        )

    batch = UploadBatchRecord(
        id=new_id("batch"),
        job_id=job_id,
        total_files=len(files),
        queued_files=0,
        status="queued",
        created_by=actor,
    )
    session.add(batch)
    session.flush()
    task_ids: list[str] = []

    for file in files:
        candidate = CandidateRecord(id=new_id("cand"), status="processing")
        session.add(candidate)
        session.flush()
        original_name = safe_filename(file.filename or "resume")
        suffix = Path(original_name).suffix.lower()
        resume_id = new_id("resume")
        storage_key = f"{batch.id}/{resume_id}{suffix}"
        try:
            _, size_bytes, sha256 = await save_upload(file, storage_key)
        except ValueError as exc:
            candidate.status = "failed"
            session.add(
                ProcessingTaskRecord(
                    id=new_id("task"),
                    batch_id=batch.id,
                    resume_id=None,
                    application_id=None,
                    status="failed",
                    attempts=1,
                    error=str(exc),
                    completed_at=now_utc(),
                )
            )
            record_event(
                session,
                actor=actor,
                action="resume.upload_failed",
                entity_type="candidate",
                entity_id=candidate.id,
                after={"filename": original_name, "error": str(exc)},
            )
            continue

        exact_duplicate = find_exact_file_duplicate(session, sha256)
        resume = ResumeRecord(
            id=resume_id,
            candidate_id=candidate.id,
            batch_id=batch.id,
            original_name=original_name,
            storage_key=storage_key,
            content_type=file.content_type or "",
            size_bytes=size_bytes,
            file_sha256=sha256,
            parse_status="duplicate" if exact_duplicate else "queued",
        )
        application = ApplicationRecord(
            id=new_id("app"),
            candidate_id=candidate.id,
            job_id=job_id,
            resume_id=resume.id,
        )
        session.add_all([resume, application])
        session.flush()
        task = ProcessingTaskRecord(
            id=new_id("task"),
            batch_id=batch.id,
            resume_id=resume.id,
            application_id=application.id,
            status="duplicate" if exact_duplicate else "queued",
            completed_at=now_utc() if exact_duplicate else None,
        )
        session.add(task)
        if exact_duplicate:
            matched = session.get(CandidateRecord, exact_duplicate.matched_candidate_id)
            if matched:
                candidate.name = matched.name
                candidate.normalized_name = matched.normalized_name
                candidate.email = matched.email
                candidate.normalized_phone = matched.normalized_phone
                candidate.location = matched.location
                candidate.years_experience = matched.years_experience
                candidate.education = matched.education
                candidate.skills = matched.skills
                candidate.experience_summary = matched.experience_summary
            candidate.status = "duplicate_review"
            candidate.duplicate_of_id = exact_duplicate.matched_candidate_id
            candidate.duplicate_confidence = exact_duplicate.confidence
            session.add(
                DuplicateMatchRecord(
                    id=new_id("dup"),
                    candidate_id=candidate.id,
                    matched_candidate_id=exact_duplicate.matched_candidate_id,
                    match_type=exact_duplicate.match_type,
                    confidence=exact_duplicate.confidence,
                    evidence=exact_duplicate.evidence,
                )
            )
        else:
            task_ids.append(task.id)
        record_event(
            session,
            actor=actor,
            action="resume.uploaded",
            entity_type="resume",
            entity_id=resume.id,
            after={
                "filename": original_name,
                "size_bytes": size_bytes,
                "batch_id": batch.id,
                "duplicate": bool(exact_duplicate),
            },
            metadata={"sha256_prefix": sha256[:12]},
        )

    session.flush()
    refresh_batch_counts(session, batch.id)
    record_event(
        session,
        actor=actor,
        action="batch.created",
        entity_type="upload_batch",
        entity_id=batch.id,
        after={
            "job_id": job_id,
            "total_files": batch.total_files,
            "queued_files": len(task_ids),
        },
    )
    session.commit()
    if task_ids:
        background_tasks.add_task(process_batch, batch.id)
    return batch_dict(batch)


@app.get("/api/upload-batches")
def list_upload_batches(
    session: SessionDep,
    job_id: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
):
    statement = select(UploadBatchRecord).order_by(desc(UploadBatchRecord.created_at))
    if job_id:
        statement = statement.where(UploadBatchRecord.job_id == job_id)
    statement = statement.limit(limit)
    return [batch_dict(row) for row in session.scalars(statement)]


@app.get("/api/upload-batches/{batch_id}")
def get_upload_batch(batch_id: str, session: SessionDep):
    batch = session.get(UploadBatchRecord, batch_id)
    if not batch:
        raise HTTPException(404, "上传批次不存在")
    refresh_batch_counts(session, batch_id)
    session.commit()
    return batch_dict(batch)


@app.post("/api/upload-batches/{batch_id}/retry")
def retry_failed_batch(
    batch_id: str,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    actor: str = Query(default="hr", max_length=80),
):
    batch = session.get(UploadBatchRecord, batch_id)
    if not batch:
        raise HTTPException(404, "上传批次不存在")
    result = session.execute(
        update(ProcessingTaskRecord)
        .where(
            ProcessingTaskRecord.batch_id == batch_id,
            ProcessingTaskRecord.status == "failed",
            ProcessingTaskRecord.resume_id.is_not(None),
        )
        .values(
            status="queued",
            attempts=0,
            error="",
            available_at=now_utc(),
            completed_at=None,
        )
    )
    count = result.rowcount or 0
    refresh_batch_counts(session, batch_id)
    record_event(
        session,
        actor=actor,
        action="batch.retry_requested",
        entity_type="upload_batch",
        entity_id=batch_id,
        after={"retried_tasks": count},
    )
    session.commit()
    if count:
        background_tasks.add_task(process_batch, batch_id)
    return {"batch_id": batch_id, "retried_tasks": count}


def candidate_payload(
    session: Session, candidate: CandidateRecord, application: ApplicationRecord
) -> dict:
    report = session.scalar(
        select(AnalysisReportRecord)
        .where(
            AnalysisReportRecord.application_id == application.id,
            AnalysisReportRecord.is_current.is_(True),
        )
        .order_by(desc(AnalysisReportRecord.created_at))
    )
    duplicate = session.scalar(
        select(DuplicateMatchRecord)
        .where(
            DuplicateMatchRecord.candidate_id == candidate.id,
            DuplicateMatchRecord.resolution == "pending",
        )
        .order_by(desc(DuplicateMatchRecord.created_at))
    )
    return {
        "id": candidate.id,
        "application_id": application.id,
        "job_id": application.job_id,
        "name": candidate.name,
        "email": mask_email(candidate.email),
        "phone": mask_phone(candidate.normalized_phone),
        "location": candidate.location,
        "years_experience": candidate.years_experience,
        "education": candidate.education,
        "skills": candidate.skills,
        "experience_summary": candidate.experience_summary,
        "status": candidate.status,
        "stage": application.stage,
        "decision": application.decision,
        "decision_note": application.decision_note,
        "duplicate": (
            {
                "id": duplicate.id,
                "matched_candidate_id": duplicate.matched_candidate_id,
                "match_type": duplicate.match_type,
                "confidence": duplicate.confidence,
                "evidence": duplicate.evidence,
            }
            if duplicate
            else None
        ),
        "report": (
            {
                "id": report.id,
                "match_score": report.match_score,
                "recommendation": report.recommendation,
                "summary": report.summary,
                "breakdown": report.breakdown,
                "strengths": report.strengths,
                "risks": report.risks,
                "reasons": report.reasons,
                "missing_skills": report.missing_skills,
                "interview_focus": report.interview_focus,
                "provider": report.provider,
                "model_version": report.model_version,
                "scoring_version": report.scoring_version,
                "created_at": report.created_at,
            }
            if report
            else None
        ),
        "created_at": candidate.created_at,
    }


@app.get("/api/candidates")
def list_candidates(
    session: SessionDep,
    job_id: str | None = None,
    decision: str | None = None,
    min_score: float | None = Query(default=None, ge=0, le=100),
    sort: str = Query(default="score_desc", pattern="^(score_desc|score_asc|newest)$"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    statement = select(ApplicationRecord)
    if job_id:
        statement = statement.where(ApplicationRecord.job_id == job_id)
    if decision:
        statement = statement.where(ApplicationRecord.decision == decision)
    applications = list(
        session.scalars(statement.order_by(desc(ApplicationRecord.created_at)))
    )
    rows = []
    for application in applications:
        candidate = session.get(CandidateRecord, application.candidate_id)
        if candidate:
            payload = candidate_payload(session, candidate, application)
            score = payload["report"]["match_score"] if payload["report"] else -1
            if min_score is None or score >= min_score:
                rows.append(payload)
    if sort.startswith("score"):
        rows.sort(
            key=lambda row: row["report"]["match_score"] if row["report"] else -1,
            reverse=sort == "score_desc",
        )
    return {
        "items": rows[offset : offset + limit],
        "total": len(rows),
        "limit": limit,
        "offset": offset,
    }


@app.get("/api/candidates/{candidate_id}")
def get_candidate(candidate_id: str, session: SessionDep, job_id: str | None = None):
    candidate = session.get(CandidateRecord, candidate_id)
    if not candidate:
        raise HTTPException(404, "候选人不存在")
    statement = select(ApplicationRecord).where(
        ApplicationRecord.candidate_id == candidate_id
    )
    if job_id:
        statement = statement.where(ApplicationRecord.job_id == job_id)
    application = session.scalar(statement.order_by(desc(ApplicationRecord.created_at)))
    if not application:
        raise HTTPException(404, "候选人没有对应的投递记录")
    return candidate_payload(session, candidate, application)


@app.patch("/api/applications/{application_id}/decision")
def decide(application_id: str, body: DecisionRequest, session: SessionDep):
    application = session.get(ApplicationRecord, application_id)
    if not application:
        raise HTTPException(404, "投递记录不存在")
    before = {
        "decision": application.decision,
        "note": application.decision_note,
        "stage": application.stage,
    }
    application.decision = body.decision
    application.decision_note = body.note
    application.decided_by = body.actor
    application.decided_at = now_utc()
    if body.decision == "interview":
        application.stage = "interview"
    elif body.decision == "reject":
        application.stage = "closed"
    elif body.decision == "hold":
        application.stage = "talent_pool"
    record_event(
        session,
        actor=body.actor,
        action="application.decision_changed",
        entity_type="application",
        entity_id=application.id,
        before=before,
        after={
            "decision": application.decision,
            "note": application.decision_note,
            "stage": application.stage,
        },
    )
    session.commit()
    return {"id": application.id, "decision": application.decision, "stage": application.stage}


@app.patch("/api/duplicates/{duplicate_id}/resolve")
def resolve_duplicate(
    duplicate_id: str, body: DuplicateResolutionRequest, session: SessionDep
):
    duplicate = session.get(DuplicateMatchRecord, duplicate_id)
    if not duplicate:
        raise HTTPException(404, "重复匹配记录不存在")
    if duplicate.resolution != "pending":
        raise HTTPException(409, "该重复记录已处理")
    duplicate.resolution = body.resolution
    duplicate.resolved_by = body.actor
    duplicate.resolved_at = now_utc()
    candidate = session.get(CandidateRecord, duplicate.candidate_id)
    if candidate and body.resolution == "keep_separate":
        candidate.duplicate_of_id = None
        candidate.duplicate_confidence = 0
        candidate.status = "ready"
    elif candidate and body.resolution == "ignore":
        candidate.status = "archived"
    record_event(
        session,
        actor=body.actor,
        action="duplicate.resolved",
        entity_type="duplicate_match",
        entity_id=duplicate.id,
        before={"resolution": "pending"},
        after={"resolution": body.resolution},
        metadata={
            "candidate_id": duplicate.candidate_id,
            "matched_candidate_id": duplicate.matched_candidate_id,
        },
    )
    session.commit()
    return {"id": duplicate.id, "resolution": duplicate.resolution}


@app.get("/api/audit-events")
def list_audit_events(
    session: SessionDep,
    entity_type: str | None = None,
    entity_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    statement = select(AuditEventRecord).order_by(desc(AuditEventRecord.created_at))
    if entity_type:
        statement = statement.where(AuditEventRecord.entity_type == entity_type)
    if entity_id:
        statement = statement.where(AuditEventRecord.entity_id == entity_id)
    events = session.scalars(statement.limit(limit))
    return [
        {
            "id": event.id,
            "actor": event.actor,
            "action": event.action,
            "entity_type": event.entity_type,
            "entity_id": event.entity_id,
            "before": event.before,
            "after": event.after,
            "metadata": event.metadata_json,
            "request_id": event.request_id,
            "created_at": event.created_at,
        }
        for event in events
    ]
