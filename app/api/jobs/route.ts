import { and, count, desc, eq, gte } from "drizzle-orm";
import { getDb } from "../../../db";
import { auditEvents, candidates, jobs } from "../../../db/schema";
import { safeJson, type ApiJob } from "../../../lib/hiremind";

function serializeJob(
  row: typeof jobs.$inferSelect,
  candidateCount = 0,
  highMatch = 0,
): ApiJob {
  return {
    id: row.id,
    title: row.title,
    department: row.department,
    location: row.location,
    minYears: row.minYears,
    mustHave: safeJson(row.mustHave, []),
    niceToHave: safeJson(row.niceToHave, []),
    status: row.status as ApiJob["status"],
    candidates: candidateCount,
    highMatch,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

export async function GET() {
  try {
    const db = getDb();
    const rows = await db.select().from(jobs).orderBy(desc(jobs.updatedAt));
    const result = await Promise.all(
      rows.map(async (job) => {
        const [all] = await db.select({ value: count() }).from(candidates).where(eq(candidates.jobId, job.id));
        const [high] = await db
          .select({ value: count() })
          .from(candidates)
          .where(and(eq(candidates.jobId, job.id), gte(candidates.score, 85)));
        return serializeJob(job, all?.value || 0, high?.value || 0);
      }),
    );
    return Response.json({ jobs: result });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "岗位读取失败" }, { status: 500 });
  }
}

export async function POST(request: Request) {
  try {
    const payload = (await request.json()) as {
      title?: string;
      department?: string;
      location?: string;
      minYears?: number;
      mustHave?: string[];
      niceToHave?: string[];
    };
    const title = payload.title?.trim();
    if (!title) return Response.json({ error: "岗位名称不能为空" }, { status: 400 });
    const db = getDb();
    const id = crypto.randomUUID();
    const [job] = await db
      .insert(jobs)
      .values({
        id,
        title,
        department: payload.department?.trim() || "",
        location: payload.location?.trim() || "",
        minYears: Math.max(0, Number(payload.minYears) || 0),
        mustHave: JSON.stringify((payload.mustHave || []).filter(Boolean)),
        niceToHave: JSON.stringify((payload.niceToHave || []).filter(Boolean)),
      })
      .returning();
    await db.insert(auditEvents).values({
      action: "job.created",
      entityType: "job",
      entityId: id,
      detail: JSON.stringify({ title }),
    });
    return Response.json({ job: serializeJob(job) }, { status: 201 });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "岗位创建失败" }, { status: 500 });
  }
}
