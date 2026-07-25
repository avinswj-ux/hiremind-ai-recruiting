import { desc, eq } from "drizzle-orm";
import { getDb } from "../../../db";
import { candidates } from "../../../db/schema";
import { safeJson, type ApiCandidate } from "../../../lib/hiremind";

function serialize(row: typeof candidates.$inferSelect): ApiCandidate {
  return {
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
    skills: safeJson(row.skills, []),
    strength: row.strength,
    risk: row.risk,
    summary: row.summary,
    dimensions: safeJson(row.dimensions, []),
    provider: row.provider,
    createdAt: row.createdAt,
  };
}

export async function GET(request: Request) {
  try {
    const jobId = new URL(request.url).searchParams.get("jobId");
    if (!jobId) return Response.json({ candidates: [] });
    const rows = await getDb()
      .select()
      .from(candidates)
      .where(eq(candidates.jobId, jobId))
      .orderBy(desc(candidates.score), desc(candidates.createdAt));
    return Response.json({ candidates: rows.map(serialize) });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "候选人读取失败" }, { status: 500 });
  }
}
