"""Shared entity base."""

from __future__ import annotations

from homeassistant.config_entries import SOURCE_IGNORE, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BASE_URL, DOMAIN
from .coordinator import GridhuntCoordinator


BRAND = "Gridhunt"


def device_name(hass: HomeAssistant, entry: ConfigEntry) -> str:
    """Device name: "Gridhunt" for the first account, "Gridhunt <account>" for the next ones.

    Entity ids and friendly names come from it (has_entity_name): sensor.gridhunt_tiles, "Gridhunt Tiles".
    The account name appears only when a second account would otherwise collide.
    """
    entries = [e for e in hass.config_entries.async_entries(DOMAIN) if e.source != SOURCE_IGNORE]
    if not entries or entries[0].entry_id == entry.entry_id:
        return BRAND
    return f"{BRAND} {entry.title}".strip()


class GridhuntEntity(CoordinatorEntity[GridhuntCoordinator]):
    """Base class: one device per account."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GridhuntCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=device_name(coordinator.hass, entry),
            manufacturer="Gridhunt",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=entry.data.get(CONF_BASE_URL),
        )
