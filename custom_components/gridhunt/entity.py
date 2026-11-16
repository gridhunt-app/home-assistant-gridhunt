"""Shared entity base."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_BASE_URL, DOMAIN
from .coordinator import GridhuntCoordinator


class GridhuntEntity(CoordinatorEntity[GridhuntCoordinator]):
    """Base class: one device per account."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: GridhuntCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Gridhunt",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=entry.data.get(CONF_BASE_URL),
        )
