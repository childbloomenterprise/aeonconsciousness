"""Vercel FastAPI entrypoint.

Vercel routes /api/* to this ASGI application. Route paths intentionally retain
their /api prefix because FastAPI receives the original request path.
"""

import os

# Vercel deployment files are read-only. Alpha retains an ephemeral recovery
# copy in the writable serverless temporary directory; cloud mirroring supplies
# durable storage once the Supabase migration is applied.
if os.environ.get("VERCEL"):
    os.environ.setdefault("AEON_RUNTIME_DIR", "/tmp/aeon-runtime")

from aeon.api.app import app

__all__ = ["app"]
