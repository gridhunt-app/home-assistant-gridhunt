"""Device tracker: current position while riding."""

from __future__ import annotations

from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import GridhuntConfigEntry, GridhuntCoordinator
from .entity import GridhuntEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: GridhuntConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([GridhuntTracker(entry.runtime_data.coordinator)])


class GridhuntTracker(GridhuntEntity, TrackerEntity):
    """Location is known only while riding."""

    _attr_translation_key = "position"
    _attr_source_type = SourceType.GPS

    def __init__(self, coordinator: GridhuntCoordinator) -> None:
        super().__init__(coordinator, "position")

    def _pos(self) -> dict[str, Any] | None:
        data = self.coordinator.data
        pos = data.state.get("position")
        return pos if data.riding and isinstance(pos, dict) else None

    @property
    def latitude(self) -> float | None:
        pos = self._pos()
        return pos.get("lat") if pos else None

    @property
    def longitude(self) -> float | None:
        pos = self._pos()
        return pos.get("lon") if pos else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        pos = self._pos() or {}
        return {"ageSec": pos.get("ageSec"), "speedKmh": pos.get("speedKmh")}
