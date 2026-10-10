import { test } from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { once } from "node:events";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { api } from "../worker/api.js";
import { createLocalServer } from "../scripts/local-server.mjs";

const worker = {
  fetch(request, env) {
    const url = new URL(request.url);
    return api.fetch(
      new Request(
        new URL(url.pathname.slice(4) + url.search, url.origin),
        request,
      ),
      env,
    );
  },
};
async function start(options = { ephemeral: true }) {
  const { server, env } = createLocalServer(worker, options);
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const port = server.address().port,
    origin = `http://127.0.0.1:${port}`;
  return {
    server,
    env,
    port,
    origin,
    async close() {
      const closed = once(server, "close");
      server.close();
      server.closeAllConnections();
      await closed;
    },
    async call(path, method = "GET", data, extra = {}) {
      const response = await fetch(origin + "/api" + path, {
        method,
        headers: { origin, "content-type": "application/json", ...extra },
        body: data === undefined ? undefined : JSON.stringify(data),
      });
      return { status: response.status, data: await response.json() };
    },
  };
}
const brief = {
  title: "Local restart fixture",
  brief: "Produce a checked Markdown report for the local restart fixture.",
  max_tokens: 10000,
};
async function job(local) {
  const r = await local.call("/orgs/org_primary/jobs", "POST", brief, {
    "idempotency-key": crypto.randomUUID(),
  });
  assert.equal(r.status, 201, JSON.stringify(r.data));
  return r.data.job;
}
function raw(
  local,
  { headers = {}, method = "GET", path = "/api/session", chunks = [] } = {},
) {
  return new Promise((resolve, reject) => {
    const req = http.request(
      { hostname: "127.0.0.1", port: local.port, method, path, headers },
      (res) => {
        let body = "";
        res.setEncoding("utf8");
        res.on("data", (part) => {
          body += part;
        });
        res.on("end", () => resolve({ status: res.statusCode, body }));
      },
    );
    req.on("error", reject);
    for (const chunk of chunks) req.write(chunk);
    req.end();
  });
}

test("loopback guards reject forged Host, foreign Origin and cross-site reads", async (t) => {
  const local = await start();
  t.after(() => local.close());
  for (const headers of [
    { host: `evil.example:${local.port}` },
    { origin: "https://evil.example" },
    { "sec-fetch-site": "cross-site" },
  ])
    assert.equal((await raw(local, { headers })).status, 403);
  assert.equal((await raw(local)).status, 200);
  assert.equal(
    (await raw(local, { path: "//evil.example/api/session" })).status,
    400,
  );
});

test("localhost alias preserves same-origin writes and forged identity headers cannot change owner", async (t) => {
  const local = await start();
  t.after(() => local.close());
  const session = await local.call("/session", "GET", undefined, {
    "oai-authenticated-user-id": "forged-user",
    "oai-authenticated-user-email": "forged@example.com",
  });
  assert.equal(session.status, 200);
  assert.deepEqual(
    { ...local.env.db.prepare("SELECT subject,email FROM memberships").get() },
    { subject: "local-owner", email: "local-owner@example.com" },
  );
  const result = await raw(local, {
    method: "POST",
    path: "/api/orgs/org_primary/jobs",
    headers: {
      host: `localhost:${local.port}`,
      origin: `http://localhost:${local.port}`,
      "content-type": "application/json",
      "idempotency-key": crypto.randomUUID(),
    },
    chunks: [JSON.stringify(brief)],
  });
  assert.equal(result.status, 201, result.body);
  const denied = await local.call("/session", "GET", undefined, {
    authorization: "Bearer invalid-local-worker",
    "oai-authenticated-user-id": "local-owner",
    "oai-authenticated-user-email": "local-owner@example.com",
  });
  assert.equal(denied.status, 401);
});

test("HTTP adapter rejects declared and chunked oversized bodies before API buffering", async (t) => {
  const local = await start();
  t.after(() => local.close());
  for (const headers of [
    { "content-length": "128001" },
    { "transfer-encoding": "chunked" },
  ]) {
    const r = await raw(local, {
      method: "POST",
      path: "/api/orgs/org_primary/jobs",
      headers: {
        origin: local.origin,
        "content-type": "application/json",
        ...headers,
      },
      chunks: [" ".repeat(128001)],
    });
    assert.equal(r.status, 413);
  }
  assert.equal((await local.call("/health")).status, 200);
});

