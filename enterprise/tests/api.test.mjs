import { test } from "node:test";
import assert from "node:assert/strict";
import { api, hash } from "../worker/api.js";
import { environment, headers } from "./harness.mjs";

async function request(
  env,
  path,
  method = "GET",
  data,
  subject = "owner",
  extra = {},
) {
  const r = await api.request(
    `https://console.test${path}`,
    {
      method,
      headers: headers(subject, extra),
      body: data === undefined ? undefined : JSON.stringify(data),
    },
    env,
  );
  let output;
  try {
    output = await r.json();
  } catch {
    output = null;
  }
  return { status: r.status, data: output };
}
async function setup() {
  const env = environment();
  assert.equal((await request(env, "/session")).status, 200);
  return env;
}
const brief = {
  title: "Research worker runtime",
  brief: "Inspect primary documentation and write a cited Markdown guide.",
  kind: "research",
  max_tokens: 10000,
};
async function create(env, extra = {}, key = crypto.randomUUID()) {
  const r = await request(
    env,
    "/orgs/org_primary/jobs",
    "POST",
    { ...brief, ...extra },
    "owner",
    { "idempotency-key": key },
  );
  assert.equal(r.status, 201, JSON.stringify(r.data));
  return r.data.job;
}
async function worker(env) {
  const r = await request(env, "/orgs/org_primary/workers", "POST", {
    name: "test-worker",
    mode: "docker",
  });
  assert.equal(r.status, 201);
  return { authorization: `Bearer ${r.data.worker_token}` };
}
test("unauthenticated requests rejected; cross-origin mutation rejected", async () => {
  const env = environment();
  assert.equal(
    (await api.request("https://console.test/session", {}, env)).status,
    401,
  );
  await request(env, "/session");
  assert.equal(
    (
      await request(env, "/orgs/org_primary/jobs", "POST", brief, "owner", {
        origin: "https://evil.test",
        "idempotency-key": "test-key-001",
      })
    ).status,
    403,
  );
});
test("tenant-scoped reads hide other organizations", async () => {
  const env = await setup();
  const second = await request(env, "/organizations", "POST", {
    name: "Second organization",
  });
  assert.equal(second.status, 201);
  assert.equal(
    (
      await request(
        env,
        `/orgs/${second.data.id}/jobs`,
        "GET",
        undefined,
        "stranger",
      )
    ).status,
    404,
  );
});
test("viewer cannot create tasks or enroll workers", async () => {
  const e = await setup();
  e.db
    .prepare("INSERT INTO memberships VALUES (?,?,?,?,?)")
    .run("org_primary", "viewer", "viewer@example.com", "viewer", 1);
  assert.equal(
    (
      await request(e, "/orgs/org_primary/jobs", "POST", brief, "viewer", {
        "idempotency-key": "view-test-01",
      })
    ).status,
    403,
  );
  assert.equal(
    (
      await request(
        e,
        "/orgs/org_primary/workers",
        "POST",
        { name: "Bad", mode: "docker" },
        "viewer",
      )
    ).status,
    403,
  );
});
test("idempotency produces one job and one audit mutation", async () => {
  const e = await setup();
  const j = await create(e, {}, "duplicate-key");
  const again = await request(
    e,
    "/orgs/org_primary/jobs",
    "POST",
    brief,
    "owner",
    { "idempotency-key": "duplicate-key" },
  );
  assert.equal(again.status, 200);
  assert.equal(again.data.job.id, j.id);
  assert.equal(e.db.prepare("SELECT count(*) AS n FROM jobs").get().n, 1);
  assert.equal(
    e.db
      .prepare("SELECT count(*) AS n FROM audit WHERE action='task.created'")
      .get().n,
    1,
  );
});
test("daily quota rejects without orphan task or audit", async () => {
  const e = await setup();
  e.db.prepare("UPDATE organizations SET daily_jobs=1").run();
  await create(e);
  assert.equal(
    (
      await request(e, "/orgs/org_primary/jobs", "POST", brief, "owner", {
        "idempotency-key": "quota-second",
      })
    ).status,
    429,
  );
  assert.equal(e.db.prepare("SELECT count(*) AS n FROM jobs").get().n, 1);
});
test("external grant waits for approval; self-approval needs explicit owner override", async () => {
  const e = await setup();
  const j = await create(e, {
    grant: {
      external_actions: ["browser_write"],
      browser_write_domains: ["example.com"],
    },
  });
  assert.equal(j.status, "pending_approval");
  assert.equal(
    (
      await request(e, `/orgs/org_primary/jobs/${j.id}/approve`, "POST", {
        reason: "Valid reviewed task",
      })
    ).status,
    403,
  );
  assert.equal(
    (
      await request(e, `/orgs/org_primary/jobs/${j.id}/approve`, "POST", {
        reason: "Owner accepts this scoped change",
        owner_override: true,
      })
    ).status,
    200,
  );
});
test("spending disabled and grant domains reject private/invalid hostnames", async () => {
  const e = await setup();
  for (const g of [
    {
      external_actions: ["spend"],
      browser_write_domains: ["example.com"],
      max_spend: 10,
    },
    {
      external_actions: ["browser_write"],
      browser_write_domains: ["localhost"],
    },
    { external_actions: ["message"], browser_write_domains: ["example.com"] },
  ])
    assert.ok(
      (
        await request(
          e,
          "/orgs/org_primary/jobs",
          "POST",
          { ...brief, grant: g },
          "owner",
          { "idempotency-key": crypto.randomUUID() },
        )
      ).status >= 400,
    );
});
test("atomic claims give one worker per job; pending approval cannot claim", async () => {
  const e = await setup();
  await create(e);
  await create(e, {
    grant: {
      external_actions: ["browser_write"],
      browser_write_domains: ["example.com"],
    },
  });
  const a = await worker(e),
    b = await worker(e);
  const first = await request(e, "/worker/claim", "POST", {}, "none", a),
    second = await request(e, "/worker/claim", "POST", {}, "none", b);
  assert.ok(first.data.job);
  assert.equal(second.data.job, null);
  assert.equal(
    e.db.prepare("SELECT count(*) AS n FROM jobs WHERE status='running'").get()
      .n,
    1,
  );
});
test("worker token cannot use owner APIs", async () => {
  const e = await setup(),
    w = await worker(e);
  const r = await api.request(
    "https://console.test/orgs/org_primary/workers",
    {
      method: "POST",
      headers: { ...w, "content-type": "application/json" },
      body: JSON.stringify({ name: "evil", mode: "docker" }),
    },
    e,
  );
  assert.equal(r.status, 401);
});
test("expired or cancelled lease cannot heartbeat/finish", async () => {
  const e = await setup(),
    j = await create(e),
    w = await worker(e),
    claim = (await request(e, "/worker/claim", "POST", {}, "none", w)).data;
  e.db.prepare("UPDATE jobs SET lease_expires_at=1 WHERE id=?").run(j.id);
  assert.equal(
    (
      await request(
        e,
        `/worker/jobs/${j.id}/heartbeat`,
        "POST",
        { lease_token: claim.lease_token },
        "none",
        w,
      )
    ).status,
    409,
  );
  await request(e, "/orgs/org_primary/jobs");
  assert.equal(
    e.db.prepare("SELECT status FROM jobs WHERE id=?").get(j.id).status,
    "interrupted",
  );
});
test("artifacts reject traversal, require current lease, and download as attachment", async () => {
  const e = await setup(),
    j = await create(e),
    w = await worker(e),
    claim = (await request(e, "/worker/claim", "POST", {}, "none", w)).data;
  const upload = (p) =>
    api.request(
      `https://console.test/worker/jobs/${j.id}/artifacts?path=${encodeURIComponent(p)}`,
      {
        method: "PUT",
        headers: { ...w, "x-lease-token": claim.lease_token },
        body: "<script>evil()</script>",
      },
      e,
    );
  assert.equal((await upload("../evil.html")).status, 400);
  assert.equal((await upload("index.html")).status, 201);
  const a = e.db.prepare("SELECT * FROM artifacts").get();
  const r = await api.request(
    `https://console.test/orgs/org_primary/artifacts/${a.id}`,
    { headers: headers() },
    e,
  );
  assert.equal(r.status, 200);
  assert.match(r.headers.get("content-disposition"), /^attachment/);
  assert.match(r.headers.get("content-security-policy"), /sandbox/);
  assert.equal(a.sha256, await hash("<script>evil()</script>"));
});
test("completed gate refuses missing artifact, gaps, invalid audit or token overrun", async () => {
  const e = await setup(),
    j = await create(e),
    w = await worker(e),
    claim = (await request(e, "/worker/claim", "POST", {}, "none", w)).data;
  const base = {
    status: "completed",
    model_tokens: 100,
    audit_valid: true,
    unresolved_gaps: [],
  };
  const finish = (r) =>
    request(
      e,
      `/worker/jobs/${j.id}/finish`,
      "POST",
      { lease_token: claim.lease_token, result: r },
      "none",
      w,
    );
  assert.equal((await finish(base)).status, 400);
  await api.request(
    `https://console.test/worker/jobs/${j.id}/artifacts?path=guide.md`,
    {
      method: "PUT",
      headers: { ...w, "x-lease-token": claim.lease_token },
      body: "A checked guide",
    },
    e,
  );
  for (const invalid of [
    { ...base, audit_valid: false },
    { ...base, unresolved_gaps: ["missing evidence"] },
    { ...base, model_tokens: 10001 },
  ])
    assert.equal((await finish(invalid)).status, 400);
  assert.equal((await finish(base)).status, 200);
  assert.equal((await finish(base)).status, 200);
  assert.equal(
    e.db
      .prepare("SELECT count(*) AS n FROM audit WHERE action='task.finished'")
      .get().n,
    1,
  );
});

