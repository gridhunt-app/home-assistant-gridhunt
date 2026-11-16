"""Binary sensor: riding."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import GridhuntConfigEntry, GridhuntCoordinator
from .entity import GridhuntEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: GridhuntConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([GridhuntRidingSensor(entry.runtime_data.coordinator)])


class GridhuntRidingSensor(GridhuntEntity, BinarySensorEntity):
    """On while a ride is being recorded."""

    _attr_translation_key = "riding"
    _attr_device_class = BinarySensorDeviceClass.MOVING

    def __init__(self, coordinator: GridhuntCoordinator) -> None:
        super().__init__(coordinator, "riding")

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.riding

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        s = self.coordinator.data.state
        return {
            k: s.get(k) for k in ("kind", "routeName", "startedAt", "offRoute") if k in s
        }
