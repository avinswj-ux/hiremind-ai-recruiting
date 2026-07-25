from __future__ import annotations

import json
import re
from typing import Optional

import httpx

from .config import settings
from .models import AnalysisReport, Job, ParsedResume, ScoreBreakdown
from .scoring import score_candidate


async def enhance_with_llm(
    job: Job,
    parsed: ParsedResume,
    base: AnalysisReport,
) -> AnalysisReport:
    """Optional DeepSeek polish. Falls back to rule-based report."""
    if not settings.deepseek_api_key:
        return base

    system = (
        "你是资深 HR 招聘顾问。根据岗位与候选人解析结果，输出严格 JSON，"
        "不要 markdown。字段：summary, recommendation(strong_yes|yes|maybe|no), "
        "strengths[], risks[], reasons[], interview_focus[], missing_skills[]。"
        "中文简体，客观、可执行。"
    )
    user = {
        "job": {
            "title": job.title,
            "requirements": job.requirements,
            "must_have": job.must_have,
            "nice_to_have": job.nice_to_have,
            "min_years": job.min_years,
        },
        "candidate": parsed.model_dump(),
        "rule_score": base.model_dump(),
    }
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{settings.deepseek_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.deepseek_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.deepseek_model,
                    "temperature": 0.3,
                    "max_tokens": 800,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(user, ensure_ascii=False)},
                    ],
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            data = _parse_json_blob(content)
            if not data:
                return base
            return AnalysisReport(
                summary=data.get("summary") or base.summary,
                recommendation=data.get("recommendation") or base.recommendation,
                match_score=base.match_score,
                breakdown=base.breakdown,
                strengths=data.get("strengths") or base.strengths,
                risks=data.get("risks") or base.risks,
                reasons=data.get("reasons") or base.reasons,
                missing_skills=data.get("missing_skills") or base.missing_skills,
                interview_focus=data.get("interview_focus") or base.interview_focus,
                provider="deepseek+rules",
            )
    except Exception:
        return base


def _parse_json_blob(text: str) -> Optional[dict]:
    text = (text or "").strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


async def analyze(job: Job, parsed: ParsedResume) -> AnalysisReport:
    base = score_candidate(job, parsed)
    return await enhance_with_llm(job, parsed, base)


async def notify_feishu(title: str, text: str) -> bool:
    """Stub for later Feishu integration."""
    url = settings.feishu_webhook_url
    if not url:
        return False
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                url,
                json={
                    "msg_type": "text",
                    "content": {"text": f"{title}\n{text}"},
                },
            )
        return True
    except Exception:
        return False
