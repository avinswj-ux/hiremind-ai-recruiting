import { sql } from "drizzle-orm";
import { index, integer, sqliteTable, text, uniqueIndex } from "drizzle-orm/sqlite-core";

export const jobs = sqliteTable("jobs", {
  id: text("id").primaryKey(),
  title: text("title").notNull(),
  department: text("department").notNull().default(""),
  location: text("location").notNull().default(""),
  minYears: integer("min_years").notNull().default(0),
  mustHave: text("must_have").notNull().default("[]"),
  niceToHave: text("nice_to_have").notNull().default("[]"),
  status: text("status").notNull().default("open"),
  createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
});

export const candidates = sqliteTable(
  "candidates",
  {
    id: text("id").primaryKey(),
    jobId: text("job_id").notNull().references(() => jobs.id),
    fileName: text("file_name").notNull(),
    fileHash: text("file_hash").notNull(),
    name: text("name").notNull(),
    role: text("role").notNull().default(""),
    company: text("company").notNull().default(""),
    years: text("years").notNull().default(""),
    city: text("city").notNull().default(""),
    degree: text("degree").notNull().default(""),
    score: integer("score").notNull().default(0),
    status: text("status").notNull().default("待处理"),
    skills: text("skills").notNull().default("[]"),
    strength: text("strength").notNull().default(""),
    risk: text("risk").notNull().default(""),
    summary: text("summary").notNull().default(""),
    dimensions: text("dimensions").notNull().default("[]"),
    provider: text("provider").notNull().default("rules"),
    resumeExcerpt: text("resume_excerpt").notNull().default(""),
    createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
    updatedAt: text("updated_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [
    uniqueIndex("candidates_job_hash_unique").on(table.jobId, table.fileHash),
    index("candidates_job_score_idx").on(table.jobId, table.score),
  ],
);

export const auditEvents = sqliteTable(
  "audit_events",
  {
    id: integer("id").primaryKey({ autoIncrement: true }),
    action: text("action").notNull(),
    entityType: text("entity_type").notNull(),
    entityId: text("entity_id").notNull(),
    detail: text("detail").notNull().default("{}"),
    createdAt: text("created_at").notNull().default(sql`CURRENT_TIMESTAMP`),
  },
  (table) => [index("audit_entity_idx").on(table.entityType, table.entityId)],
);
