"""Vercel FastAPI entrypoint.

Vercel routes /api/* to this ASGI application. Route paths intentionally retain
their /api prefix because FastAPI receives the original request path.
"""

from aeon.api.app import app

__all__ = ["app"]

