import {
  sqliteTable,
  text,
  integer,
  primaryKey,
  uniqueIndex,
  index,
} from "drizzle-orm/sqlite-core";

export const organizations = sqliteTable("organizations", {
  id: text("id").primaryKey(),
  name: text("name").notNull(),
  ownerSubject: text("owner_subject"),
  dailyJobs: integer("daily_jobs").notNull().default(25),
  dailyTokens: integer("daily_tokens").notNull().default(1000000),
  maxTaskTokens: integer("max_task_tokens").notNull().default(50000),
  createdAt: integer("created_at").notNull(),
});
export const memberships = sqliteTable(
  "memberships",
  {
    orgId: text("org_id")
      .notNull()
      .references(() => organizations.id),
    subject: text("subject").notNull(),
    email: text("email").notNull(),
    role: text("role").notNull(),
    createdAt: integer("created_at").notNull(),
  },
  (t) => [primaryKey({ columns: [t.orgId, t.subject] })],
);
export const workers = sqliteTable(
  "workers",
  {
    id: text("id").primaryKey(),
    orgId: text("org_id")
      .notNull()
      .references(() => organizations.id),
    name: text("name").notNull(),
    tokenHash: text("token_hash").notNull(),
    mode: text("mode").notNull(),
    revoked: integer("revoked").notNull().default(0),
    heartbeatAt: integer("heartbeat_at"),
    createdAt: integer("created_at").notNull(),
  },
  (t) => [
    uniqueIndex("workers_token").on(t.tokenHash),
    index("workers_org").on(t.orgId),
  ],
);
export const jobs = sqliteTable(
  "jobs",
  {
    id: text("id").primaryKey(),
    orgId: text("org_id")
      .notNull()
      .references(() => organizations.id),
    title: text("title").notNull(),
    brief: text("brief").notNull(),
    status: text("status").notNull(),
    kind: text("kind").notNull(),
    grant: text("grant").notNull(),
    maxTokens: integer("max_tokens").notNull(),
    maxSteps: integer("max_steps").notNull(),
    maxRevisions: integer("max_revisions").notNull(),
    deadlineMinutes: integer("deadline_minutes").notNull(),
    usedTokens: integer("used_tokens").notNull().default(0),
    createdBy: text("created_by").notNull(),
    approvedBy: text("approved_by"),
    idempotencyKey: text("idempotency_key").notNull(),
    workerId: text("worker_id").references(() => workers.id),
    leaseHash: text("lease_hash"),
    leaseExpiresAt: integer("lease_expires_at"),
    attempts: integer("attempts").notNull().default(0),
    result: text("result"),
    progress: text("progress"),
    resumeOptions: text("resume_options"),
    createdAt: integer("created_at").notNull(),
    updatedAt: integer("updated_at").notNull(),
  },
  (t) => [
    uniqueIndex("jobs_idempotency").on(t.orgId, t.idempotencyKey),
    index("jobs_queue").on(t.orgId, t.status, t.createdAt),
  ],
);
export const artifacts = sqliteTable(
  "artifacts",
  {
    id: text("id").primaryKey(),
    orgId: text("org_id")
      .notNull()
      .references(() => organizations.id),
    jobId: text("job_id")
      .notNull()
      .references(() => jobs.id),
    path: text("path").notNull(),
    objectKey: text("object_key").notNull(),
    size: integer("size").notNull(),
    sha256: text("sha256").notNull(),
    createdAt: integer("created_at").notNull(),
  },
  (t) => [
    uniqueIndex("artifact_path").on(t.jobId, t.path),
    index("artifact_org").on(t.orgId, t.jobId),
  ],
);
export const audit = sqliteTable(
  "audit",
  {
    id: integer("id").primaryKey({ autoIncrement: true }),
    orgId: text("org_id")
      .notNull()
      .references(() => organizations.id),
    actor: text("actor").notNull(),
    action: text("action").notNull(),
    target: text("target").notNull(),
    detail: text("detail").notNull(),
    createdAt: integer("created_at").notNull(),
  },
  (t) => [index("audit_org").on(t.orgId, t.id)],
);
export const invitations = sqliteTable(
  "invitations",
  {
    id: text("id").primaryKey(),
    orgId: text("org_id")
      .notNull()
      .references(() => organizations.id),
    email: text("email").notNull(),
    role: text("role").notNull(),
    tokenHash: text("token_hash").notNull(),
    expiresAt: integer("expires_at").notNull(),
    consumedBy: text("consumed_by"),
  },
  (t) => [uniqueIndex("invitation_token").on(t.tokenHash)],
);
