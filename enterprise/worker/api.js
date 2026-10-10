import { Hono } from "hono";
import { z } from "zod";
export const api = new Hono();
const now = () => Math.floor(Date.now() / 1000),
  id = (p) => `${p}_${crypto.randomUUID().replaceAll("-", "")}`,
  token = () =>
    crypto.randomUUID().replaceAll("-", "") +
    crypto.randomUUID().replaceAll("-", "");
export const hash = async (v) =>
  [
    ...new Uint8Array(
      await crypto.subtle.digest(
        "SHA-256",
        typeof v === "string" ? new TextEncoder().encode(v) : v,
      ),
    ),
  ]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
const fail = (status, message) => {
  throw Object.assign(new Error(message), { status });
};
const stmt = (e, s, ...a) => e.DB.prepare(s).bind(...a),
  one = (e, s, ...a) => stmt(e, s, ...a).first(),
  rows = async (e, s, ...a) => (await stmt(e, s, ...a).all()).results;
async function boundedBytes(request, limit) {
  if (!request.body) return new Uint8Array().buffer;
  const reader = request.body.getReader(),
    chunks = [];
  let size = 0;
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > limit) {
      await reader.cancel();
      fail(413, "Request too large.");
    }
    chunks.push(value);
  }
  const output = new Uint8Array(size);
  let offset = 0;
  for (const chunk of chunks) {
    output.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return output.buffer;
}
const connection = (c, org, worker, key, mode) => ({
  base_url: new URL(c.req.url).origin,
  org_id: org,
  worker_id: worker,
  worker_token: key,
  site_token: c.env.AEON_SITE_SERVICE_KEY || "",
  mode,
});
const body = async (c) => {
  if (!c.req.header("content-type")?.startsWith("application/json"))
    fail(415, "JSON required.");
  const raw = new TextDecoder().decode(await boundedBytes(c.req.raw, 128000));
  if (new TextEncoder().encode(raw).length > 128000)
    fail(413, "Request too large.");
  try {
    return JSON.parse(raw);
  } catch {
    fail(400, "Invalid JSON.");
  }
};
const parse = (s, v) => {
  const r = s.safeParse(v);
  if (!r.success)
    fail(
      400,
      r.error.issues
        .map((x) => x.message)
        .join("; ")
        .slice(0, 500),
    );
  return r.data;
};
const grantSchema = z
  .object({
    external_actions: z
      .array(z.enum(["publish", "message", "spend", "delete", "browser_write"]))
      .max(5)
      .default([]),
    browser_write_domains: z
      .array(
        z
          .string()
          .regex(
            /^(?!localhost$)(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}$/,
          ),
      )
      .max(15)
      .default([]),
    recipients: z.array(z.string().min(3).max(200)).max(20).default([]),
    max_spend: z.number().finite().min(0).max(100).default(0),
    currency: z
      .string()
      .regex(/^[A-Z]{3}$/)
      .default("USD"),
  })
  .strict();
const jobSchema = z
  .object({
    title: z.string().trim().min(3).max(120),
    brief: z.string().trim().min(10).max(12000),
    kind: z
      .enum(["research", "website", "code", "browser_file", "general"])
      .default("general"),
    grant: grantSchema.prefault({}),
    max_tokens: z.number().int().min(1000).max(50000).default(20000),
    max_steps: z.number().int().min(1).max(64).default(32),
    max_revisions: z.number().int().min(0).max(5).default(3),
    deadline_minutes: z.number().int().min(1).max(90).default(30),
  })
  .strict();
const leaseSchema = z.object({ lease_token: z.string().min(30).max(150) });
const safePath = z
  .string()
  .min(1)
  .max(240)
  .regex(/^[a-zA-Z0-9_ .\/-]+$/)
  .refine(
    (p) =>
      !p.startsWith("/") &&
      !p.split("/").some((s) => !s || s === "." || s === ".."),
    "Unsafe artifact path.",
  );
const decode = (j) =>
  j
    ? {
        ...j,
        grant: JSON.parse(j.grant),
        result: j.result ? JSON.parse(j.result) : null,
        progress: j.progress ? JSON.parse(j.progress) : null,
        resume_options: j.resume_options ? JSON.parse(j.resume_options) : null,
        lease_hash: undefined,
      }
    : null;
