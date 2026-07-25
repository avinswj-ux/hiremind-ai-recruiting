from __future__ import annotations

import asyncio
import secrets
import socket
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from .ai_service import analyze
from .audit import record_event
from .config import settings
from .database import SessionLocal
from .dedup import content_fingerprint, find_identity_duplicate, normalize_name, normalize_phone
from .entities import (
    AnalysisReportRecord,
    ApplicationRecord,
    CandidateRecord,
    DuplicateMatchRecord,
    JobRecord,
    ProcessingTaskRecord,
    ResumeRecord,
    UploadBatchRecord,
)
from .file_store import path_for
from .models import Job
from .resume_parser import parse_resume_file


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def to_domain_job(row: JobRecord) -> Job:
    return Job(
        id=row.id,
        title=row.title,
        department=row.department,
        location=row.location,
        description=row.description,
        requirements=row.requirements,
        must_have=row.must_have,
        nice_to_have=row.nice_to_have,
        min_years=row.min_years,
        keywords=row.keywords,
        created_at=row.created_at.isoformat(),
        status=row.status,
    )


def refresh_batch_counts(session: Session, batch_id: str) -> UploadBatchRecord:
    batch = session.get(UploadBatchRecord, batch_id)
    if not batch:
        raise LookupError("批次不存在")
    rows = session.execute(
        select(ProcessingTaskRecord.status, func.count())
        .where(ProcessingTaskRecord.batch_id == batch_id)
        .group_by(ProcessingTaskRecord.status)
    ).all()
    counts = dict(rows)
    batch.queued_files = counts.get("queued", 0)
    batch.processing_files = counts.get("processing", 0)
    batch.completed_files = counts.get("completed", 0)
    batch.duplicate_files = counts.get("duplicate", 0)
    batch.failed_files = counts.get("failed", 0)
    finished = batch.completed_files + batch.duplicate_files + batch.failed_files
    if finished >= batch.total_files:
        batch.status = "completed_with_errors" if batch.failed_files else "completed"
        batch.completed_at = utc_now()
    elif batch.processing_files:
        batch.status = "processing"
    else:
        batch.status = "queued"
    return batch


def recover_expired_tasks(session: Session) -> int:
    expires_before = utc_now() - timedelta(seconds=settings.worker_lease_seconds)
    result = session.execute(
        update(ProcessingTaskRecord)
        .where(
            ProcessingTaskRecord.status == "processing",
            ProcessingTaskRecord.locked_at < expires_before,
        )
        .values(
            status="queued",
            locked_by="",
            locked_at=None,
            error="任务租约超时，已自动恢复",
        )
    )
    session.commit()
    return result.rowcount or 0


def claim_next_task(
    session: Session, worker_id: str, batch_id: str | None = None
) -> str | None:
    statement = (
        select(ProcessingTaskRecord)
        .where(
            ProcessingTaskRecord.status == "queued",
            ProcessingTaskRecord.available_at <= utc_now(),
        )
        .order_by(ProcessingTaskRecord.created_at.asc())
        .limit(1)
    )
    if batch_id:
        statement = statement.where(ProcessingTaskRecord.batch_id == batch_id)
    if session.bind and session.bind.dialect.name == "postgresql":
        statement = statement.with_for_update(skip_locked=True)
    task = session.scalar(statement)
    if not task:
        return None
    task.status = "processing"
    task.locked_by = worker_id
    task.locked_at = utc_now()
    task.started_at = task.started_at or utc_now()
    task.attempts += 1
    refresh_batch_counts(session, task.batch_id)
    session.commit()
    return task.id


