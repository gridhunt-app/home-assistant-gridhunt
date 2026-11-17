"""Small async client for the Gridhunt Home Assistant API (/api/ha/*)."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import aiohttp

from .const import PAIR_NAME

TIMEOUT = aiohttp.ClientTimeout(total=20)


class GridhuntError(Exception):
    """Base error."""


class AuthError(GridhuntError):
    """Token missing or revoked (the server answers 404 for both)."""


class ScopeError(GridhuntError):
    """The token lacks the required scope (403)."""


class ApiError(GridhuntError):
    """Any other API or network failure."""

    def __init__(
        self, message: str, *, status: int | None = None, code: str | None = None
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code


class NotFoundError(ApiError):
    """404 on an endpoint where it does not mean a bad token."""


def account_id_of(me: dict[str, Any]) -> str | None:
    """Stable opaque account key from /api/ha/me (``accountKey``), None on servers that do not send it yet."""
    value = me.get("accountKey") if isinstance(me, dict) else None
    return value if isinstance(value, str) and value else None


class GridhuntClient:
    """Thin wrapper over aiohttp."""

    def __init__(
        self, session: aiohttp.ClientSession, base_url: str, token: str | None = None
    ) -> None:
        self._session = session
        self.base_url = base_url.rstrip("/")
        self._token = token

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        auth_404: bool = True,
    ) -> Any:
        """Call the API and map errors to exceptions."""
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        try:
            async with self._session.request(
                method,
                f"{self.base_url}{path}",
                headers=headers,
                json=json,
                timeout=TIMEOUT,
            ) as resp:
                try:
                    body = await resp.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError):
                    body = None
                status = resp.status
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ApiError(f"Cannot reach Gridhunt: {err}", code="cannot_connect") from err

        if status < 400:
            return body
        code = body.get("error") if isinstance(body, dict) else None
        if status == 404 and auth_404:
            raise AuthError("Token rejected (404)")
        if status == 404:
            raise NotFoundError("Not found", status=404, code=code)
        if status == 403:
            raise ScopeError(code or "insufficient_scope")
        raise ApiError(f"HTTP {status}", status=status, code=code)

    # --- authenticated reads -------------------------------------------------
    async def me(self) -> dict[str, Any]:
        return await self.request("GET", "/api/ha/me") or {}

    async def state(self) -> dict[str, Any]:
        return await self.request("GET", "/api/ha/state") or {}

    async def live(self) -> dict[str, Any]:
        return await self.request("GET", "/api/ha/live") or {}

    async def stats(self) -> dict[str, Any]:
        return await self.request("GET", "/api/ha/stats") or {}

    async def tiles(self) -> dict[str, Any]:
        """Tile map for the idle card (z14 tiles in view, current square, active target)."""
        return (
            await self.request("GET", "/api/ha/tiles", auth_404=False) or {}
        )

    async def routes(self) -> list[dict[str, Any]]:
        body = await self.request("GET", "/api/ha/routes") or {}
        return list(body.get("routes") or [])

    async def route(self, route_id: str) -> dict[str, Any]:
        return (
            await self.request("GET", f"/api/ha/routes/{quote(route_id, safe='')}", auth_404=False) or {}
        )

    # --- webhook -------------------------------------------------------------
    async def put_webhook(self, url: str) -> dict[str, Any]:
        return await self.request("PUT", "/api/ha/webhook", json={"url": url}) or {}

    async def delete_webhook(self) -> None:
        await self.request("DELETE", "/api/ha/webhook")

    # --- pairing (no token) --------------------------------------------------
    async def pair_start(self, name: str = PAIR_NAME) -> dict[str, Any]:
        return await self.request(
            "POST", "/api/ha/pair", json={"name": name}, auth_404=False
        ) or {}

    async def pair_poll(self, device_code: str) -> dict[str, Any]:
        return await self.request(
            "POST", "/api/ha/pair/poll", json={"deviceCode": device_code}, auth_404=False
        ) or {}
