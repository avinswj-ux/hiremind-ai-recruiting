from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from .entities import CandidateRecord, ResumeRecord
from .models import ParsedResume


@dataclass
class DuplicateResult:
    matched_candidate_id: str
    match_type: str
    confidence: float
    evidence: dict[str, str]


def normalize_phone(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if digits.startswith("86") and len(digits) == 13:
        digits = digits[2:]
    return digits


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", "", value or "").lower()


def content_fingerprint(text: str) -> str:
    normalized = re.sub(r"\W+", "", (text or "").lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def find_exact_file_duplicate(
    session: Session, sha256: str
) -> DuplicateResult | None:
    resume = session.scalar(
        select(ResumeRecord)
        .where(ResumeRecord.file_sha256 == sha256)
        .order_by(ResumeRecord.created_at.asc())
    )
    if not resume:
        return None
    return DuplicateResult(
        matched_candidate_id=resume.candidate_id,
        match_type="file_hash",
        confidence=1.0,
        evidence={"sha256": sha256},
    )


def find_identity_duplicate(
    session: Session,
    parsed: ParsedResume,
    fingerprint: str,
    exclude_candidate_id: str,
) -> DuplicateResult | None:
    phone = normalize_phone(parsed.phone)
    email = (parsed.email or "").strip().lower()
    conditions = []
    if phone:
        conditions.append(CandidateRecord.normalized_phone == phone)
    if email:
        conditions.append(CandidateRecord.email == email)
    if conditions:
        candidate = session.scalar(
            select(CandidateRecord).where(
                CandidateRecord.id != exclude_candidate_id, or_(*conditions)
            )
        )
        if candidate:
            match_type = (
                "phone"
                if phone and candidate.normalized_phone == phone
                else "email"
            )
            return DuplicateResult(
                matched_candidate_id=candidate.id,
                match_type=match_type,
                confidence=0.99,
                evidence={
                    "phone_last4": phone[-4:] if phone else "",
                    "email_domain": email.split("@")[-1] if "@" in email else "",
                },
            )

    resume = session.scalar(
        select(ResumeRecord).where(
            ResumeRecord.candidate_id != exclude_candidate_id,
            ResumeRecord.content_fingerprint == fingerprint,
        )
    )
    if resume:
        return DuplicateResult(
            matched_candidate_id=resume.candidate_id,
            match_type="content_fingerprint",
            confidence=0.96,
            evidence={"fingerprint_prefix": fingerprint[:12]},
        )

    normalized_name = normalize_name(parsed.name)
    if normalized_name and normalized_name != "未知候选人":
        candidate = session.scalar(
            select(CandidateRecord).where(
                CandidateRecord.id != exclude_candidate_id,
                CandidateRecord.normalized_name == normalized_name,
            )
        )
        if candidate:
            return DuplicateResult(
                matched_candidate_id=candidate.id,
                match_type="name_review",
                confidence=0.65,
                evidence={"normalized_name": normalized_name},
            )
    return None
