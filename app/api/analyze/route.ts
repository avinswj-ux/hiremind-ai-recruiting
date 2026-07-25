import { and, eq } from "drizzle-orm";
import { getDb } from "../../../db";
import { auditEvents, candidates, jobs } from "../../../db/schema";
import { analyzeResume } from "../../../lib/deepseek";
import { safeJson, type ApiCandidate, type ApiJob } from "../../../lib/hiremind";
import { extractResumeText, sha256 } from "../../../lib/resume-parser";

function apiJob(row: typeof jobs.$inferSelect): ApiJob {
  return {
    id: row.id,
    title: row.title,
    department: row.department,
    location: row.location,
    minYears: row.minYears,
    mustHave: safeJson(row.mustHave, []),
    niceToHave: safeJson(row.niceToHave, []),
    status: row.status as ApiJob["status"],
    candidates: 0,
    highMatch: 0,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

export async function POST(request: Request) {
  try {
    const form = await request.formData();
    const file = form.get("file");
    const jobId = String(form.get("jobId") || "");
    if (!(file instanceof File) || !jobId) {
      return Response.json({ error: "缺少简历文件或岗位" }, { status: 400 });
    }
    if (file.size > 20 * 1024 * 1024) {
      return Response.json({ error: `${file.name} 超过 20 MB` }, { status: 413 });
    }
    const suffix = file.name.toLowerCase().split(".").pop();
    if (!["pdf", "docx", "txt"].includes(suffix || "")) {
      return Response.json({ error: `${file.name} 格式不支持` }, { status: 415 });
    }

    const db = getDb();
    const [jobRow] = await db.select().from(jobs).where(eq(jobs.id, jobId)).limit(1);
    if (!jobRow) return Response.json({ error: "岗位不存在" }, { status: 404 });
    if (jobRow.status !== "open") return Response.json({ error: "当前岗位未在招聘中" }, { status: 409 });

    const bytes = new Uint8Array(await file.arrayBuffer());
    const fileHash = await sha256(bytes);
    const [duplicate] = await db
      .select()
      .from(candidates)
      .where(and(eq(candidates.jobId, jobId), eq(candidates.fileHash, fileHash)))
      .limit(1);
    if (duplicate) {
      return Response.json({ duplicate: true, candidateId: duplicate.id, fileName: file.name });
    }

    const text = (await extractResumeText(new File([bytes], file.name, { type: file.type }))).trim();
    if (text.length < 20) return Response.json({ error: `${file.name} 未提取到足够文本` }, { status: 422 });
    const { analysis, provider } = await analyzeResume(apiJob(jobRow), text);
    const id = crypto.randomUUID();
    const status = analysis.score >= 85 ? "建议面试" : "待处理";
    const [row] = await db
      .insert(candidates)
      .values({
        id,
        jobId,
        fileName: file.name,
        fileHash,
        name: analysis.name || file.name.replace(/\.[^.]+$/, ""),
        role: analysis.role,
        company: analysis.company,
        years: analysis.years,
        city: analysis.city,
        degree: analysis.degree,
        score: analysis.score,
        status,
        skills: JSON.stringify(analysis.skills),
        strength: analysis.strength,
        risk: analysis.risk,
        summary: analysis.summary,
        dimensions: JSON.stringify(analysis.dimensions),
        provider,
        resumeExcerpt: text.slice(0, 50000),
      })
      .returning();
    await db.insert(auditEvents).values({
      action: "candidate.analyzed",
      entityType: "candidate",
      entityId: id,
      detail: JSON.stringify({ jobId, fileName: file.name, score: analysis.score, provider }),
    });
    const candidate: ApiCandidate = {
      id: row.id,
      jobId: row.jobId,
      fileName: row.fileName,
      name: row.name,
      role: row.role,
      company: row.company,
      years: row.years,
      city: row.city,
      degree: row.degree,
      score: row.score,
      status: row.status as ApiCandidate["status"],
      skills: analysis.skills,
      strength: row.strength,
      risk: row.risk,
      summary: row.summary,
      dimensions: analysis.dimensions,
      provider: row.provider,
      createdAt: row.createdAt,
    };
    return Response.json({ duplicate: false, candidate }, { status: 201 });
  } catch (error) {
    return Response.json(
      { error: error instanceof Error ? error.message : "简历分析失败" },
      { status: 500 },
    );
  }
}