test("runtime metadata declares local persistence without credentials or paths", async (t) => {
  const local = await start();
  t.after(() => local.close());
  assert.deepEqual((await local.call("/local/runtime")).data, {
    mode: "local",
    persistence: false,
  });
});

test("tasks, worker identity and uploaded artifact survive local server restart", async (t) => {
  const stateDir = mkdtempSync(join(tmpdir(), "aeon-local-restart-"));
  t.after(() => rmSync(stateDir, { recursive: true, force: true }));
  let local = await start({ stateDir });
  try {
    assert.deepEqual((await local.call("/local/runtime")).data, {
      mode: "local",
      persistence: true,
    });
    assert.equal((await local.call("/session")).status, 200);
    const created = await job(local);
    const enrollment = await local.call("/orgs/org_primary/workers", "POST", {
      name: "Persistence fixture",
      mode: "trusted-local",
    });
    assert.equal(enrollment.status, 201);
    const auth = { authorization: `Bearer ${enrollment.data.worker_token}` };
    const claim = (await local.call("/worker/claim", "POST", {}, auth)).data;
    assert.equal(claim.job.id, created.id);
    const content = "Persisted checked artifact\n";
    const upload = await fetch(
      `${local.origin}/api/worker/jobs/${created.id}/artifacts?path=report.md`,
      {
        method: "PUT",
        headers: { ...auth, "x-lease-token": claim.lease_token },
        body: content,
      },
    );
    assert.equal(upload.status, 201, await upload.text());
    assert.equal(
      (
        await local.call(
          `/worker/jobs/${created.id}/finish`,
          "POST",
          {
            lease_token: claim.lease_token,
            result: {
              status: "completed",
              model_tokens: 100,
              audit_valid: true,
              unresolved_gaps: [],
            },
          },
          auth,
        )
      ).status,
      200,
    );
    const artifact = local.env.db
      .prepare("SELECT id,sha256 FROM artifacts WHERE job_id=?")
      .get(created.id);
    await local.close();
    local = await start({ stateDir });
    const restored = await local.call(`/orgs/org_primary/jobs/${created.id}`);
    assert.equal(restored.status, 200);
    assert.equal(restored.data.job.status, "completed");
    const download = await fetch(
      `${local.origin}/api/orgs/org_primary/artifacts/${artifact.id}`,
    );
    assert.equal(download.status, 200);
    assert.equal(await download.text(), content);
    assert.equal(
      (await local.call("/worker/claim", "POST", {}, auth)).status,
      200,
    );
    assert.equal(
      local.env.db
        .prepare("SELECT count(*) AS n FROM __aeon_local_migrations")
        .get().n,
      1,
    );
  } finally {
    await local.close();
  }
});

test("concurrent local submissions honor atomic quota without nested transactions", async (t) => {
  const local = await start();
  t.after(() => local.close());
  await local.call("/session");
  local.env.db.prepare("UPDATE organizations SET daily_jobs=3").run();
  const submissions = await Promise.all(
    Array.from({ length: 8 }, () =>
      local.call("/orgs/org_primary/jobs", "POST", brief, {
        "idempotency-key": crypto.randomUUID(),
      }),
    ),
  );
  assert.equal(submissions.filter((r) => r.status === 201).length, 3);
  assert.equal(submissions.filter((r) => r.status === 429).length, 5);
  assert.equal(
    local.env.db.prepare("SELECT count(*) AS n FROM jobs").get().n,
    3,
  );
});

async function enrollWorker(local, name) {
  const response = await local.call("/orgs/org_primary/workers", "POST", {
    name, mode: "trusted-local",
  });
  assert.equal(response.status, 201, JSON.stringify(response.data));
  return { authorization: `Bearer ${response.data.worker_token}` };
}

