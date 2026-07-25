from __future__ import annotations

from .models import (
    AnalysisReport,
    Job,
    ParsedResume,
    ScoreBreakdown,
)


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _coverage(needles: list[str], haystack: str, skills: list[str]) -> tuple[float, list[str], list[str]]:
    if not needles:
        return 1.0, [], []
    blob = haystack + " " + " ".join(skills)
    blob_l = blob.lower()
    hit, miss = [], []
    for n in needles:
        n = n.strip()
        if not n:
            continue
        if _norm(n) in blob_l or any(_norm(n) in _norm(sk) or _norm(sk) in _norm(n) for sk in skills):
            hit.append(n)
        else:
            miss.append(n)
    total = len(hit) + len(miss)
    return (len(hit) / total if total else 1.0), hit, miss


def score_candidate(job: Job, parsed: ParsedResume) -> AnalysisReport:
    text = parsed.raw_text_preview or ""
    must = job.must_have or job.requirements[:5]
    nice = job.nice_to_have or []
    keywords = job.keywords or []

    must_cov, must_hit, must_miss = _coverage(must, text, parsed.skills)
    nice_cov, nice_hit, nice_miss = _coverage(nice, text, parsed.skills)
    kw_cov, kw_hit, kw_miss = _coverage(keywords, text, parsed.skills)

    # skill: weight must heavily
    skill_score = round(100 * (0.75 * must_cov + 0.25 * nice_cov), 1)

    # experience
    min_y = float(job.min_years or 0)
    years = float(parsed.years_experience or 0)
    if min_y <= 0:
        exp_score = 80.0 if years > 0 else 60.0
    elif years >= min_y:
        exp_score = min(100.0, 70 + (years - min_y) * 8)
    elif years >= min_y * 0.7:
        exp_score = 55.0
    else:
        exp_score = 30.0

    # education heuristic
    edu_blob = " ".join(parsed.education).lower()
    if any(x in edu_blob for x in ["博士", "phd", "硕士", "master", "mba"]):
        edu_score = 90.0
    elif any(x in edu_blob for x in ["本科", "学士", "bachelor", "大学"]):
        edu_score = 75.0
    elif parsed.education:
        edu_score = 60.0
    else:
        edu_score = 50.0

    keyword_score = round(100 * kw_cov, 1) if keywords else skill_score

    overall = round(
        0.45 * skill_score
        + 0.25 * exp_score
        + 0.15 * edu_score
        + 0.15 * keyword_score,
        1,
    )

    strengths = []
    risks = []
    reasons = []

    if must_hit:
        strengths.append(f"硬性技能匹配：{', '.join(must_hit[:6])}")
        reasons.append(f"覆盖关键要求 {len(must_hit)}/{len(must_hit)+len(must_miss)}")
    if nice_hit:
        strengths.append(f"加分项：{', '.join(nice_hit[:5])}")
    if years and min_y and years >= min_y:
        strengths.append(f"工作年限约 {years} 年，满足 ≥{min_y} 年要求")
        reasons.append("经验年限达标")
    if parsed.education:
        strengths.append(f"教育背景：{parsed.education[0]}")

    if must_miss:
        risks.append(f"可能缺失硬性要求：{', '.join(must_miss[:6])}")
        reasons.append("硬性技能存在缺口，建议面试核实")
    if min_y and years < min_y:
        risks.append(f"年限约 {years} 年，低于岗位要求 {min_y} 年")
    if not parsed.email and not parsed.phone:
        risks.append("联系方式不完整，跟进成本高")
    if not parsed.experience_summary:
        risks.append("经历描述偏少，难以验证项目深度")
    if overall < 50:
        reasons.append("综合匹配偏低，不建议优先推进")
    elif overall >= 75:
        reasons.append("综合匹配较高，建议进入面试池")
    else:
        reasons.append("中等匹配，可人工复核后决定")

    if overall >= 80:
        rec = "strong_yes"
    elif overall >= 65:
        rec = "yes"
    elif overall >= 45:
        rec = "maybe"
    else:
        rec = "no"

    rec_label = {
        "strong_yes": "强烈推荐",
        "yes": "推荐面试",
        "maybe": "待定 / 可储备",
        "no": "暂不推荐",
    }[rec]

    summary = (
        f"{parsed.name} 与「{job.title}」综合匹配 {overall} 分（{rec_label}）。"
        f"技能 {skill_score}、经验 {exp_score}、教育 {edu_score}。"
    )

    interview_focus = []
    for m in must_miss[:3]:
        interview_focus.append(f"核实是否具备：{m}")
    if years < min_y:
        interview_focus.append("了解相关领域实际项目深度与年限口径")
    interview_focus.append("确认到岗时间、期望薪资与工作地偏好")
    if not interview_focus:
        interview_focus = ["深挖代表性项目结果与协作方式", "文化匹配与稳定性"]

    return AnalysisReport(
        summary=summary,
        recommendation=rec,
        match_score=overall,
        breakdown=ScoreBreakdown(
            skill_match=skill_score,
            experience_match=round(exp_score, 1),
            education_match=edu_score,
            keyword_coverage=keyword_score,
            overall=overall,
        ),
        strengths=strengths or ["基础信息已解析，待进一步对比"],
        risks=risks or ["暂无明显红旗，仍建议标准背调"],
        reasons=reasons,
        missing_skills=must_miss + [x for x in nice_miss if x not in must_miss][:8],
        interview_focus=interview_focus[:6],
        provider="rules",
    )
