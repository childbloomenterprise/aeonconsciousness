# AEON Enterprise 0.4.0 — release record

Date: 4 October 2026. Initial release boundary: owner-private enterprise pilot.

7 October continuation: [worker runtime repair and fresh live acceptance](AEON_ENTERPRISE_WORKER_REPAIR_2026_10_07.md).

## Implemented

- Hosted control-plane source with organization roles, email-bound invitations,
  approvals, budgets, durable queue and audit exports.
- Revocable outbound worker credentials, atomic claims, cancellation, checkpoint
  recovery and idempotent finish requests.
- Real AEON runtime bridge, open-format deliverables, bounded artifact storage,
  SHA-256 metadata and safe attachment downloads.
- Responsive operations console, production Worker bundle, D1 schema migrations,
  Docker job image and Windows supervisor launcher.
- Python SDK/CLI and optional NVIDIA toolkit/Codex integration from the prior worker.
- GitHub CI with Python tests, Node tests, production dependency audit, bundle
  validation and the HTTP-to-worker-to-download fixture.

## Observed checks

| Check | Observed result |
|---|---|
| Python regression suite | 176 passed |
| Control-plane SQL/security tests | 19 passed |
| Desktop/mobile UI | Create, detail, cancel, navigation; no horizontal page overflow or page errors |
| Installed 0.4.0 wheel | Built, installed; enterprise CLI bridge available |
| Local HTTP integration | Completed; 3 artifacts; downloaded hashes match; runtime audit valid |
| Bundle | Valid ESM `default.fetch`; storage bindings corrected to `DB`/`BUCKET` strings |
| Configured credential scan | No configured model/admin secret values in staged source |
| Docker execution | Not run; current host has no Docker daemon |
| Production npm audit | Zero production dependency vulnerabilities; local and Linux CI checks passed |
| Production hosting | Published successfully; private authenticated Site, D1 and R2 ready |

The HTTP fixture used `deterministic-no-model` and local SQLite/in-memory R2. It
demonstrates integration, not hosted persistence, live model quality or superiority.
Live acceptance also completed with Gemini `gemini-3.5-flash-lite`: 6 steps, 16,161 tokens, valid runtime audit, no reported gaps. The inventory assignment produced 5 hosted artifacts. Independent download checks confirmed all SHA-256 hashes, line totals, total quantity 6 and grand total USD 73.50. This is one task, not a general success-rate estimate.

Live URL: https://aeon-enterprise.childbloomenterprise.chatgpt.site

Site source commit: `a89f3e7fccd7473793c2ef430f3015b92d2d3bd2`. Deployment: `appgdep_6ac1fbbb83a8819191b8e6691e581ee5`. Saved version: `appgprj_6ac1f2adde588191be4ed9a554cbdf7c~appgver_330329436704819182da59a2b4794f3d`. GitHub enterprise source matches the deployed source across all 22 tracked files. Owner-private Windows worker started in the background; computer must remain awake and online. Connection/model secrets remain in an owner-restricted directory outside Git.

## Known rollout limitations

Trusted-local execution has host account permissions. Docker networking has no
egress proxy. Customer SSO/SCIM, provider-key vault, autoscaling, tested backup restore,
retention controls, independent security review and SLOs remain open. Current access
policy stays owner-private. See [operations guide](AEON_ENTERPRISE_OPERATIONS.md).
