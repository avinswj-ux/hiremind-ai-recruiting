import { count, eq, sql } from "drizzle-orm";
import { getDb } from "../../../../db";
import { auditEvents, candidates, jobs } from "../../../../db/schema";

export async function PATCH(request: Request, context: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await context.params;
    const payload = (await request.json()) as { status?: "open" | "paused" | "archived" };
    if (!payload.status || !["open", "paused", "archived"].includes(payload.status)) {
      return Response.json({ error: "岗位状态不合法" }, { status: 400 });
    }
    const db = getDb();
    const [job] = await db
      .update(jobs)
      .set({ status: payload.status, updatedAt: sql`CURRENT_TIMESTAMP` })
      .where(eq(jobs.id, id))
      .returning();
    if (!job) return Response.json({ error: "岗位不存在" }, { status: 404 });
    await db.insert(auditEvents).values({
      action: "job.status_changed",
      entityType: "job",
      entityId: id,
      detail: JSON.stringify({ status: payload.status }),
    });
    return Response.json({ ok: true });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "岗位更新失败" }, { status: 500 });
  }
}

export async function DELETE(_: Request, context: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await context.params;
    const db = getDb();
    const [linked] = await db.select({ value: count() }).from(candidates).where(eq(candidates.jobId, id));
    if ((linked?.value || 0) > 0) {
      return Response.json({ error: "该岗位已关联候选人，只能归档" }, { status: 409 });
    }
    const [job] = await db.delete(jobs).where(eq(jobs.id, id)).returning();
    if (!job) return Response.json({ error: "岗位不存在" }, { status: 404 });
    await db.insert(auditEvents).values({
      action: "job.deleted",
      entityType: "job",
      entityId: id,
      detail: JSON.stringify({ title: job.title }),
    });
    return Response.json({ ok: true });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "岗位删除失败" }, { status: 500 });
  }
}
