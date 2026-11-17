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
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.loader import async_get_integration
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import slugify

from . import panel, webhooks
from .api import GridhuntClient, GridhuntError, account_id_of
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
from .entity import device_name
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
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="no_account"
        )
    return entries[0].runtime_data.coordinator


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Once per HA instance: frontend files, websocket commands, services."""
    def _scan() -> tuple[list, bool, bool]:
        # all blocking file-system work in one executor job (no I/O on the event loop)
        return load_extensions(), WWW_DIR.is_dir(), (WWW_DIR / CARD_FILE).is_file()

    extensions, www_exists, card_exists = await hass.async_add_executor_job(_scan)
    hass.data[DOMAIN] = {"extensions": extensions}

    integration = await async_get_integration(hass, DOMAIN)
    if hass.http is not None and www_exists:
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(WWW_DIR), True)]
        )
        card_url = f"{STATIC_URL}/{CARD_FILE}?v={integration.version}"
        # sidebar panel module = the card file (defines gridhunt-panel and the gridhunt:mark icon)
        hass.data[DOMAIN]["card_url"] = card_url
        if card_exists:
            hass.data[DOMAIN]["card_file"] = True
            frontend.add_extra_js_url(hass, card_url)

    async_register_websocket(hass)

    async def _refresh(call: ServiceCall) -> None:
        entry_id = call.data.get("entry_id")
        entries = hass.config_entries.async_loaded_entries(DOMAIN)
        if entry_id is not None:
            entries = [e for e in entries if e.entry_id == entry_id]
            if not entries:
                raise ServiceValidationError(
                    translation_domain=DOMAIN, translation_key="unknown_entry"
                )
        for entry in entries:
            coordinator = entry.runtime_data.coordinator
            coordinator.force_refresh_all()
            await coordinator.async_refresh()

    hass.services.async_register(DOMAIN, SERVICE_REFRESH, _refresh, schema=REFRESH_SCHEMA)

    for ext in extensions:
        if hook := getattr(ext, "async_setup", None):
            await hook(hass)
    return True


def _migrate_entity_ids(hass: HomeAssistant, entry: GridhuntConfigEntry) -> None:
    """v1 -> v2: the device was named after the account ("Rafał Wasil" -> sensor.rafal_wasil_tiles).

    Now it is "Gridhunt" (sensor.gridhunt_tiles). Only ids still in their default form (account slug prefix) are
    renamed and only when the target id is free; ids the user renamed stay. The device name follows DeviceInfo on
    setup; a name set by the user (name_by_user) is kept by Home Assistant.
    """
    old = slugify(entry.title or "")
    new = slugify(device_name(hass, entry))
    if not old or old == new:
        return
    reg = er.async_get(hass)
    for ent in er.async_entries_for_config_entry(reg, entry.entry_id):
        domain, obj = ent.entity_id.split(".", 1)
        if obj == old:
            rest = ""
        elif obj.startswith(old + "_"):
            rest = obj[len(old) :]
        else:
            continue
        target = f"{domain}.{new}{rest}"
        if reg.async_is_registered(target) or hass.states.get(target) is not None:
            LOGGER.info("Gridhunt: %s kept, %s is taken", ent.entity_id, target)
            continue
        reg.async_update_entity(ent.entity_id, new_entity_id=target)
    dev_reg = dr.async_get(hass)
    for dev in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if (DOMAIN, entry.entry_id) in dev.identifiers and not dev.name_by_user:
            dev_reg.async_update_device(dev.id, name=device_name(hass, entry))


async def async_migrate_entry(hass: HomeAssistant, entry: GridhuntConfigEntry) -> bool:
    """Config entry migrations."""
    if entry.version > 3:
        return False
    if entry.version == 1:
        _migrate_entity_ids(hass, entry)
        hass.config_entries.async_update_entry(entry, version=2)
    if entry.version == 2:
        # v2 -> v3: unique_id = hash of the token -> stable account id (from /api/ha/me).
        # Best effort here; setup retries it once the first refresh has the account id.
        try:
            client = GridhuntClient(
                async_get_clientsession(hass), entry.data[CONF_BASE_URL], entry.data[CONF_TOKEN]
            )
            _adopt_account_id(hass, entry, await client.me())
        except GridhuntError:
            pass
        hass.config_entries.async_update_entry(entry, version=3)
    return True


def _adopt_account_id(hass: HomeAssistant, entry: GridhuntConfigEntry, me: dict) -> None:
    """Switch a legacy (token hash) unique_id to the account id, unless another entry already owns it."""
    account_id = account_id_of(me)
    if not account_id or entry.unique_id == account_id:
        return
    if any(e.unique_id == account_id and e.entry_id != entry.entry_id
           for e in hass.config_entries.async_entries(DOMAIN)):
        LOGGER.warning("Gridhunt: another entry already uses this account; %s keeps its id", entry.title)
        return
    hass.config_entries.async_update_entry(entry, unique_id=account_id)


async def async_setup_entry(hass: HomeAssistant, entry: GridhuntConfigEntry) -> bool:
    """Set up one Gridhunt account."""
    client = GridhuntClient(
        async_get_clientsession(hass), entry.data[CONF_BASE_URL], entry.data[CONF_TOKEN]
    )
    coordinator = GridhuntCoordinator(hass, entry, client, get_extensions(hass))
    await coordinator.async_config_entry_first_refresh()

    _adopt_account_id(hass, entry, coordinator.data.me)

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
    # network PUT must not delay setup: runs in the background, polling covers the gap
    entry.async_create_background_task(
        hass,
        webhooks.async_register_remote(hass, entry, client, webhook_id),
        name="gridhunt webhook registration",
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    panel.async_track_entry(hass, entry, True)
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    return True


async def _async_entry_updated(hass: HomeAssistant, entry: GridhuntConfigEntry) -> None:
    """Options changed: add or remove the sidebar panel without a reload."""
    panel.async_track_entry(hass, entry, True)


async def async_unload_entry(hass: HomeAssistant, entry: GridhuntConfigEntry) -> bool:
    """Unload an account."""
    runtime = entry.runtime_data
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        panel.async_track_entry(hass, entry, False)
        webhooks.async_unregister_local(hass, runtime.webhook_id)
        for ext in runtime.coordinator.extensions:
            if hook := getattr(ext, "async_unload_entry", None):
                await hook(hass, runtime.coordinator)
        others = [
            e for e in hass.config_entries.async_loaded_entries(DOMAIN) if e.entry_id != entry.entry_id
        ]
        if not others:
            for ext in get_extensions(hass):
                if hook := getattr(ext, "async_unload", None):
                    await hook(hass)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: GridhuntConfigEntry) -> None:
    """Account removed for good: delete the server-side webhook and the cloudhook."""
    await webhooks.async_delete_remote(hass, entry)
    await webhooks.async_delete_cloudhook(hass, entry)
