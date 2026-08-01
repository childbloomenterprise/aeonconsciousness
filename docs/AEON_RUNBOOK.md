# Runbook

## Local

1. Create virtual environment and install `pip install -e ".[dev]"`.
2. Copy `.env.example` to `.env`; MOCK requires no keys.
3. Run `python -m aeon.api.app`.
4. From `frontend/`, run `npm install` then `npm run dev`.
5. Run tests with `pytest`.

## Claude

Set `AEON_MODEL_PROVIDER=anthropic`, `AEON_MODEL_NAME`, and `ANTHROPIC_API_KEY` in `.env`. Never commit `.env`.

Gemini uses `AEON_MODEL_PROVIDER=gemini` with `GOOGLE_API_KEY`. OpenAI-compatible endpoints use `AEON_MODEL_PROVIDER=openai_compatible`, `OPENAI_COMPATIBLE_BASE_URL`, and `OPENAI_COMPATIBLE_API_KEY`.

## Supabase

Apply `supabase/migrations/001_aeon_alpha.sql` using Supabase tooling. Set URL and service-role key only in backend environment. Alpha continues locally if cloud mirror is unavailable.

Set `AEON_RUNTIME_MODE=hybrid` to mirror signed events while retaining local authority. `cloud` currently retains the same local recovery copy and enables the mirror; it does not make browser code authoritative.

## Vercel

`vercel.json` builds `frontend/` and exposes `api/index.py` as the FastAPI catch-all for `/api/*`. Set backend-only variables in Vercel: `AEON_RUNTIME_MODE`, `AEON_MODEL_PROVIDER`, `ANTHROPIC_API_KEY` where applicable, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY`. Do not set any service-role value as a browser-exposed variable.
