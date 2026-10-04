# AEON Enterprise 0.4.0 — release record

Date: 4 October 2026. Initial release boundary: owner-private enterprise pilot.

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
| Production npm audit | Local check blocked by registry DNS; CI gate configured |
| Production hosting | Pending; hosting connector HTTP transport unavailable |

The HTTP fixture used `deterministic-no-model` and local SQLite/in-memory R2. It
demonstrates integration, not hosted persistence, live model quality or superiority.
Hosting provisioning and actual live task execution still need verification after
connectivity recovers. No URL is certified live by this record.

## Known rollout limitations

Trusted-local execution has host account permissions. Docker networking has no
egress proxy. Customer SSO/SCIM, provider-key vault, autoscaling, tested backup restore,
retention controls, independent security review and SLOs remain open. Current access
policy stays owner-private. See [operations guide](AEON_ENTERPRISE_OPERATIONS.md).
