# AEON Enterprise control plane 0.4.0

Private operations console: durable organizations, roles, approvals, task reservations,
worker leases, artifact downloads and audit exports. Model execution runs on outbound
workers. Current release targets an owner-private enterprise pilot.

## Development

Requires Node.js 24 (`node:sqlite` in tests). From this directory:

```powershell
npm ci
npm test
npm run build
npm run validate
npm run dev
```

Local preview `http://127.0.0.1:8787` uses a development identity and ephemeral storage.
Never publish `scripts/dev.mjs`. Production entrypoint: `dist/server/index.js`.
Production requires Sites' authenticated dispatcher, D1 and R2. Do not expose this
Worker on a generic platform that accepts arbitrary `oai-authenticated-user-*` headers.

## Production

See [operations guide](../docs/AEON_ENTERPRISE_OPERATIONS.md). Site identity and logical
bindings live in `.openai/hosting.json`; secrets do not. Push exact source through the
Sites workflow, package `dist`, then deploy the saved version. Sites applies generated
Drizzle migrations before upload; applied migrations must remain immutable.

| Runtime value | Purpose |
|---|---|
| `AEON_OWNER_EMAIL` | Restricts first workspace bootstrap |
| `AEON_ADMIN_KEY` | Secret deployment bearer; initial organization only |
| `AEON_SITE_SERVICE_KEY` | Secret dispatcher access for outbound workers |
| `AEON_ALLOW_SPEND` | Absent or `false` disables spending |

Worker enrollment downloads revocable, organization-scoped connection JSON once.
Store outside the checkout with owner-only permissions. Administrator secrets never
enter job subprocesses.

## API

Routes use `/api`. Browser requests use Site authentication; writes require same-origin
`Origin`. Workers send their bearer and `OAI-Sites-Authorization`. Deployment operations
use the separate master bearer. Every organization route enforces membership/role.

| Route | Purpose |
|---|---|
| `GET /health`, `GET /session` | Readiness; accessible organizations |
| `POST /organizations` | Create organization |
| `GET /orgs/:orgId/dashboard` | Queue, usage and worker status |
| `GET/POST /orgs/:orgId/jobs` | List/create; create requires `Idempotency-Key` |
| `GET /orgs/:orgId/jobs/:jobId` | Result and artifact metadata |
| `POST /orgs/:orgId/jobs/:jobId/approve` | Reviewer/owner approval |
| `POST /orgs/:orgId/jobs/:jobId/cancel` | Revoke execution lease |
| `POST /orgs/:orgId/jobs/:jobId/resume` | Explicit checkpoint recovery with limits |
| `POST /orgs/:orgId/workers` | Enroll worker and download connection |
| `POST /orgs/:orgId/workers/:workerId/revoke` | Revoke worker |
| `GET /orgs/:orgId/artifacts/:artifactId` | Authorized attachment download |
| `GET /orgs/:orgId/audit?after=0`, `GET /orgs/:orgId/export` | Audit cursor; owner record export |
| `POST /orgs/:orgId/invitations`, `POST /invitations/accept` | Email-bound 24h invitation |
| `POST /bootstrap` | Deployment-only enrollment |
| `POST /worker/claim` | Atomic claim, 90-second lease |
| `POST /worker/jobs/:jobId/heartbeat` | Renew lease |
| `PUT /worker/jobs/:jobId/artifacts?path=...` | Bounded authorized upload |
| `POST /worker/jobs/:jobId/finish` | Result; identical finish retries safely |

Completion requires reported valid runtime audit, artifacts, no reported gaps and
usage within budget. This is a worker report, not independent factual attestation.