test("cancelled HTTP task rejects heartbeat, upload, finish and resume while preserving reservation", async (t) => {
  const local = await start();
  t.after(() => local.close());
  await local.call("/session");
  const created = await job(local);
  const auth = await enrollWorker(local, "Cancellation fixture");
  const claim = (await local.call("/worker/claim", "POST", {}, auth)).data;
  assert.equal(claim.job.id, created.id);
  assert.equal((await local.call(`/orgs/org_primary/jobs/${created.id}/cancel`, "POST", {})).status, 200);
  assert.equal((await local.call(`/worker/jobs/${created.id}/heartbeat`, "POST", { lease_token: claim.lease_token }, auth)).status, 409);
  const upload = await fetch(`${local.origin}/api/worker/jobs/${created.id}/artifacts?path=late.md`, {
    method: "PUT", headers: { ...auth, "x-lease-token": claim.lease_token }, body: "Late artifact",
  });
  assert.equal(upload.status, 409);
  assert.equal((await local.call(`/worker/jobs/${created.id}/finish`, "POST", {
    lease_token: claim.lease_token, result: { status: "partial", model_tokens: 1 },
  }, auth)).status, 409);
  assert.equal((await local.call(`/orgs/org_primary/jobs/${created.id}/resume`, "POST", { additional_steps: 1 })).status, 409);
  assert.equal((await local.call("/orgs/org_primary/dashboard")).data.usage.reserved_tokens, brief.max_tokens);
  assert.equal((await local.call("/worker/claim", "POST", {}, auth)).data.job, null);
  assert.equal(local.env.db.prepare("SELECT count(*) AS n FROM artifacts").get().n, 0);
});

test("expired lease requires explicit recovery on original worker and invalidates stale authority", async (t) => {
  const local = await start();
  t.after(() => local.close());
  await local.call("/session");
  const created = await job(local);
  const original = await enrollWorker(local, "Original fixture worker");
  const claim = (await local.call("/worker/claim", "POST", {}, original)).data;
  const other = await enrollWorker(local, "Other fixture worker");
  local.env.db.prepare("UPDATE jobs SET lease_expires_at=1 WHERE id=?").run(created.id);
  assert.equal((await local.call(`/worker/jobs/${created.id}/heartbeat`, "POST", { lease_token: claim.lease_token }, original)).status, 409);
  assert.equal((await local.call("/worker/claim", "POST", {}, other)).data.job, null);
  assert.equal((await local.call(`/orgs/org_primary/jobs/${created.id}`)).data.job.status, "interrupted");
  assert.equal((await local.call(`/orgs/org_primary/jobs/${created.id}/resume`, "POST", { additional_minutes: 1 })).status, 200);
  assert.equal((await local.call("/worker/claim", "POST", {}, other)).data.job, null);
  const recovered = (await local.call("/worker/claim", "POST", {}, original)).data;
  assert.equal(recovered.job.id, created.id);
  assert.equal(recovered.job.attempts, 2);
  assert.notEqual(recovered.lease_token, claim.lease_token);
  assert.equal((await local.call(`/worker/jobs/${created.id}/heartbeat`, "POST", { lease_token: claim.lease_token }, original)).status, 409);
  assert.equal((await local.call(`/worker/jobs/${created.id}/heartbeat`, "POST", { lease_token: recovered.lease_token }, other)).status, 409);
  assert.equal((await local.call(`/worker/jobs/${created.id}/heartbeat`, "POST", { lease_token: recovered.lease_token }, original)).status, 200);
  assert.equal((await local.call(`/orgs/org_primary/jobs/${created.id}/cancel`, "POST", {}, original)).status, 401);
});

test("cumulative resume limits reject overflow without changing task or audit and allow exact runtime caps", async (t) => {
  const local = await start();
  t.after(() => local.close());
  await local.call("/session");
  for (const [field, option, cap] of [
    ["max_steps", "additional_steps", 200],
    ["max_revisions", "additional_revisions", 20],
    ["deadline_minutes", "additional_minutes", 1440],
  ]) {
    const created = await job(local);
    // A persisted near-cap fixture represents earlier valid explicit resumes.
    local.env.db.prepare(`UPDATE jobs SET status='interrupted',${field}=? WHERE id=?`).run(cap - 1, created.id);
    const before = local.env.db.prepare("SELECT * FROM jobs WHERE id=?").get(created.id);
    const denied = await local.call(`/orgs/org_primary/jobs/${created.id}/resume`, "POST", { [option]: 2 });
    assert.equal(denied.status, 400, JSON.stringify(denied.data));
    assert.deepEqual(local.env.db.prepare("SELECT * FROM jobs WHERE id=?").get(created.id), before);
    assert.equal(local.env.db.prepare("SELECT count(*) AS n FROM audit WHERE action='task.resume_requested' AND target=?").get(created.id).n, 0);
    const boundary = await local.call(`/orgs/org_primary/jobs/${created.id}/resume`, "POST", { [option]: 1 });
    assert.equal(boundary.status, 200, JSON.stringify(boundary.data));
    const saved = local.env.db.prepare("SELECT * FROM jobs WHERE id=?").get(created.id);
    assert.equal(saved[field], cap);
    assert.equal(saved.status, "queued");
  }
});
