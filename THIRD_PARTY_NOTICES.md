# Third-party notices

## Enterprise control-plane dependencies

External npm packages: Hono (MIT), Zod (MIT), Drizzle ORM/Kit (Apache-2.0),
esbuild (MIT) and Prettier (MIT). Exact versions recorded in
`enterprise/package-lock.json`; upstream packages retain their own notices.
Enterprise application code is original AEON integration code. Cloudflare D1/R2
and authenticated Sites hosting provide managed infrastructure, not vendored code.

## Hermes Agent

This framework derives architectural patterns from the locally installed
NousResearch Hermes Agent source:

- Local source inspected: `C:\Users\vaish\AppData\Local\hermes\hermes-agent`
- Installed distribution: `hermes-agent 0.18.0`
- Inspected commit: `605727e3`
- Upstream: https://github.com/NousResearch/hermes-agent
- License: MIT

Hermes Agent copyright © 2025 Nous Research.

The complete upstream MIT license text appears in
`third_party/hermes-agent-LICENSE`.

## AI2-THOR

The optional AEON world runtime integrates with AI2-THOR as an external Python
dependency:

- Copyright Allen Institute for AI
- Source: https://github.com/allenai/ai2thor
- License: Apache License 2.0

AI2-THOR and its Unity scene builds are not vendored in this repository.

## OpenAI Codex

AEON's opt-in structured-inference backend invokes the installed Codex CLI;
Codex remains an external runtime, rather than a copied implementation.

- Upstream: https://github.com/openai/codex
- Source inspected: `a933dd77dbe101d7bd746ea3c7d1f8174eca4a05`
- License: Apache-2.0; full text in `third_party/codex-LICENSE`
- Protocol guidance: https://developers.openai.com/codex/noninteractive
- AEON adapter: `aeon_worker/codex_provider.py`, original integration code.

## NVIDIA NeMo Agent Toolkit

Optional external dependency: `nvidia-nat-core==1.9.0`. AEON uses its function
registration and workflow APIs to expose the existing worker as a toolkit
workflow. Toolkit registration boilerplate adapts the official example;
the task runtime and authority checks remain AEON code.

- Upstream: https://github.com/NVIDIA/NeMo-Agent-Toolkit
- Source inspected: `c7e1162a1c7ff18bbd797e090a56cad97c281c92`
- Example: `examples/getting_started/simple_web_query/src/nat_simple_web_query/register.py`
- NVIDIA copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
- License: Apache-2.0; full text in `third_party/nemo-agent-toolkit-LICENSE`
- No upstream implementation files are vendored. Installed dependencies retain
  their own distribution notices and licenses.

## Microsoft Playwright

AEON uses Playwright as an external browser dependency (deployment pin 1.63.0).
Container deployment additionally redistributes its unchanged Docker seccomp
profile, copied from the official version-tagged source:

- Upstream: https://github.com/microsoft/playwright
- Profile: https://github.com/microsoft/playwright/blob/v1.63.0/utils/docker/seccomp_profile.json
- SHA256: `cc3e61cabda6bbc1e53e54d27ba4d55a9d3be829b6dd1a596f4a7b31b1cc7849`
- Copyright Microsoft Corporation.
- License: Apache-2.0; upstream text in `third_party/playwright-LICENSE`.
- Distributed file: `deployment/seccomp_profile.json`; no implementation source
  from Playwright is vendored in AEON's Python runtime.
