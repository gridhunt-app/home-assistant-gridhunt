"""The Gridhunt integration."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol
from homeassistant.components import frontend, webhook as ha_webhook
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_integration
from homeassistant.helpers.typing import ConfigType

from . import webhooks
from .api import GridhuntClient
from .const import (
    CARD_FILE,
    CONF_BASE_URL,
    CONF_TOKEN,
    CONF_WEBHOOK_ID,
    DOMAIN,
    LOGGER,
    SERVICE_REFRESH,
    STATIC_URL,
)
from .coordinator import GridhuntConfigEntry, GridhuntCoordinator, GridhuntRuntime
from .ext import load_extensions
from .ws import async_register_websocket

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.DEVICE_TRACKER]
WWW_DIR = Path(__file__).parent / "www"

REFRESH_SCHEMA = vol.Schema({vol.Optional("entry_id"): cv.string})


def get_extensions(hass: HomeAssistant) -> list:
    """Extension modules found at startup."""
    return hass.data.get(DOMAIN, {}).get("extensions", [])


def get_coordinator(hass: HomeAssistant, entry_id: str | None = None) -> GridhuntCoordinator:
    """Coordinator of the given (or first) loaded entry."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if entry_id is not None:
        entries = [e for e in entries if e.entry_id == entry_id]
    if not entries:
        raise ServiceValidationError("No loaded Gridhunt account")
    return entries[0].runtime_data.coordinator


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Once per HA instance: frontend files, websocket commands, services."""
    extensions = await hass.async_add_executor_job(load_extensions)
    hass.data[DOMAIN] = {"extensions": extensions}

    integration = await async_get_integration(hass, DOMAIN)
    card = WWW_DIR / CARD_FILE
    if hass.http is not None and WWW_DIR.is_dir():
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(WWW_DIR), True)]
        )
        if card.is_file():
            frontend.add_extra_js_url(hass, f"{STATIC_URL}/{CARD_FILE}?v={integration.version}")

    async_register_websocket(hass)

    async def _refresh(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id")
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if entry_id is not None:
            entries = [e for e in entries if e.entry_id == entry_id]
            if not entries:
                raise ServiceValidationError("Unknown entry_id")
        for entry in entries:
            coordinator = entry.runtime_data.coordinator
            coordinator.force_refresh_all()
            await coordinator.async_refresh()

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, _refresh, schema=REFRESH_SCHEMA)

    for ext in extensions:
        if hook := getattr(ext, "async_setup", None):
            await hook(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: GridhuntConfigEntry) -> bool:
    """Set up one Gridhunt account."""
    client = GridhuntClient(
        async_get_clientsession(hass), entry.data[CONF_BASE_URL], entry.data[CONF_TOKEN]
    )
    coordinator = GridhuntCoordinator(hass, entry, client, get_extensions(hass))
    await coordinator.async_config_entry_first_refresh()

    webhook_id = entry.data.get(CONF_WEBHOOK_ID)
    if not webhook_id:
        webhook_id = ha_webhook.async_generate_id()
        hass.config_entries.async_update_entry(
            entry, data={**entry.data, CONF_WEBHOOK_ID: webhook_id}
        )
    entry.runtime_data = GridhuntRuntime(client, coordinator, webhook_id)

    for ext in coordinator.extensions:
        if hook := getattr(ext, "async_setup_entry", None):
            await hook(hass, coordinator)

    webhooks.async_register_handler(hass, entry, webhook_id)
    await webhooks.async_register_remote(hass, entry, client, webhook_id)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GridhuntConfigEntry) -> bool:
    """Unload an account."""
    runtime = entry.runtime_data
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await webhooks.async_unregister(hass, runtime.client, runtime.webhook_id)
        for ext in runtime.coordinator.extensions:
            if hook := getattr(ext, "async_unload_entry", None):
                await hook(hass, runtime.coordinator)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: GridhuntConfigEntry) -> None:
    """Clean up a cloudhook when the account is removed."""
    await webhooks.async_delete_cloudhook(hass, entry)
