"use strict";
const $ = (s) => document.querySelector(s),
  esc = (v) =>
    String(v ?? "").replace(
      /[&<>"']/g,
      (c) =>
        ({
          "&": "&amp;",
          "<": "&lt;",
          ">": "&gt;",
          '"': "&quot;",
          "'": "&#39;",
        })[c],
    );
const state = {
  session: null,
  org: null,
  dashboard: null,
  jobs: [],
  view: "tasks",
  filter: "all",
};
const label = (s) => String(s).replaceAll("_", " "),
  date = (t) => (t ? new Date(t * 1000).toLocaleString() : "Not connected");
const badge = (s) => `<span class="pill ${esc(s)}">${esc(label(s))}</span>`;
const authRole = () => state.dashboard?.role || "viewer",
  canWork = () => ["owner", "operator"].includes(authRole());
async function call(path, method = "GET", data, extra = {}) {
  const response = await fetch("/api" + path, {
    method,
    headers: {
      ...(data === undefined ? {} : { "content-type": "application/json" }),
      ...extra,
    },
    body: data === undefined ? undefined : JSON.stringify(data),
    credentials: "same-origin",
  });
  const value = await response.json();
  if (!response.ok)
    throw Object.assign(new Error(value.error || "Request failed."), {
      status: response.status,
    });
  return value;
}
const base = () => `/orgs/${encodeURIComponent(state.org)}`;
function notice(message) {
  $("#notice").textContent = message;
  $("#notice").hidden = !message;
}
function modal(title, content) {
  $("#dialog-title").textContent = title;
  $("#dialog-body").innerHTML = content;
  $("#dialog").showModal();
}
function formError(e) {
  let el = $("#form-error");
  if (el) el.textContent = e.message;
  else notice(e.message);
}
function download(name, data) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  );
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
function metric(title, value, note) {
  return `<div class="metric"><div class="metric-label">${esc(title)}</div><strong>${esc(value)}</strong><small>${esc(note)}</small></div>`;
}
async function refresh() {
  if (!state.org) return;
  const [d, j] = await Promise.all([
    call(base() + "/dashboard"),
    call(base() + "/jobs"),
  ]);
  state.dashboard = d;
  state.jobs = j.jobs;
  const total = (s) =>
    d.stats
      .filter((v) => s.includes(v.status))
      .reduce((n, v) => n + v.count, 0);
  $("#metrics").innerHTML =
    metric("Queued", total(["queued"]), "Ready for a connected worker") +
    metric("Running", total(["running"]), "Current worker leases") +
    metric("Completed", total(["completed"]), "Runtime checks passed") +
    metric(
      "Needs attention",
      total(["partial", "failed", "interrupted", "pending_approval"]),
      "Review gaps, approvals, or recovery",
    );
  $("#role").textContent = d.role;
  $("#create").disabled = !canWork();
  $("#approval-count").textContent = total(["pending_approval"]) || "";
  await render();
}
async function render() {
  const titles = {
    tasks: "Work queue",
    approvals: "Approvals",
    workers: "Workers",
    members: "Team & access",
    audit: "Audit history",
  };
  $("#view-title").textContent = titles[state.view];
  document
    .querySelectorAll("[data-view]")
    .forEach((b) =>
      b.classList.toggle("active", b.dataset.view === state.view),
    );
  if (state.view === "tasks" || state.view === "approvals") {
    const jobs = state.jobs.filter((j) =>
      state.view === "approvals"
        ? j.status === "pending_approval"
        : state.filter === "all" || j.status === state.filter,
    );
    const quota = `<div class="quota"><span>Tasks today: ${state.dashboard.usage.jobs} / ${state.dashboard.organization.daily_jobs}</span><span>Tokens reserved / used: ${Number(state.dashboard.usage.reserved_tokens).toLocaleString()} / ${Number(state.dashboard.organization.daily_tokens).toLocaleString()}</span></div>`;
    const filter =
      state.view === "tasks"
        ? `<label><span class="sr-only">Filter tasks</span><select id="filter">${["all", "queued", "running", "completed", "pending_approval", "partial", "interrupted", "failed", "cancelled"].map((s) => `<option value="${s}" ${state.filter === s ? "selected" : ""}>${esc(s === "all" ? "All statuses" : label(s))}</option>`).join("")}</select></label>`
        : "";
    $("#view").innerHTML =
      quota +
      (jobs.length
        ? `<div class="panel"><div class="panel-top"><h2>${state.view === "approvals" ? "External actions awaiting review" : "Recent tasks"}</h2>${filter}</div><table><thead><tr><th>Task</th><th>Status</th><th>Type</th><th>Created</th></tr></thead><tbody>${jobs.map((j) => `<tr data-job="${j.id}" tabindex="0" role="button" aria-label="Open ${esc(j.title)}"><td><strong>${esc(j.title)}</strong><small>${j.id.slice(0, 16)} · ${Number(j.used_tokens || j.progress?.tokens || 0).toLocaleString()} tokens</small></td><td>${badge(j.status)}</td><td>${esc(label(j.kind))}</td><td>${esc(date(j.created_at))}</td></tr>`).join("")}</tbody></table></div>`
        : `<div class="empty"><h2>${state.view === "approvals" ? "No approvals waiting" : state.filter === "all" ? "Your work queue starts here" : "No matching tasks"}</h2><p>${state.view === "approvals" ? "Tasks with external effects appear here before a worker can act." : "Give AEON an outcome, a deadline, and acceptance criteria. Its worker will return artifacts and evidence."}</p>${canWork() ? '<button class="primary" id="empty-create">Create a task</button>' : ""}</div>`);
    $("#filter")?.addEventListener("change", (e) => {
      state.filter = e.target.value;
      render();
    });
    $("#empty-create")?.addEventListener("click", createTask);
    document.querySelectorAll("[data-job]").forEach((row) => {
      row.addEventListener("click", () => openTask(row.dataset.job));
      row.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          openTask(row.dataset.job);
        }
      });
    });
  } else if (state.view === "workers") {
    const w = state.dashboard.workers;
    $("#view").innerHTML =
      `<div class="panel-top"><div><h2>Connected workers</h2><p class="state-note">Long tasks run on your worker. A lost lease requires explicit recovery.</p></div>${authRole() === "owner" ? '<button id="add-worker" class="primary">Enroll worker</button>' : ""}</div><div class="cards">${w.map((x) => `<article class="card"><h2>${esc(x.name)}</h2>${badge(x.revoked ? "revoked" : x.heartbeat_at && Date.now() / 1000 - x.heartbeat_at < 120 ? "online" : "offline")}<p>Execution: ${esc(x.mode)}<br>Last contact: ${esc(date(x.heartbeat_at))}</p><code>${x.id}</code>${authRole() === "owner" && !x.revoked ? `<div class="actions"><button class="danger" data-revoke="${x.id}">Revoke credential</button></div>` : ""}</article>`).join("") || '<div class="empty"><h2>No worker connected</h2><p>Enroll a worker to process approved tasks. Queued work stays saved until one connects.</p></div>'}</div>`;
    $("#add-worker")?.addEventListener("click", enrollWorker);
    document.querySelectorAll("[data-revoke]").forEach(
      (b) =>
        (b.onclick = async () => {
          try {
            await call(
              base() + `/workers/${b.dataset.revoke}/revoke`,
              "POST",
              {},
            );
            await refresh();
          } catch (e) {
            notice(e.message);
          }
        }),
    );
  } else if (state.view === "members") {
    const data = await call(base() + "/members");
    $("#view").innerHTML =
      `<div class="panel"><div class="panel-top"><h2>Workspace members</h2>${authRole() === "owner" ? '<button class="primary" id="invite">Create invitation</button>' : ""}</div><table><thead><tr><th>Member</th><th>Role</th><th>Joined</th></tr></thead><tbody>${data.members.map((m) => `<tr><td>${esc(m.email)}</td><td>${badge(m.role)}</td><td>${esc(date(m.created_at))}</td></tr>`).join("")}</tbody></table></div><p class="hint">Application membership and hosting access both apply. This deployment currently stays private to its owner; invitations do not change that access policy.</p><div class="cards"><article class="card"><h2>Organization</h2><p>${esc(state.dashboard.organization.name)}</p><div class="actions"><button class="secondary" id="new-org">New organization</button>${authRole() === "owner" ? '<button class="secondary" id="export">Export records</button>' : ""}</div></article></div>`;
    $("#invite")?.addEventListener("click", invite);
    $("#new-org").onclick = newOrganization;
    $("#export")?.addEventListener("click", async () => {
      try {
        download("aeon-workspace-export.json", await call(base() + "/export"));
      } catch (e) {
        notice(e.message);
      }
    });
  } else {
    const data = await call(base() + "/audit");
    $("#view").innerHTML =
      `<div class="panel"><div class="panel-top"><h2>Recorded operations</h2><span class="hint">First 200 events · JSON export includes full history</span></div><table><thead><tr><th>Operation</th><th>Actor</th><th>Target</th><th>Time</th></tr></thead><tbody>${data.events.map((e) => `<tr><td><strong>${esc(e.action)}</strong><small>${esc(e.detail)}</small></td><td>${esc(e.actor)}</td><td>${esc(e.target)}</td><td>${esc(date(e.created_at))}</td></tr>`).join("") || '<tr><td colspan="4">No operations recorded yet.</td></tr>'}</tbody></table></div>`;
  }
}
function createTask() {
  modal(
    "Delegate a task",
    `<form id="task-form"><div class="field"><label for="title">Task name</label><input id="title" name="title" required minlength="3" maxlength="120" placeholder="Research supplier options"></div><div class="field"><label for="brief">Outcome and acceptance criteria</label><textarea id="brief" name="brief" required minlength="10" maxlength="12000" rows="6" placeholder="Describe the usable result you need, required sources, audience, and how you will judge success."></textarea></div><div class="columns"><div class="field"><label for="kind">Work type</label><select id="kind" name="kind">${["research", "website", "code", "browser_file", "general"].map((v) => `<option value="${v}">${esc(label(v))}</option>`).join("")}</select></div><div class="field"><label for="tokens">Token ceiling</label><input id="tokens" name="max_tokens" type="number" min="1000" max="50000" value="20000" required></div><div class="field"><label for="deadline">Deadline, minutes</label><input id="deadline" name="deadline_minutes" type="number" min="1" max="90" value="30" required></div></div><details><summary>External action permissions</summary><p class="hint">Default: public reading and task files only. External changes need scoped permission and approval. Spending disabled in this deployment.</p><div class="field"><label for="grant">Grant JSON</label><textarea id="grant" name="grant" rows="5">{"external_actions": [], "browser_write_domains": [], "recipients": [], "max_spend": 0, "currency": "USD"}</textarea></div></details><p class="hint">Subgoals and routine choices come from your brief. Review the finished artifact before using it for business decisions.</p><div id="form-error" class="error" role="alert"></div><div class="form-actions"><button class="primary" type="submit">Queue task</button></div></form>`,
  );
  $("#task-form").onsubmit = async (e) => {
    e.preventDefault();
    const form = new FormData(e.target),
      button = e.target.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      await call(
        base() + "/jobs",
        "POST",
        {
          title: form.get("title"),
          brief: form.get("brief"),
          kind: form.get("kind"),
          max_tokens: Number(form.get("max_tokens")),
          deadline_minutes: Number(form.get("deadline_minutes")),
          grant: JSON.parse(form.get("grant")),
        },
        { "idempotency-key": crypto.randomUUID() },
      );
      $("#dialog").close();
      state.view = "tasks";
      state.filter = "all";
      notice("Task saved. It will start when a matching worker claims it.");
      await refresh();
    } catch (err) {
      formError(err);
      button.disabled = false;
    }
  };
}
async function openTask(jobId) {
  try {
    const { job: j, artifacts } = await call(base() + `/jobs/${jobId}`);
    modal(
      j.title,
      `${badge(j.status)}<div class="section-heading">Assignment</div><div class="detail-text">${esc(j.brief)}</div><div class="section-heading">Limits & execution</div><p class="hint">${j.max_tokens.toLocaleString()} token ceiling · ${j.deadline_minutes} minutes · ${j.attempts} attempt(s)<br>Recorded usage: ${Number(j.used_tokens || j.progress?.tokens || 0).toLocaleString()} tokens · ${esc(j.progress?.phase || "Awaiting worker")}</p>${j.grant.external_actions.length ? `<details><summary>External grant</summary><pre>${esc(JSON.stringify(j.grant, null, 2))}</pre></details>` : ""}<div class="section-heading">Artifacts</div>${artifacts.map((a) => `<a class="artifact" href="/api${base()}/artifacts/${a.id}" download><span>${esc(a.path)}</span><small>${(a.size / 1024).toFixed(1)} KB · download</small></a>`).join("") || '<p class="hint">No artifact uploaded yet.</p>'}${j.result ? `<div class="section-heading">Verified outcome & remaining gaps</div><p class="hint">Runtime audit: ${j.result.audit_valid === true ? "valid" : "not verified"} · ${esc(j.result.reason || j.result.status)}</p><div class="detail-text">${esc((j.result.unresolved_gaps || []).join("\n") || "No unresolved gap reported by runtime.")}</div><details><summary>Decisions and result evidence</summary><pre>${esc(JSON.stringify(j.result, null, 2))}</pre></details>` : ""}<div id="form-error" class="error" role="alert"></div><div class="form-actions">${j.status === "pending_approval" && ["owner", "reviewer"].includes(authRole()) ? '<button class="primary" id="approve">Review approval</button>' : ""}${["interrupted", "partial"].includes(j.status) && canWork() ? '<button class="secondary" id="resume">Resume with limits</button>' : ""}${["queued", "pending_approval", "running", "interrupted"].includes(j.status) && canWork() ? '<button class="danger" id="cancel-task">Cancel task</button>' : ""}</div>`,
    );
    $("#cancel-task")?.addEventListener("click", async () => {
      try {
        await call(base() + `/jobs/${j.id}/cancel`, "POST", {});
        $("#dialog").close();
        notice(
          "Cancellation saved. Running worker stops when its next heartbeat is rejected.",
        );
        await refresh();
      } catch (e) {
        formError(e);
      }
    });
    $("#approve")?.addEventListener("click", () => approve(j));
    $("#resume")?.addEventListener("click", () => resume(j));
  } catch (e) {
    notice(e.message);
  }
}
function approve(j) {
  $("#dialog-body").innerHTML =
    `<form id="approve-form"><p class="hint">Approve only the named domains, recipients, and actions. This approval becomes part of audit history.</p><pre>${esc(JSON.stringify(j.grant, null, 2))}</pre><div class="field"><label for="reason">Approval reason</label><textarea id="reason" minlength="10" maxlength="500" required></textarea></div>${authRole() === "owner" ? '<label class="hint"><input id="override" type="checkbox"> Explicit owner override when approving my own task</label>' : ""}<div id="form-error" class="error" role="alert"></div><div class="form-actions"><button class="primary">Approve scope</button></div></form>`;
  $("#approve-form").onsubmit = async (e) => {
    e.preventDefault();
    try {
      await call(base() + `/jobs/${j.id}/approve`, "POST", {
        reason: $("#reason").value,
        owner_override: $("#override")?.checked || false,
      });
      $("#dialog").close();
      await refresh();
    } catch (e) {
      formError(e);
    }
  };
}
function resume(j) {
  $("#dialog-body").innerHTML =
    `<form id="resume-form"><p class="hint">Resume on the original worker with its saved checkpoint. External effects may already have happened; inspect evidence before retrying.</p><div class="columns"><div class="field"><label for="extra-tokens">Additional tokens</label><input id="extra-tokens" type="number" min="0" max="10000" value="${j.status === "partial" ? 5000 : 0}"></div><div class="field"><label for="extra-steps">Additional steps</label><input id="extra-steps" type="number" min="0" max="20" value="5"></div><div class="field"><label for="extra-minutes">Additional minutes</label><input id="extra-minutes" type="number" min="0" max="30" value="10"></div></div><div id="form-error" class="error" role="alert"></div><div class="form-actions"><button class="primary">Request resume</button></div></form>`;
  $("#resume-form").onsubmit = async (e) => {
    e.preventDefault();
    try {
      await call(base() + `/jobs/${j.id}/resume`, "POST", {
        additional_model_tokens: Number($("#extra-tokens").value),
        additional_steps: Number($("#extra-steps").value),
        additional_minutes: Number($("#extra-minutes").value),
        additional_revisions: 1,
      });
      $("#dialog").close();
      await refresh();
    } catch (e) {
      formError(e);
    }
  };
}
function enrollWorker() {
  modal(
    "Enroll a worker",
    `<form id="worker-form"><div class="field"><label for="worker-name">Worker name</label><input id="worker-name" minlength="2" maxlength="80" required placeholder="Production worker 01"></div><div class="field"><label for="worker-mode">Execution boundary</label><select id="worker-mode"><option value="docker">Docker containers — separate job execution</option><option value="trusted-local">Trusted local — owner machine permissions</option></select><small>Use Docker for organizational work. Trusted local mode is intended for your own private tasks.</small></div><div id="form-error" class="error" role="alert"></div><div class="form-actions"><button class="primary">Create worker credential</button></div></form>`,
  );
  $("#worker-form").onsubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await call(base() + "/workers", "POST", {
        name: $("#worker-name").value,
        mode: $("#worker-mode").value,
      });
      $("#dialog-body").innerHTML =
        '<p>Credential generated. Download it now; worker token cannot be retrieved later.</p><p class="hint">Keep this file private. Use the worker installation instructions in GitHub.</p><button id="download-connection" class="primary">Download connection file</button>';
      $("#download-connection").onclick = () =>
        download(
          "aeon-worker-connection.json",
          r.connection || { ...r, base_url: location.origin },
        );
      await refresh();
    } catch (e) {
      formError(e);
    }
  };
}
function invite() {
  modal(
    "Invite a team member",
    `<form id="invite-form"><div class="field"><label for="email">Email bound to ChatGPT sign-in</label><input id="email" type="email" required></div><div class="field"><label for="member-role">Role</label><select id="member-role"><option value="viewer">Viewer — read results and evidence</option><option value="operator">Operator — delegate and recover tasks</option><option value="reviewer">Reviewer — approve external scopes</option></select></div><p class="hint">Invitation lasts 24 hours. Hosting access must also allow this visitor. No message will be sent automatically.</p><div id="form-error" class="error" role="alert"></div><div class="form-actions"><button class="primary">Create invitation link</button></div></form>`,
  );
  $("#invite-form").onsubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await call(base() + "/invitations", "POST", {
        email: $("#email").value,
        role: $("#member-role").value,
      });
      $("#dialog-body").innerHTML =
        `<p>Share this invitation with the intended member.</p><div class="field"><label for="invite-link">Invitation link</label><input id="invite-link" readonly value="${esc(r.invite_url)}"></div><p class="hint">Expires ${esc(date(r.expires_at))}. Current hosting audience remains unchanged.</p>`;
    } catch (e) {
      formError(e);
    }
  };
}
function newOrganization() {
  modal(
    "Create organization",
    `<form id="org-form"><div class="field"><label for="org-name">Organization name</label><input id="org-name" required minlength="3" maxlength="80"></div><div id="form-error" class="error" role="alert"></div><div class="form-actions"><button class="primary">Create organization</button></div></form>`,
  );
  $("#org-form").onsubmit = async (e) => {
    e.preventDefault();
    try {
      const r = await call("/organizations", "POST", {
        name: $("#org-name").value,
      });
      $("#dialog").close();
      await initialize(r.id);
    } catch (e) {
      formError(e);
    }
  };
}
async function initialize(selected) {
  try {
    const inviteKey = new URL(location.href).searchParams.get("invite");
    if (inviteKey) {
      await call("/invitations/accept", "POST", { token: inviteKey });
      history.replaceState(null, "", "/");
    }
    state.session = await call("/session");
    state.org = selected || state.session.organizations[0].id;
    $("#org").innerHTML = state.session.organizations
      .map((o) => `<option value="${o.id}">${esc(o.name)}</option>`)
      .join("");
    $("#org").value = state.org;
    $("#org").disabled = false;
    $("#account").textContent = state.session.email;
    await refresh();
  } catch (e) {
    $("#view").innerHTML =
      `<div class="error-page"><h2>${e.status === 401 ? "Sign in to your workspace" : "Workspace unavailable"}</h2><p>${esc(e.message)}</p>${e.status === 401 ? '<a class="sign-in" href="/signin-with-chatgpt?return_to=/" target="_top">Sign in with ChatGPT</a>' : '<button class="secondary" id="retry-load">Retry</button>'}</div>`;
    $("#retry-load")?.addEventListener("click", () => initialize());
    $("#account").textContent = "Not connected";
  }
}
$("#close").onclick = () => $("#dialog").close();
$("#create").onclick = createTask;
$("#refresh").onclick = () => refresh().catch((e) => notice(e.message));
$("#org").onchange = (e) => {
  state.org = e.target.value;
  notice("");
  refresh().catch((e) => notice(e.message));
};
document.querySelectorAll("[data-view]").forEach(
  (b) =>
    (b.onclick = () => {
      state.view = b.dataset.view;
      render().catch((e) => notice(e.message));
    }),
);
initialize();
setInterval(() => {
  if (state.org && !$("#dialog").open)
    refresh().catch((e) => notice(e.message));
}, 10000);