const auditStmt = (
  e,
  actor,
  org,
  action,
  target,
  detail,
  conditional = false,
) =>
  stmt(
    e,
    `INSERT INTO audit (org_id,actor,action,target,detail,created_at) SELECT ?,?,?,?,?,? ${conditional ? "WHERE changes()>0" : ""}`,
    org,
    actor,
    action,
    target,
    JSON.stringify(detail),
    now(),
  );
async function mutate(c, sql, args, action, target, detail = {}) {
  const a = c.get("auth");
  return (
    await c.env.DB.batch([
      stmt(c.env, sql, ...args),
      auditStmt(c.env, a.subject, a.org.id, action, target, detail, true),
    ])
  )[0];
}
async function primary(e) {
  await stmt(
    e,
    "INSERT OR IGNORE INTO organizations (id,name,created_at) VALUES (?,?,?)",
    "org_primary",
    "AEON workspace",
    now(),
  ).run();
  return one(e, "SELECT * FROM organizations WHERE id=?", "org_primary");
}
function csrf(c) {
  if (
    !["GET", "HEAD", "OPTIONS"].includes(c.req.method) &&
    !c.get("service") &&
    (c.req.header("origin") !== new URL(c.req.url).origin ||
      c.req.header("sec-fetch-site") === "cross-site")
  )
    fail(403, "Same-origin request required.");
}
async function user(c) {
  const subject = c.req.header("oai-authenticated-user-id"),
    email = c.req.header("oai-authenticated-user-email");
  if (!subject || !email) fail(401, "Authenticated user required.");
  return { subject, email: email.toLowerCase() };
}
api.use("*", async (c, next) => {
  if (!c.env.DB) fail(503, "Database unavailable.");
  if (Number(c.req.header("content-length") || 0) > 8500000)
    fail(413, "Request too large.");
  const b = c.req.header("authorization")?.replace(/^Bearer /, "");
  if (
    b &&
    c.env.AEON_ADMIN_KEY &&
    (await hash(b)) === (await hash(c.env.AEON_ADMIN_KEY))
  )
    c.set("service", true);
  await next();
});
api.onError((e, c) => {
  if (!e.status) console.error("enterprise_request_failed", c.req.path, e.name);
  return c.json(
    {
      error: e.status
        ? e.message
        : "Service unavailable; retry a safe operation.",
    },
    e.status || 500,
  );
});
api.get("/health", async (c) => {
  await one(c.env, "SELECT 1 AS ready");
  return c.json({
    status: "ready",
    version: "0.4.0",
    artifact_storage: !!c.env.BUCKET,
  });
});
api.post("/bootstrap", async (c) => {
  if (!c.get("service")) fail(401, "Deployment credential required.");
  const d = parse(
    z
      .object({
        name: z.string().min(2).max(80).default("AEON worker"),
        mode: z.enum(["docker", "trusted-local"]).default("docker"),
      })
      .strict(),
    await body(c),
  );
  const org = await primary(c.env),
    key = token(),
    w = id("worker");
  await c.env.DB.batch([
    stmt(
      c.env,
      "INSERT INTO workers (id,org_id,name,token_hash,mode,created_at) VALUES (?,?,?,?,?,?)",
      w,
      org.id,
      d.name,
      await hash(key),
      d.mode,
      now(),
    ),
    auditStmt(c.env, "service:deployment", org.id, "worker.enrolled", w, d),
  ]);
  return c.json(
    {
      worker_id: w,
      org_id: org.id,
      worker_token: key,
      mode: d.mode,
      connection: connection(c, org.id, w, key, d.mode),
    },
    201,
  );
});
api.get("/session", async (c) => {
  const u = await user(c);
  const initial = await primary(c.env);
  if (
    !initial.owner_subject &&
    c.env.AEON_OWNER_EMAIL &&
    u.email !== c.env.AEON_OWNER_EMAIL.toLowerCase()
  )
    fail(403, "Initial workspace belongs to its configured owner.");
  await c.env.DB.batch([
    stmt(
      c.env,
      "UPDATE organizations SET owner_subject=? WHERE id=? AND owner_subject IS NULL",
      u.subject,
      "org_primary",
    ),
    stmt(
      c.env,
      "INSERT OR IGNORE INTO memberships (org_id,subject,email,role,created_at) SELECT id,?,?,'owner',? FROM organizations WHERE id=? AND owner_subject=?",
      u.subject,
      u.email,
      now(),
      "org_primary",
      u.subject,
    ),
  ]);
  const orgs = await rows(
    c.env,
    "SELECT o.*,m.role FROM organizations o JOIN memberships m ON m.org_id=o.id WHERE m.subject=? ORDER BY o.created_at",
    u.subject,
  );
  if (!orgs.length)
    fail(403, "Membership required. Ask owner for an invitation.");
  return c.json({ ...u, organizations: orgs });
});
api.post("/organizations", async (c) => {
  const u = await user(c);
  csrf(c);
  const d = parse(
    z.object({ name: z.string().trim().min(3).max(80) }).strict(),
    await body(c),
  );
  if (
    (
      await one(
        c.env,
        "SELECT count(*) AS n FROM organizations WHERE owner_subject=?",
        u.subject,
      )
    ).n >= 10
  )
    fail(429, "Organization limit reached.");
  const org = id("org");
  await c.env.DB.batch([
    stmt(
      c.env,
      "INSERT INTO organizations (id,name,owner_subject,created_at) VALUES (?,?,?,?)",
      org,
      d.name,
      u.subject,
      now(),
    ),
    stmt(
      c.env,
      "INSERT INTO memberships (org_id,subject,email,role,created_at) VALUES (?,?,?,'owner',?)",
      org,
      u.subject,
      u.email,
      now(),
    ),
    auditStmt(c.env, u.subject, org, "organization.created", org, d),
  ]);
  return c.json({ id: org }, 201);
});
api.post("/invitations/accept", async (c) => {
  const u = await user(c);
  csrf(c);
  const d = parse(
    z.object({ token: z.string().min(30).max(150) }).strict(),
    await body(c),
  );
  const i = await one(
    c.env,
    "SELECT * FROM invitations WHERE token_hash=? AND expires_at>? AND consumed_by IS NULL",
    await hash(d.token),
    now(),
  );
  if (!i || i.email !== u.email)
    fail(403, "Invitation invalid, expired, or belongs to another email.");
  const r = await c.env.DB.batch([
    stmt(
      c.env,
      "UPDATE invitations SET consumed_by=? WHERE id=? AND consumed_by IS NULL",
      u.subject,
      i.id,
    ),
    stmt(
      c.env,
      "INSERT OR IGNORE INTO memberships (org_id,subject,email,role,created_at) SELECT org_id,?,?,role,? FROM invitations WHERE id=? AND consumed_by=?",
      u.subject,
      u.email,
      now(),
      i.id,
      u.subject,
    ),
    auditStmt(c.env, u.subject, i.org_id, "invitation.accepted", i.id, {}),
  ]);
  if (!r[0].meta.changes) fail(409, "Invitation already consumed.");
  return c.json({ org_id: i.org_id });
});
api.use("/orgs/:orgId/*", async (c, next) => {
  const org = await one(
    c.env,
    "SELECT * FROM organizations WHERE id=?",
    c.req.param("orgId"),
  );
  if (!org) fail(404, "Workspace not found.");
  let a;
  if (c.get("service")) {
    if (org.id !== "org_primary")
      fail(403, "Deployment credential restricted to initial workspace.");
    a = { subject: "service:deployment", role: "owner", org };
  } else {
    const u = await user(c),
      m = await one(
        c.env,
        "SELECT * FROM memberships WHERE org_id=? AND subject=?",
        org.id,
        u.subject,
      );
    if (!m) fail(404, "Workspace not found.");
    a = { ...u, role: m.role, org };
  }
  c.set("auth", a);
  csrf(c);
  await next();
});
const allow = (c, r) => {
  if (!r.includes(c.get("auth").role))
    fail(403, "Role does not permit operation.");
};
const jobFor = async (c) => {
  const j = await one(
    c.env,
    "SELECT * FROM jobs WHERE org_id=? AND id=?",
    c.get("auth").org.id,
    c.req.param("jobId"),
  );
  if (!j) fail(404, "Task not found.");
  return j;
};
async function expire(e, o) {
  await stmt(
    e,
    "UPDATE jobs SET status='interrupted',lease_hash=NULL,updated_at=? WHERE org_id=? AND status='running' AND lease_expires_at<=?",
    now(),
    o,
    now(),
  ).run();
}
api.get("/orgs/:orgId/dashboard", async (c) => {
  const o = c.get("auth").org;
  await expire(c.env, o.id);
  const day = Math.floor(now() / 86400) * 86400;
  return c.json({
    organization: o,
    role: c.get("auth").role,
    stats: await rows(
      c.env,
      "SELECT status,count(*) AS count FROM jobs WHERE org_id=? GROUP BY status",
      o.id,
    ),
    usage: await one(
      c.env,
      "SELECT count(*) AS jobs,coalesce(sum(CASE WHEN status IN ('completed','partial','failed') THEN used_tokens ELSE max_tokens END),0) AS reserved_tokens FROM jobs WHERE org_id=? AND created_at>=?",
      o.id,
      day,
    ),
    workers: await rows(
      c.env,
      "SELECT id,name,mode,revoked,heartbeat_at,created_at FROM workers WHERE org_id=? ORDER BY created_at DESC",
      o.id,
    ),
  });
});
api.get("/orgs/:orgId/jobs", async (c) => {
  await expire(c.env, c.get("auth").org.id);
  return c.json({
    jobs: (
      await rows(
        c.env,
        "SELECT * FROM jobs WHERE org_id=? ORDER BY created_at DESC LIMIT 100",
        c.get("auth").org.id,
      )
    ).map(decode),
  });
});
api.post("/orgs/:orgId/jobs", async (c) => {
  allow(c, ["owner", "operator"]);
  const a = c.get("auth"),
    d = parse(jobSchema, await body(c)),
    ik = c.req.header("idempotency-key");
  if (!ik || !/^[a-zA-Z0-9_-]{8,100}$/.test(ik))
    fail(400, "Idempotency-Key header required.");
  const old = await one(
    c.env,
    "SELECT * FROM jobs WHERE org_id=? AND idempotency_key=?",
    a.org.id,
    ik,
  );
  if (old) return c.json({ job: decode(old), replayed: true });
  if (d.max_tokens > a.org.max_task_tokens)
    fail(400, "Task exceeds token ceiling.");
  if (
    d.grant.external_actions.includes("spend") &&
    c.env.AEON_ALLOW_SPEND !== "true"
  )
    fail(403, "Spending disabled by deployment policy.");
  if (d.grant.external_actions.length && !d.grant.browser_write_domains.length)
    fail(400, "External actions need allowed domains.");
  if (
    d.grant.external_actions.includes("message") &&
    !d.grant.recipients.length
  )
    fail(400, "Messaging needs explicit recipients.");
  const j = id("job"),
    ts = now(),
    day = Math.floor(ts / 86400) * 86400,
    status = d.grant.external_actions.length ? "pending_approval" : "queued";
  const r = await mutate(
    c,
    `INSERT INTO jobs (id,org_id,title,brief,status,kind,grant,max_tokens,max_steps,max_revisions,deadline_minutes,created_by,idempotency_key,created_at,updated_at)
    SELECT ?,?,?,?,?,?,?,?,?,?,?,?,?,?,? WHERE NOT EXISTS (SELECT 1 FROM jobs WHERE org_id=? AND idempotency_key=?)
    AND (SELECT count(*) FROM jobs WHERE org_id=? AND created_at>=?)<?
    AND (SELECT coalesce(sum(CASE WHEN status IN ('completed','partial','failed') THEN used_tokens ELSE max_tokens END),0) FROM jobs WHERE org_id=? AND created_at>=?)+?<=?`,
    [
      j,
      a.org.id,
      d.title,
      d.brief,
      status,
      d.kind,
      JSON.stringify(d.grant),
      d.max_tokens,
      d.max_steps,
      d.max_revisions,
      d.deadline_minutes,
      a.subject,
      ik,
      ts,
      ts,
      a.org.id,
      ik,
      a.org.id,
      day,
      a.org.daily_jobs,
      a.org.id,
      day,
      d.max_tokens,
      a.org.daily_tokens,
    ],
    "task.created",
    j,
    { status, kind: d.kind, max_tokens: d.max_tokens },
  );
  if (!r.meta.changes) {
    const replay = await one(
      c.env,
      "SELECT * FROM jobs WHERE org_id=? AND idempotency_key=?",
      a.org.id,
      ik,
    );
    if (replay) return c.json({ job: decode(replay), replayed: true });
    fail(429, "Daily task or token reservation quota reached.");
  }
  return c.json(
    { job: decode(await one(c.env, "SELECT * FROM jobs WHERE id=?", j)) },
    201,
  );
});
api.get("/orgs/:orgId/jobs/:jobId", async (c) =>
  c.json({
    job: decode(await jobFor(c)),
    artifacts: await rows(
      c.env,
      "SELECT id,path,size,sha256,created_at FROM artifacts WHERE org_id=? AND job_id=? ORDER BY path",
      c.get("auth").org.id,
      c.req.param("jobId"),
    ),
  }),
);
api.post("/orgs/:orgId/jobs/:jobId/approve", async (c) => {
  allow(c, ["owner", "reviewer"]);
  const j = await jobFor(c),
    a = c.get("auth"),
    d = parse(
      z
        .object({
          reason: z.string().trim().min(10).max(500),
          owner_override: z.boolean().default(false),
        })
        .strict(),
      await body(c),
    );
  if (j.created_by === a.subject && !(a.role === "owner" && d.owner_override))
    fail(403, "Independent approval required; owner may explicitly override.");
  const r = await mutate(
    c,
    "UPDATE jobs SET status='queued',approved_by=?,updated_at=? WHERE id=? AND org_id=? AND status='pending_approval'",
    [a.subject, now(), j.id, a.org.id],
    "task.approved",
    j.id,
    d,
  );
  if (!r.meta.changes) fail(409, "Task no longer awaiting approval.");
  return c.json({ status: "queued" });
});
api.post("/orgs/:orgId/jobs/:jobId/cancel", async (c) => {
  allow(c, ["owner", "operator"]);
  const j = await jobFor(c),
    r = await mutate(
      c,
      "UPDATE jobs SET status='cancelled',lease_hash=NULL,updated_at=? WHERE id=? AND org_id=? AND status IN ('queued','pending_approval','running','interrupted')",
      [now(), j.id, c.get("auth").org.id],
      "task.cancelled",
      j.id,
    );
  if (!r.meta.changes) fail(409, "Task cannot be cancelled in current state.");
  return c.json({ status: "cancelled" });
});
api.post("/orgs/:orgId/jobs/:jobId/resume", async (c) => {
  allow(c, ["owner", "operator"]);
  const j = await jobFor(c),
    d = parse(
      z
        .object({
          additional_model_tokens: z
            .number()
            .int()
            .min(0)
            .max(10000)
            .default(0),
          additional_steps: z.number().int().min(0).max(20).default(0),
          additional_minutes: z.number().int().min(0).max(30).default(0),
          additional_revisions: z.number().int().min(0).max(2).default(0),
        })
        .strict(),
      await body(c),
    );
  if (j.status === "partial" && !Object.values(d).some(Boolean))
    fail(400, "Partial tasks need explicit additional limits.");
  if (
    j.max_tokens + d.additional_model_tokens >
    c.get("auth").org.max_task_tokens
  )
    fail(400, "Resume exceeds task ceiling.");
  if (
    j.max_steps + d.additional_steps > 200 ||
    j.max_revisions + d.additional_revisions > 20 ||
    j.deadline_minutes + d.additional_minutes > 1440
  )
    fail(400, "Resume exceeds runtime step, revision or deadline ceiling.");
  const r = await mutate(
    c,
    `UPDATE jobs SET status='queued',resume_options=?,max_tokens=max_tokens+?,max_steps=max_steps+?,max_revisions=max_revisions+?,deadline_minutes=deadline_minutes+?,lease_hash=NULL,updated_at=? WHERE id=? AND org_id=? AND status IN ('partial','interrupted')
      AND max_tokens+? <= (SELECT max_task_tokens FROM organizations WHERE id=jobs.org_id)
      AND max_steps+?<=200 AND max_revisions+?<=20 AND deadline_minutes+?<=1440
      AND (SELECT coalesce(sum(CASE WHEN status IN ('completed','partial','failed') THEN used_tokens ELSE max_tokens END),0) FROM jobs WHERE org_id=? AND created_at>=?)+? <= ?`,
    [
      JSON.stringify(d),
      d.additional_model_tokens,
      d.additional_steps,
      d.additional_revisions,
      d.additional_minutes,
      now(),
      j.id,
      c.get("auth").org.id,
      d.additional_model_tokens,
      d.additional_steps,
      d.additional_revisions,
      d.additional_minutes,
      c.get("auth").org.id,
      Math.floor(now() / 86400) * 86400,
      j.status === "partial"
        ? Math.max(0, j.max_tokens + d.additional_model_tokens - j.used_tokens)
        : d.additional_model_tokens,
      c.get("auth").org.daily_tokens,
    ],
    "task.resume_requested",
    j.id,
    d,
  );
  if (!r.meta.changes)
    fail(
      409,
      "Resume denied: task state changed or organization token quota reached.",
    );
  return c.json({ status: "queued" });
});
api.get("/orgs/:orgId/audit", async (c) => {
  const after = Number(c.req.query("after") || 0);
  if (!Number.isSafeInteger(after) || after < 0)
    fail(400, "Invalid audit cursor.");
  return c.json({
    events: await rows(
      c.env,
      "SELECT * FROM audit WHERE org_id=? AND id>? ORDER BY id LIMIT 200",
      c.get("auth").org.id,
      after,
    ),
  });
});
api.get("/orgs/:orgId/export", async (c) => {
  allow(c, ["owner"]);
  const o = c.get("auth").org;
  return c.json({
    version: "0.4.0",
    exported_at: now(),
    organization: o,
    jobs: (await rows(c.env, "SELECT * FROM jobs WHERE org_id=?", o.id)).map(
      decode,
    ),
    artifacts: await rows(
      c.env,
      "SELECT id,job_id,path,size,sha256 FROM artifacts WHERE org_id=?",
      o.id,
    ),
    audit: await rows(
      c.env,
      "SELECT * FROM audit WHERE org_id=? ORDER BY id",
      o.id,
    ),
  });
});
api.get("/orgs/:orgId/members", async (c) =>
  c.json({
    members: await rows(
      c.env,
      "SELECT subject,email,role,created_at FROM memberships WHERE org_id=?",
      c.get("auth").org.id,
    ),
  }),
);
api.post("/orgs/:orgId/invitations", async (c) => {
  allow(c, ["owner"]);
  const d = parse(
      z
        .object({
          email: z.string().email().max(200),
          role: z.enum(["operator", "reviewer", "viewer"]),
        })
        .strict(),
      await body(c),
    ),
    key = token(),
    i = id("invite");
  await mutate(
    c,
    "INSERT INTO invitations (id,org_id,email,role,token_hash,expires_at) VALUES (?,?,?,?,?,?)",
    [
      i,
      c.get("auth").org.id,
      d.email.toLowerCase(),
      d.role,
      await hash(key),
      now() + 86400,
    ],
    "invitation.created",
    i,
    d,
  );
  return c.json(
    {
      invite_url: new URL(`/?invite=${key}`, c.req.url).href,
      expires_at: now() + 86400,
    },
    201,
  );
});
api.post("/orgs/:orgId/members/:subject", async (c) => {
  allow(c, ["owner"]);
  const d = parse(
      z.object({ role: z.enum(["operator", "reviewer", "viewer"]) }).strict(),
      await body(c),
    ),
    s = c.req.param("subject");
  if (s === c.get("auth").org.owner_subject)
    fail(400, "Owner cannot be demoted.");
  const r = await mutate(
    c,
    "UPDATE memberships SET role=? WHERE org_id=? AND subject=?",
    [d.role, c.get("auth").org.id, s],
    "membership.role_changed",
    s,
    d,
  );
  if (!r.meta.changes) fail(404, "Member not found.");
  return c.json(d);
});
api.post("/orgs/:orgId/workers", async (c) => {
  allow(c, ["owner"]);
  const d = parse(
      z
        .object({
          name: z.string().min(2).max(80),
          mode: z.enum(["docker", "trusted-local"]),
        })
        .strict(),
      await body(c),
    ),
    key = token(),
    w = id("worker");
  await mutate(
    c,
    "INSERT INTO workers (id,org_id,name,token_hash,mode,created_at) VALUES (?,?,?,?,?,?)",
    [w, c.get("auth").org.id, d.name, await hash(key), d.mode, now()],
    "worker.enrolled",
    w,
    d,
  );
  return c.json(
    {
      worker_id: w,
      worker_token: key,
      org_id: c.get("auth").org.id,
      connection: connection(c, c.get("auth").org.id, w, key, d.mode),
    },
    201,
  );
});
api.post("/orgs/:orgId/workers/:workerId/revoke", async (c) => {
  allow(c, ["owner"]);
  const r = await mutate(
    c,
    "UPDATE workers SET revoked=1 WHERE id=? AND org_id=? AND revoked=0",
    [c.req.param("workerId"), c.get("auth").org.id],
    "worker.revoked",
    c.req.param("workerId"),
  );
  if (!r.meta.changes) fail(404, "Active worker not found.");
  return c.json({ revoked: true });
});
api.get("/orgs/:orgId/artifacts/:artifactId", async (c) => {
  const a = await one(
    c.env,
    "SELECT * FROM artifacts WHERE id=? AND org_id=?",
    c.req.param("artifactId"),
    c.get("auth").org.id,
  );
  if (!a) fail(404, "Artifact not found.");
  const object = await c.env.BUCKET.get(a.object_key);
  if (!object) fail(404, "Stored artifact unavailable.");
  return new Response(object.body, {
    headers: {
      "content-type": "application/octet-stream",
      "content-disposition": `attachment; filename*=UTF-8''${encodeURIComponent(a.path.split("/").pop())}`,
      "content-security-policy": "sandbox; default-src 'none'",
      "x-content-type-options": "nosniff",
      "cache-control": "no-store",
      etag: `"${a.sha256}"`,
    },
  });
});
// Separate worker credentials have no approval or membership authority.
api.use("/worker/*", async (c, next) => {
  const b = c.req.header("authorization")?.replace(/^Bearer /, "");
  if (!b) fail(401, "Worker credential required.");
  const w = await one(
    c.env,
    "SELECT * FROM workers WHERE token_hash=? AND revoked=0",
    await hash(b),
  );
  if (!w) fail(401, "Worker credential invalid or revoked.");
  c.set("worker", w);
  c.set("service", true);
  c.set("auth", {
    subject: w.id,
    role: "worker",
    org: await one(c.env, "SELECT * FROM organizations WHERE id=?", w.org_id),
  });
  await stmt(
    c.env,
    "UPDATE workers SET heartbeat_at=? WHERE id=?",
    now(),
    w.id,
  ).run();
  await next();
});
api.post("/worker/claim", async (c) => {
  const w = c.get("worker");
  await expire(c.env, w.org_id);
  const key = token(),
    r = await mutate(
      c,
      `UPDATE jobs SET status='running',worker_id=?,lease_hash=?,lease_expires_at=?,attempts=attempts+1,updated_at=? WHERE id=(SELECT id FROM jobs WHERE org_id=? AND status='queued' AND (worker_id IS NULL OR worker_id=?) ORDER BY created_at LIMIT 1) AND status='queued' RETURNING *`,
      [w.id, await hash(key), now() + 90, now(), w.org_id, w.id],
      "task.claimed",
      w.id,
      { mode: w.mode },
    );
  const j = r.results?.[0];
  return c.json(
    j ? { job: decode(j), lease_token: key, lease_seconds: 90 } : { job: null },
  );
});
async function lease(c, key) {
  const w = c.get("worker"),
    j = await one(
      c.env,
      "SELECT * FROM jobs WHERE id=? AND org_id=? AND worker_id=? AND status='running' AND lease_expires_at>? AND lease_hash=?",
      c.req.param("jobId"),
      w.org_id,
      w.id,
      now(),
      await hash(key),
    );
  if (!j) fail(409, "Lease lost, expired, or task cancelled.");
  return j;
}
api.post("/worker/jobs/:jobId/heartbeat", async (c) => {
  const d = parse(
      leaseSchema
        .extend({
          progress: z
            .object({
              phase: z.string().max(30),
              steps: z.number().int().min(0),
              tokens: z.number().int().min(0),
            })
            .optional(),
        })
        .strict(),
      await body(c),
    ),
    j = await lease(c, d.lease_token);
  const r = await stmt(
    c.env,
    "UPDATE jobs SET lease_expires_at=?,progress=?,updated_at=? WHERE id=? AND lease_hash=? AND status='running'",
    now() + 90,
    JSON.stringify(d.progress || {}),
    now(),
    j.id,
    await hash(d.lease_token),
  ).run();
  if (!r.meta.changes) fail(409, "Lease lost.");
  return c.json({ lease_seconds: 90 });
});
api.put("/worker/jobs/:jobId/artifacts", async (c) => {
  const key = c.req.header("x-lease-token");
  if (!key) fail(401, "Lease token required.");
  const j = await lease(c, key),
    p = parse(safePath, c.req.query("path"));
  if (
    !/\.(md|txt|html|css|js|mjs|jsx|ts|tsx|py|json|csv|svg|yaml|yml|toml|png|jpe?g|zip)$/i.test(
      p,
    )
  )
    fail(400, "Unsupported artifact format.");
  const bytes = await boundedBytes(c.req.raw, 8000000);
  if (bytes.byteLength > 8000000) fail(413, "Artifact exceeds 8 MB.");
  const totals = await one(
    c.env,
    "SELECT count(*) AS n,coalesce(sum(size),0) AS bytes FROM artifacts WHERE job_id=? AND path<>?",
    j.id,
    p,
  );
  if (totals.n >= 64 || totals.bytes + bytes.byteLength > 32000000)
    fail(429, "Artifact quota reached.");
  if (!c.env.BUCKET) fail(503, "Artifact storage unavailable.");
  const digest = await hash(bytes),
    objectKey = `${j.org_id}/${j.id}/${digest}/${p}`;
  await c.env.BUCKET.put(objectKey, bytes, {
    httpMetadata: { contentType: "application/octet-stream" },
  });
  const inserted = await mutate(
    c,
    `INSERT INTO artifacts (id,org_id,job_id,path,object_key,size,sha256,created_at)
     SELECT ?,?,?,?,?,?,?,? WHERE EXISTS (SELECT 1 FROM jobs WHERE id=? AND org_id=? AND worker_id=? AND status='running' AND lease_hash=? AND lease_expires_at>?)
     AND (SELECT count(*) FROM artifacts WHERE job_id=? AND path<>?)<64
     AND (SELECT coalesce(sum(size),0) FROM artifacts WHERE job_id=? AND path<>?)+?<=32000000
     ON CONFLICT(job_id,path) DO UPDATE SET object_key=excluded.object_key,size=excluded.size,sha256=excluded.sha256,created_at=excluded.created_at`,
    [
      id("artifact"),
      j.org_id,
      j.id,
      p,
      objectKey,
      bytes.byteLength,
      digest,
      now(),
      j.id,
      j.org_id,
      j.worker_id,
      await hash(key),
      now(),
      j.id,
      p,
      j.id,
      p,
      bytes.byteLength,
    ],
    "artifact.uploaded",
    j.id,
    { path: p, size: bytes.byteLength, sha256: digest },
  );
  if (!inserted.meta.changes)
    fail(409, "Lease changed or artifact quota reached during upload.");
  return c.json({ path: p, size: bytes.byteLength, sha256: digest }, 201);
});
api.post("/worker/jobs/:jobId/finish", async (c) => {
  const d = parse(
      leaseSchema
        .extend({ result: z.record(z.string(), z.unknown()) })
        .strict(),
      await body(c),
    ),
    status = d.result.status,
    tokens = d.result.model_tokens ?? 0;
  const a = c.get("auth");
  const finished = await one(
    c.env,
    "SELECT * FROM jobs WHERE id=? AND org_id=? AND worker_id=? AND lease_hash=? AND status IN ('completed','partial','failed','interrupted')",
    c.req.param("jobId"),
    a.org.id,
    a.subject,
    await hash(d.lease_token),
  );
  if (finished && finished.result === JSON.stringify(d.result))
    return c.json({ status: finished.status });
  const j = await lease(c, d.lease_token);
  if (!["completed", "partial", "failed", "interrupted"].includes(status))
    fail(400, "Invalid runtime status.");
  if (!Number.isSafeInteger(tokens) || tokens < 0) fail(400, "Invalid usage.");
  const count = await one(
    c.env,
    "SELECT count(*) AS n FROM artifacts WHERE job_id=?",
    j.id,
  );
  if (
    status === "completed" &&
    (!count.n ||
      tokens > j.max_tokens ||
      d.result.audit_valid !== true ||
      (d.result.unresolved_gaps || []).length)
  )
    fail(
      400,
      "Completion needs uploaded artifact, valid audit, no gaps or token overrun.",
    );
  const r = await mutate(
    c,
    "UPDATE jobs SET status=?,result=?,used_tokens=?,lease_expires_at=NULL,updated_at=? WHERE id=? AND org_id=? AND status='running' AND lease_hash=?",
    [
      status,
      JSON.stringify(d.result),
      tokens,
      now(),
      j.id,
      j.org_id,
      await hash(d.lease_token),
    ],
    "task.finished",
    j.id,
    {
      status,
      model_tokens: tokens,
      runtime_audit_valid: d.result.audit_valid === true,
    },
  );
  if (!r.meta.changes) fail(409, "Task state changed.");
  return c.json({ status });
});
