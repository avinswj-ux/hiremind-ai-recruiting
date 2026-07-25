import { eq, sql } from "drizzle-orm";
import { getDb } from "../../../../db";
import { auditEvents, candidates } from "../../../../db/schema";

export async function PATCH(request: Request, context: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await context.params;
    const payload = (await request.json()) as { status?: string };
    const allowed = ["待处理", "建议面试", "已约面试", "人才库"];
    if (!payload.status || !allowed.includes(payload.status)) {
      return Response.json({ error: "候选人状态不合法" }, { status: 400 });
    }
    const db = getDb();
    const [candidate] = await db
      .update(candidates)
      .set({ status: payload.status, updatedAt: sql`CURRENT_TIMESTAMP` })
      .where(eq(candidates.id, id))
      .returning();
    if (!candidate) return Response.json({ error: "候选人不存在" }, { status: 404 });
    await db.insert(auditEvents).values({
      action: "candidate.status_changed",
      entityType: "candidate",
      entityId: id,
      detail: JSON.stringify({ status: payload.status }),
    });
    return Response.json({ ok: true });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "状态更新失败" }, { status: 500 });
  }
}

export async function DELETE(_: Request, context: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await context.params;
    const db = getDb();
    const [candidate] = await db.delete(candidates).where(eq(candidates.id, id)).returning();
    if (!candidate) return Response.json({ error: "候选人不存在" }, { status: 404 });
    await db.insert(auditEvents).values({
      action: "candidate.deleted",
      entityType: "candidate",
      entityId: id,
      detail: JSON.stringify({ name: candidate.name, jobId: candidate.jobId, fileName: candidate.fileName }),
    });
    return Response.json({ ok: true });
  } catch (error) {
    return Response.json({ error: error instanceof Error ? error.message : "候选人删除失败" }, { status: 500 });
  }
}
