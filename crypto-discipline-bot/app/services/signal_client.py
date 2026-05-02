from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class SignalClient:
    def __init__(self, base_url: str, timeout_sec: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_sec

    async def _get(self, path: str) -> Any:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}{path}")
            resp.raise_for_status()
            return resp.json()

    async def health(self) -> bool:
        try:
            data = await self._get("/health")
            return isinstance(data, dict) and data.get("status") == "ok"
        except Exception as exc:
            logger.warning("Signal bot health check failed: %s", exc)
            return False

    async def get_active(self) -> list[dict[str, Any]]:
        return await self._get("/signals/active")

    async def scan_now(self) -> list[dict[str, Any]]:
        return await self._get("/signals/scan")

    async def analyze(self, symbol: str) -> dict[str, Any]:
        return await self._get(f"/signal/{symbol}")

    async def get_symbols(self) -> list[str]:
        data = await self._get("/symbols")
        if isinstance(data, dict):
            return list(data.get("symbols") or [])
        return []
