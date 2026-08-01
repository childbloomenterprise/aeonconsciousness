from __future__ import annotations

from typing import Any

import httpx


class SupabaseMirror:
    """Optional cloud mirror. Local storage remains authoritative in Alpha."""

    def __init__(self, url: str, service_key: str, timeout: float = 10.0) -> None:
        self.url = url.rstrip("/")
        self.headers = {
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        }
        self.timeout = timeout

    async def append(self, table: str, record: dict[str, Any]) -> None:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.url}/rest/v1/{table}", headers=self.headers, json=record
            )
            response.raise_for_status()

    async def health_check(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.url}/rest/v1/aeon_events?select=event_id&limit=1", headers=self.headers
            )
            return {"healthy": response.status_code < 500, "status_code": response.status_code}
