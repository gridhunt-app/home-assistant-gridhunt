"""Diagnostics with secrets removed."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_TOKEN, CONF_WEBHOOK_ID, CONF_WEBHOOK_SECRET, CONF_WEBHOOK_URL
from .coordinator import GridhuntConfigEntry

TO_REDACT = {
    CONF_TOKEN,
    CONF_WEBHOOK_ID,
    CONF_WEBHOOK_SECRET,
    CONF_WEBHOOK_URL,
    "email",
    "name",
    "title",
    "unique_id",
    "liveUrl",
    "kioskUrl",
    "stateUrl",
    "position",
    "lat",
    "lon",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GridhuntConfigEntry
) -> dict[str, Any]:
    """Entry data, options and the last coordinator snapshot, redacted."""
    coordinator = entry.runtime_data.coordinator
    data = coordinator.data
    return {
        "entry": async_redact_data(
            {
                "title": entry.title,
                "unique_id": entry.unique_id,
                "version": entry.version,
                "data": dict(entry.data),
                "options": dict(entry.options),
            },
            TO_REDACT,
        ),
        "push_active": coordinator.push_active,
        "update_interval_s": coordinator.update_interval.total_seconds()
        if coordinator.update_interval
        else None,
        "last_update_success": coordinator.last_update_success,
        "me": async_redact_data(data.me, TO_REDACT) if data else None,
        "state": async_redact_data(data.state, TO_REDACT) if data else None,
        "features": data.features if data else None,
    }
