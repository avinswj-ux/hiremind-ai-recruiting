from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class JobCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    department: str = Field(default="", max_length=100)
    location: str = Field(default="", max_length=120)
    description: str = Field(default="", max_length=20_000)
    requirements: list[str] = Field(default_factory=list, max_length=30)
    must_have: list[str] = Field(default_factory=list, max_length=20)
    nice_to_have: list[str] = Field(default_factory=list, max_length=20)
    keywords: list[str] = Field(default_factory=list, max_length=30)
    min_years: float = Field(default=0, ge=0, le=50)
    scoring_weights: dict[str, float] = Field(
        default_factory=lambda: {
            "skill_match": 0.45,
            "experience_match": 0.25,
            "education_match": 0.15,
            "keyword_coverage": 0.15,
        }
    )
    reject_threshold: float = Field(default=45, ge=0, le=100)
    recommend_threshold: float = Field(default=75, ge=0, le=100)

    @model_validator(mode="after")
    def validate_thresholds(self):
        if self.reject_threshold >= self.recommend_threshold:
            raise ValueError("淘汰阈值必须低于推荐阈值")
        total = sum(self.scoring_weights.values())
        if not 0.99 <= total <= 1.01:
            raise ValueError("评分权重之和必须等于 1")
        return self


class DecisionRequest(BaseModel):
    decision: Literal["shortlist", "interview", "reject", "hold", "pending"]
    note: str = Field(default="", max_length=4_000)
    actor: str = Field(default="hr", max_length=80)


class JobStatusRequest(BaseModel):
    status: Literal["open", "paused", "archived"]
    actor: str = Field(default="hr", max_length=80)


class DuplicateResolutionRequest(BaseModel):
    resolution: Literal["merge", "keep_separate", "ignore"]
    actor: str = Field(default="hr", max_length=80)


class BatchSummary(BaseModel):
    id: str
    job_id: str
    total_files: int
    queued_files: int
    processing_files: int
    completed_files: int
    duplicate_files: int
    failed_files: int
    status: str
    created_by: str
    created_at: datetime
    completed_at: datetime | None


class AuditSummary(BaseModel):
    id: str
    actor: str
    action: str
    entity_type: str
    entity_id: str
    before: dict
    after: dict
    metadata: dict
    request_id: str
    created_at: datetime