async def process_task(task_id: str, worker_id: str) -> None:
    session = SessionLocal()
    try:
        task = session.get(ProcessingTaskRecord, task_id)
        if not task or task.status != "processing" or task.locked_by != worker_id:
            return
        resume = session.get(ResumeRecord, task.resume_id)
        application = session.get(ApplicationRecord, task.application_id)
        if not resume or not application:
            raise LookupError("任务关联记录不完整")
        candidate = session.get(CandidateRecord, application.candidate_id)
        job = session.get(JobRecord, application.job_id)
        if not candidate or not job:
            raise LookupError("候选人或岗位不存在")

        resume.parse_status = "processing"
        session.commit()
        parsed = await asyncio.to_thread(parse_resume_file, path_for(resume.storage_key))
        fingerprint = content_fingerprint(parsed.raw_text_preview)

        candidate.name = parsed.name
        candidate.normalized_name = normalize_name(parsed.name)
        candidate.email = parsed.email.lower()
        candidate.normalized_phone = normalize_phone(parsed.phone)
        candidate.location = parsed.location
        candidate.years_experience = parsed.years_experience
        candidate.education = parsed.education
        candidate.skills = parsed.skills
        candidate.experience_summary = parsed.experience_summary
        resume.raw_text_preview = parsed.raw_text_preview
        resume.content_fingerprint = fingerprint

        duplicate = find_identity_duplicate(
            session, parsed, fingerprint, candidate.id
        )
        if duplicate:
            candidate.duplicate_of_id = duplicate.matched_candidate_id
            candidate.duplicate_confidence = duplicate.confidence
            session.add(
                DuplicateMatchRecord(
                    id=f"dup_{secrets.token_hex(10)}",
                    candidate_id=candidate.id,
                    matched_candidate_id=duplicate.matched_candidate_id,
                    match_type=duplicate.match_type,
                    confidence=duplicate.confidence,
                    evidence=duplicate.evidence,
                )
            )

        report = await analyze(to_domain_job(job), parsed)
        session.execute(
            update(AnalysisReportRecord)
            .where(AnalysisReportRecord.application_id == application.id)
            .values(is_current=False)
        )
        session.add(
            AnalysisReportRecord(
                id=f"report_{secrets.token_hex(10)}",
                application_id=application.id,
                task_id=task.id,
                match_score=report.match_score,
                recommendation=report.recommendation,
                summary=report.summary,
                breakdown=report.breakdown.model_dump(),
                strengths=report.strengths,
                risks=report.risks,
                reasons=report.reasons,
                missing_skills=report.missing_skills,
                interview_focus=report.interview_focus,
                provider=report.provider,
                model_version=settings.deepseek_model if settings.deepseek_api_key else "rules-v1",
            )
        )
        resume.parse_status = "completed"
        candidate.status = "duplicate_review" if duplicate else "ready"
        task.status = "completed"
        task.completed_at = utc_now()
        task.locked_by = ""
        task.locked_at = None
        record_event(
            session,
            actor="ai-worker",
            action="analysis.completed",
            entity_type="application",
            entity_id=application.id,
            after={
                "score": report.match_score,
                "recommendation": report.recommendation,
                "duplicate": bool(duplicate),
            },
            metadata={
                "task_id": task.id,
                "provider": report.provider,
                "attempt": task.attempts,
            },
        )
        refresh_batch_counts(session, task.batch_id)
        session.commit()
    except Exception as exc:
        session.rollback()
        task = session.get(ProcessingTaskRecord, task_id)
        if task:
            task.error = str(exc)[:2_000]
            task.locked_by = ""
            task.locked_at = None
            if task.attempts < task.max_attempts:
                task.status = "queued"
                task.available_at = utc_now() + timedelta(seconds=2 ** task.attempts)
            else:
                task.status = "failed"
                task.completed_at = utc_now()
                resume = session.get(ResumeRecord, task.resume_id)
                if resume:
                    resume.parse_status = "failed"
                    resume.parse_error = task.error
            record_event(
                session,
                actor="ai-worker",
                action="analysis.failed",
                entity_type="task",
                entity_id=task.id,
                after={"status": task.status, "error": task.error},
                metadata={"attempt": task.attempts},
            )
            refresh_batch_counts(session, task.batch_id)
            session.commit()
    finally:
        session.close()


async def process_batch(batch_id: str, concurrency: int = 6) -> None:
    # SQLite is the zero-setup development fallback and only permits one writer.
    # Production PostgreSQL keeps the requested parallelism.
    with SessionLocal() as probe:
        if probe.bind and probe.bind.dialect.name == "sqlite":
            concurrency = 1
    worker_prefix = f"{socket.gethostname()}-{secrets.token_hex(4)}"
    semaphore = asyncio.Semaphore(concurrency)

    async def run_claimed(task_id: str, worker_id: str):
        async with semaphore:
            await process_task(task_id, worker_id)

    while True:
        claimed: list[tuple[str, str]] = []
        with SessionLocal() as session:
            recover_expired_tasks(session)
            for index in range(concurrency):
                worker_id = f"{worker_prefix}-{index}"
                task_id = claim_next_task(session, worker_id, batch_id=batch_id)
                if task_id:
                    claimed.append((task_id, worker_id))
                else:
                    break
        if not claimed:
            return
        await asyncio.gather(*(run_claimed(*item) for item in claimed))


async def worker_loop(poll_seconds: float = 1.0) -> None:
    worker_id = f"{socket.gethostname()}-{secrets.token_hex(5)}"
    while True:
        with SessionLocal() as session:
            recover_expired_tasks(session)
            task_id = claim_next_task(session, worker_id)
        if task_id:
            await process_task(task_id, worker_id)
        else:
            await asyncio.sleep(poll_seconds)
