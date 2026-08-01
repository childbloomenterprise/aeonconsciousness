# AEON Research Core Alpha

AEON Alpha is a locally runnable research instrument for persistent, observable cognitive architecture. It does not claim phenomenal consciousness.

## Quick start

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m aeon.api.app
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Dashboard: `http://localhost:5173` · API: `http://localhost:8000/docs`

## Vercel

Vercel serves the Vite dashboard plus `api/index.py`, a FastAPI catch-all for
`/api/*`. Configure server-side environment variables in Vercel before enabling
Claude or Supabase cloud mirroring. Apply the Supabase SQL migration before
setting `AEON_RUNTIME_MODE=hybrid` or `cloud`.

MOCK mode works without external keys. Copy `.env.example` to `.env` to configure Claude or Supabase. Runtime data stays under `runtime/` and is excluded from Git.

Scientific status: **phenomenal consciousness UNKNOWN**.
