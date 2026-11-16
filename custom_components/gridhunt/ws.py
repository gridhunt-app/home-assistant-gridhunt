"""Websocket API used by the Lovelace card."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant

from .api import ApiError, AuthError, ScopeError
from .const import DOMAIN
from .coordinator import GridhuntCoordinator


def _find(hass: HomeAssistant, entry_id: str | None) -> GridhuntCoordinator | None:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if entry_id is not None:
        entries = [e for e in entries if e.entry_id == entry_id]
    return entries[0].runtime_data.coordinator if entries else None


async def build_card_payload(coordinator: GridhuntCoordinator) -> dict[str, Any]:
    """Everything the card needs in one object."""
    live = await coordinator.async_fetch_live()
    data = coordinator.data
    payload: dict[str, Any] = {
        "entry_id": coordinator.config_entry.entry_id,
        "features": data.features,
        "me": data.me,
        "state": data.state,
        "live": live,
        "stats": data.stats,
        "routes": data.routes,
        "tiles": None if data.riding else await coordinator.async_fetch_tiles(),
    }
    for ext in coordinator.extensions:
        if hook := getattr(ext, "card_payload", None):
            payload.update(hook(coordinator))
    return payload


@websocket_api.websocket_command(
    {vol.Required("type"): "gridhunt/card", vol.Optional("entry_id"): str}
)
@websocket_api.async_response
async def ws_card(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    coordinator = _find(hass, msg.get("entry_id"))
    if coordinator is None or coordinator.data is None:
        connection.send_error(msg["id"], "not_found", "No Gridhunt account loaded")
        return
    connection.send_result(msg["id"], await build_card_payload(coordinator))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "gridhunt/route",
        vol.Required("route_id"): str,
        vol.Optional("entry_id"): str,
    }
)
@websocket_api.async_response
async def ws_route(hass: HomeAssistant, connection, msg: dict[str, Any]) -> None:
    coordinator = _find(hass, msg.get("entry_id"))
    if coordinator is None:
        connection.send_error(msg["id"], "not_found", "No Gridhunt account loaded")
        return
    try:
        result = await coordinator.client.route(msg["route_id"])
    except AuthError as err:
        connection.send_error(msg["id"], "unauthorized", str(err))
    except ScopeError as err:
        connection.send_error(msg["id"], "forbidden", str(err))
    except ApiError as err:
        connection.send_error(msg["id"], "not_found" if err.status == 404 else "api_error", str(err))
    else:
        connection.send_result(msg["id"], result)


def async_register_websocket(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_card)
    websocket_api.async_register_command(hass, ws_route)
