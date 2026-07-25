from __future__ import annotations

import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./data/test-hiremind.db"

from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.database import Base, SessionLocal, engine
from app.entities import (
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
from app.main import app


client = TestClient(app)


def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def create_job() -> str:
    response = client.post(
        "/api/jobs?actor=test-hr",
        json={
            "title": "高级 Python 后端工程师",
            "department": "研发部",
            "location": "深圳",
            "description": "负责 AI 招聘产品后端服务",
            "must_have": ["Python", "FastAPI", "PostgreSQL", "Docker"],
            "nice_to_have": ["LLM", "Redis"],
            "keywords": ["后端", "API", "AI"],
            "min_years": 3,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def resume_bytes(name: str = "林知远") -> bytes:
    return (
        f"""{name}
邮箱: {name.lower()}@example.com
电话: 13800138000
现居: 深圳
6 年后端开发经验
华中科技大学 本科
技能: Python, FastAPI, PostgreSQL, Redis, Docker, LLM
主导高并发 API 服务重构，负责推荐系统和 AI 应用平台建设。
"""
    ).encode("utf-8")


def test_job_batch_analysis_decision_and_audit():
    reset_database()
    job_id = create_job()
    files = [
        ("files", (f"candidate-{index}.txt", resume_bytes(f"候选人{index}"), "text/plain"))
        for index in range(20)
    ]
    response = client.post(
        "/api/upload-batches",
        data={"job_id": job_id, "actor": "test-hr"},
        files=files,
    )
    assert response.status_code == 202, response.text
    batch = response.json()
    assert batch["total_files"] == 20

    candidates_response = client.get(
        f"/api/candidates?job_id={job_id}&limit=200"
    )
    assert candidates_response.status_code == 200
    candidates = candidates_response.json()["items"]
    assert len(candidates) == 20
    assert any(row["report"] for row in candidates)

    application_id = next(
        row["application_id"] for row in candidates if row["report"]
    )
    decision = client.patch(
        f"/api/applications/{application_id}/decision",
        json={
            "decision": "interview",
            "note": "技术栈匹配，安排一面",
            "actor": "test-hr",
        },
    )
    assert decision.status_code == 200
    assert decision.json()["stage"] == "interview"

    events = client.get(
        f"/api/audit-events?entity_id={application_id}"
    ).json()
    assert any(row["action"] == "application.decision_changed" for row in events)


def test_exact_file_duplicate_is_flagged():
    reset_database()
    job_id = create_job()
    first = client.post(
        "/api/upload-batches",
        data={"job_id": job_id, "actor": "test-hr"},
        files={"files": ("resume.txt", resume_bytes(), "text/plain")},
    )
    assert first.status_code == 202
    second = client.post(
        "/api/upload-batches",
        data={"job_id": job_id, "actor": "test-hr"},
        files={"files": ("resume-copy.txt", resume_bytes(), "text/plain")},
    )
    assert second.status_code == 202
    assert second.json()["duplicate_files"] == 1
    rows = client.get(f"/api/candidates?job_id={job_id}&limit=200").json()["items"]
    assert any(row["duplicate"] and row["duplicate"]["match_type"] == "file_hash" for row in rows)


def test_rejects_more_than_200_files():
    reset_database()
    job_id = create_job()
    files = [
        ("files", (f"{index}.txt", b"resume", "text/plain"))
        for index in range(201)
    ]
    response = client.post(
        "/api/upload-batches",
        data={"job_id": job_id, "actor": "test-hr"},
        files=files,
    )
    assert response.status_code == 422
