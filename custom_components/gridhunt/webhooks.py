"""Webhook receiver and registration."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any

from aiohttp import web
from homeassistant.components import webhook as ha_webhook
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.network import NoURLAvailableError

from .api import ApiError, AuthError, GridhuntClient, ScopeError
from .const import (
    CONF_CLOUDHOOK,
    CONF_WEBHOOK_SECRET,
    CONF_WEBHOOK_URL,
    DOMAIN,
    LOGGER,
    SIGNATURE_HEADER,
    SIGNATURE_TOLERANCE,
)
from .coordinator import GridhuntConfigEntry, GridhuntCoordinator


def verify_signature(
    secret: str,
    header: str | None,
    body: bytes,
    *,
    now: float | None = None,
    tolerance: int = SIGNATURE_TOLERANCE,
) -> bool:
    """Check ``t=<unix>,v1=<hex>`` = HMAC-SHA256(secret, "<t>.<body>")."""
    if not secret or not header:
        return False
    parts: dict[str, list[str]] = {}
    for item in header.split(","):
        key, _, value = item.strip().partition("=")
        parts.setdefault(key, []).append(value)
    try:
        timestamp = int(parts.get("t", [""])[0])
    except ValueError:
        return False
    if abs((time.time() if now is None else now) - timestamp) > tolerance:
        return False
    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()
    return any(hmac.compare_digest(expected, sig) for sig in parts.get("v1", []))


def sign(secret: str, body: bytes, timestamp: int | None = None) -> str:
    """Build a signature header (used by tests and tooling)."""
    t = int(time.time()) if timestamp is None else timestamp
    mac = hmac.new(secret.encode(), f"{t}.".encode() + body, hashlib.sha256).hexdigest()
    return f"t={t},v1={mac}"


def async_register_handler(
    hass: HomeAssistant, entry: GridhuntConfigEntry, webhook_id: str
) -> None:
    """Register the receiving endpoint for this entry."""

    async def _handle(hass: HomeAssistant, _id: str, request: web.Request) -> web.Response:
        # Nabu Casa (cloudhook) podaje MockRequest bez read(); text() mają oba typy żądań, JSON jest w UTF-8
        body = (await request.text()).encode()
        secret = entry.data.get(CONF_WEBHOOK_SECRET, "")
        if not verify_signature(secret, request.headers.get(SIGNATURE_HEADER), body):
            return web.Response(status=401, text="bad signature")
        try:
            payload = json.loads(body)
        except ValueError:
            return web.Response(status=400, text="bad json")
        if not isinstance(payload, dict):
            return web.Response(status=400, text="bad payload")
        event = str(payload.get("event") or request.headers.get("X-Gridhunt-Event") or "")
        coordinator = entry.runtime_data.coordinator
        coordinator.async_handle_event(event, payload, "webhook")
        hass.async_create_task(coordinator.async_request_refresh())
        return web.Response(status=200, text="ok")

    ha_webhook.async_register(
        hass, DOMAIN, "Gridhunt", webhook_id, _handle, allowed_methods=["POST"]
    )


async def _resolve_url(hass: HomeAssistant, webhook_id: str) -> tuple[str, bool] | None:
    """Return (url, is_cloudhook) or None when no reachable https address exists."""
    if "cloud" in hass.config.components:
        try:
            from homeassistant.components import cloud  # noqa: PLC0415

            if cloud.async_active_subscription(hass):
                url = await cloud.async_get_or_create_cloudhook(hass, webhook_id)
                return url, True
        except (HomeAssistantError, KeyError, AttributeError) as err:
            LOGGER.debug("Cloudhook unavailable: %s", err)
    try:
        url = ha_webhook.async_generate_url(
            hass, webhook_id, allow_internal=False, allow_external=True
        )
    except NoURLAvailableError:
        return None
    return (url, False) if url.startswith("https://") else None


async def async_register_remote(
    hass: HomeAssistant, entry: GridhuntConfigEntry, client: GridhuntClient, webhook_id: str
) -> bool:
    """Tell Gridhunt where to POST. Returns True when registered (best effort)."""
    resolved = await _resolve_url(hass, webhook_id)
    if resolved is None:
        LOGGER.info("No external https URL for a webhook; relying on polling")
        return False
    url, is_cloud = resolved
    try:
        result: dict[str, Any] = await client.put_webhook(url)
    except (ApiError, ScopeError, AuthError) as err:
        LOGGER.warning("Could not register webhook with Gridhunt: %s", err)
        return False
    secret = result.get("secret")
    if not secret:
        return False
    hass.config_entries.async_update_entry(
        entry,
        data={
            **entry.data,
            CONF_WEBHOOK_SECRET: secret,
            CONF_WEBHOOK_URL: url,
            CONF_CLOUDHOOK: is_cloud,
        },
    )
    return True


async def async_unregister(
    hass: HomeAssistant, client: GridhuntClient, webhook_id: str
) -> None:
    """Remove the local handler and (best effort) the server-side URL."""
    ha_webhook.async_unregister(hass, webhook_id)
    try:
        await client.delete_webhook()
    except (ApiError, ScopeError, AuthError) as err:
        LOGGER.debug("Could not delete webhook on server: %s", err)


async def async_delete_cloudhook(hass: HomeAssistant, entry: GridhuntConfigEntry) -> None:
    """Drop the cloudhook when the entry is removed for good."""
    if not entry.data.get(CONF_CLOUDHOOK):
        return
    try:
        from homeassistant.components import cloud  # noqa: PLC0415

        await cloud.async_delete_cloudhook(hass, entry.data["webhook_id"])
    except (HomeAssistantError, KeyError, AttributeError):
        pass
