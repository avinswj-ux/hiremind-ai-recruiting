from __future__ import annotations

import secrets
import shutil
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .ai_service import analyze, notify_feishu
from .config import UPLOAD_DIR, settings
from .models import (
    Candidate,
    Decision,
    DecisionUpdate,
    Job,
    JobCreate,
    utc_now,
)
from .resume_parser import parse_resume_file
from . import storage

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


def _seed_if_empty() -> None:
    store = storage.load_store()
    if store.jobs:
        return

    def mut(s):
        job = Job(
            id=_id("job"),
            title="高级 Python 后端工程师",
            department="研发部",
            location="香港 / 深圳",
            description="负责 AI 产品后端与数据服务，参与招聘助手等业务系统建设。",
            requirements=[
                "3 年以上 Python 后端经验",
                "熟悉 FastAPI / Django / Flask 之一",
                "熟悉 PostgreSQL 或 MySQL",
                "了解 Docker 与基本云服务",
            ],
            must_have=["Python", "FastAPI", "SQL", "Docker"],
            nice_to_have=["LLM", "Redis", "Kubernetes", "React"],
            min_years=3,
            keywords=["后端", "API", "微服务", "AI"],
            created_at=utc_now(),
            status="open",
        )
        s.jobs.append(job)
        return job

    storage.with_store(mut)


@app.on_event("startup")
def on_startup():
    _seed_if_empty()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "llm": bool(settings.deepseek_api_key),
        "feishu": bool(settings.feishu_webhook_url),
        "storage": "json-file",
    }


@app.get("/api/stats")
def stats():
    return storage.compute_stats()


# ── Jobs ──────────────────────────────────────────────

@app.get("/api/jobs")
def list_jobs():
    return storage.list_jobs()


@app.post("/api/jobs", status_code=201)
def create_job(body: JobCreate):
    job = Job(id=_id("job"), created_at=utc_now(), status="open", **body.model_dump())

    def mut(s):
        s.jobs.append(job)
        return job

    return storage.with_store(mut)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "岗位不存在")
    return job


# ── Candidates ────────────────────────────────────────

@app.get("/api/candidates")
def list_candidates(job_id: Optional[str] = None):
    return storage.list_candidates(job_id)


@app.get("/api/candidates/{candidate_id}")
def get_candidate(candidate_id: str):
    c = storage.get_candidate(candidate_id)
    if not c:
        raise HTTPException(404, "候选人不存在")
    return c


@app.post("/api/candidates/upload", status_code=201)
async def upload_resume(
    job_id: str = Form(...),
    file: UploadFile = File(...),
):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "岗位不存在")

    original = file.filename or "resume.txt"
    suffix = Path(original).suffix.lower() or ".txt"
    if suffix not in {".pdf", ".docx", ".doc", ".txt"}:
        raise HTTPException(422, "仅支持 PDF / DOCX / TXT")

    cand_id = _id("cand")
    dest = UPLOAD_DIR / f"{cand_id}{suffix}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    candidate = Candidate(
        id=cand_id,
        job_id=job_id,
        filename=dest.name,
        original_name=original,
        uploaded_at=utc_now(),
        status="parsing",
    )

    def mut_add(s):
        s.candidates.append(candidate)
        return candidate

    storage.with_store(mut_add)

    try:
        parsed = parse_resume_file(dest)
        report = await analyze(job, parsed)

        def mut_done(s):
            for i, c in enumerate(s.candidates):
                if c.id == cand_id:
                    c.status = "parsed"
                    c.parsed = parsed
                    c.report = report
                    s.candidates[i] = c
                    return c
            return None

        done = storage.with_store(mut_done)
        await notify_feishu(
            "新简历初筛完成",
            f"{parsed.name} · {job.title} · {report.match_score} 分 · {report.recommendation}",
        )
        return done
    except Exception as exc:
        def mut_fail(s):
            for i, c in enumerate(s.candidates):
                if c.id == cand_id:
                    c.status = "failed"
                    c.error = str(exc)
                    s.candidates[i] = c
                    return c
            return None

        storage.with_store(mut_fail)
        raise HTTPException(500, f"解析失败: {exc}")


@app.post("/api/candidates/{candidate_id}/reanalyze")
async def reanalyze(candidate_id: str):
    c = storage.get_candidate(candidate_id)
    if not c:
        raise HTTPException(404, "候选人不存在")
    job = storage.get_job(c.job_id)
    if not job:
        raise HTTPException(404, "岗位不存在")
    path = UPLOAD_DIR / c.filename
    if not path.exists():
        raise HTTPException(404, "简历文件丢失")
    parsed = parse_resume_file(path)
    report = await analyze(job, parsed)

    def mut(s):
        for i, row in enumerate(s.candidates):
            if row.id == candidate_id:
                row.parsed = parsed
                row.report = report
                row.status = "parsed"
                row.error = ""
                s.candidates[i] = row
                return row
        return None

    return storage.with_store(mut)


@app.patch("/api/candidates/{candidate_id}/decision")
def decide(candidate_id: str, body: DecisionUpdate):
    def mut(s):
        for i, c in enumerate(s.candidates):
            if c.id == candidate_id:
                c.decision = body.decision
                c.decision_note = body.note
                c.decided_by = body.decided_by or "hr"
                c.decided_at = utc_now()
                s.candidates[i] = c
                return c
        return None

    updated = storage.with_store(mut)
    if not updated:
        raise HTTPException(404, "候选人不存在")
    return updated


@app.delete("/api/candidates/{candidate_id}")
def delete_candidate(candidate_id: str):
    def mut(s):
        before = len(s.candidates)
        target = next((c for c in s.candidates if c.id == candidate_id), None)
        s.candidates = [c for c in s.candidates if c.id != candidate_id]
        return target if len(s.candidates) < before else None

    removed = storage.with_store(mut)
    if not removed:
        raise HTTPException(404, "候选人不存在")
    path = UPLOAD_DIR / removed.filename
    if path.exists():
        path.unlink(missing_ok=True)
    return {"deleted": True, "id": candidate_id}