test("configured owner controls initial workspace bootstrap", async () => {
  const e = environment();
  e.AEON_OWNER_EMAIL = "owner@example.com";
  assert.equal(
    (await request(e, "/session", "GET", undefined, "stranger")).status,
    403,
  );
  assert.equal((await request(e, "/session")).status, 200);
});
test("cancellation during R2 upload prevents metadata commit", async () => {
  const e = await setup(),
    j = await create(e),
    w = await worker(e);
  const claim = (await request(e, "/worker/claim", "POST", {}, "none", w)).data;
  const put = e.BUCKET.put;
  e.BUCKET.put = async (...args) => {
    await put(...args);
    await request(e, `/orgs/org_primary/jobs/${j.id}/cancel`, "POST", {});
  };
  const response = await api.request(
    `https://console.test/worker/jobs/${j.id}/artifacts?path=report.md`,
    {
      method: "PUT",
      headers: { ...w, "x-lease-token": claim.lease_token },
      body: "report",
    },
    e,
  );
  assert.equal(response.status, 409);
  assert.equal(e.db.prepare("SELECT count(*) AS n FROM artifacts").get().n, 0);
  assert.equal(
    (
      await request(
        e,
        `/worker/jobs/${j.id}/heartbeat`,
        "POST",
        { lease_token: claim.lease_token },
        "none",
        w,
      )
    ).status,
    409,
  );
});
test("JSON body bound enforced before parsing", async () => {
  const e = await setup();
  const r = await api.request(
    "https://console.test/orgs/org_primary/jobs",
    { method: "POST", headers: headers(), body: " ".repeat(128001) },
    e,
  );
  assert.equal(r.status, 413);
});
test("cancellation cannot recycle reserved token quota", async () => {
  const e = await setup();
  e.db.prepare("UPDATE organizations SET daily_tokens=10000").run();
  const j = await create(e);
  await request(e, `/orgs/org_primary/jobs/${j.id}/cancel`, "POST", {});
  const r = await request(e, "/orgs/org_primary/jobs", "POST", brief, "owner", {
    "idempotency-key": crypto.randomUUID(),
  });
  assert.equal(r.status, 429);
});
test("partial resume reserves remaining tokens atomically", async () => {
  const e = await setup();
  e.db.prepare("UPDATE organizations SET daily_tokens=20000").run();
  const j = await create(e);
  e.db
    .prepare("UPDATE jobs SET status='partial',used_tokens=1000 WHERE id=?")
    .run(j.id);
  await create(e, { max_tokens: 19000 });
  const r = await request(e, `/orgs/org_primary/jobs/${j.id}/resume`, "POST", {
    additional_steps: 1,
  });
  assert.equal(r.status, 409);
  assert.equal(
    e.db.prepare("SELECT status FROM jobs WHERE id=?").get(j.id).status,
    "partial",
  );
  assert.equal(
    e.db
      .prepare(
        "SELECT count(*) AS n FROM audit WHERE action='task.resume_requested'",
      )
      .get().n,
    0,
  );
});
test("revoked worker immediately loses API access", async () => {
  const e = await setup(),
    w = await worker(e);
  const row = e.db.prepare("SELECT * FROM workers").get();
  await request(e, `/orgs/org_primary/workers/${row.id}/revoke`, "POST", {});
  assert.equal(
    (await request(e, "/worker/claim", "POST", {}, "none", w)).status,
    401,
  );
});
test("invitation binds email and can only be consumed once", async () => {
  const e = await setup(),
    r = await request(e, "/orgs/org_primary/invitations", "POST", {
      email: "reviewer@example.com",
      role: "reviewer",
    }),
    key = new URL(r.data.invite_url).searchParams.get("invite");
  assert.equal(
    (
      await request(
        e,
        "/invitations/accept",
        "POST",
        { token: key },
        "stranger",
      )
    ).status,
    403,
  );
  assert.equal(
    (
      await request(
        e,
        "/invitations/accept",
        "POST",
        { token: key },
        "reviewer",
      )
    ).status,
    200,
  );
  assert.equal(
    (
      await request(
        e,
        "/invitations/accept",
        "POST",
        { token: key },
        "reviewer",
      )
    ).status,
    403,
  );
});
