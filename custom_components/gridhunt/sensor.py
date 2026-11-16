"""Sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import GridhuntConfigEntry, GridhuntCoordinator, GridhuntData
from .entity import GridhuntEntity


def _get(d: dict[str, Any] | None, *path: str) -> Any:
    for key in path:
        if not isinstance(d, dict):
            return None
        d = d.get(key)
    return d


def _square(data: GridhuntData) -> Any:
    size = _get(data.state, "square", "size")
    return size if size is not None else data.stats.get("uber")


def _last_ride_at(data: GridhuntData) -> Any:
    raw = _get(data.state, "lastRide", "endedAt")
    return dt_util.parse_datetime(raw) if isinstance(raw, str) else None


def _last_ride_attrs(data: GridhuntData) -> dict[str, Any]:
    last = data.state.get("lastRide") or {}
    return {k: last.get(k) for k in ("name", "kind", "startedAt", "endedAt", "distanceKm", "tiles")}


@dataclass(frozen=True, kw_only=True)
class GridhuntSensorDescription(SensorEntityDescription):
    value_fn: Callable[[GridhuntData], Any]
    attrs_fn: Callable[[GridhuntData], dict[str, Any]] | None = None


_KM = {
    "native_unit_of_measurement": UnitOfLength.KILOMETERS,
    "device_class": SensorDeviceClass.DISTANCE,
    "state_class": SensorStateClass.MEASUREMENT,
}

SENSORS: tuple[GridhuntSensorDescription, ...] = (
    GridhuntSensorDescription(
        key="progress_pct",
        translation_key="progress_pct",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda d: _get(d.state, "progress", "pct"),
    ),
    GridhuntSensorDescription(
        key="distance_done_km",
        translation_key="distance_done_km",
        suggested_display_precision=1,
        value_fn=lambda d: _get(d.state, "progress", "doneKm"),
        **_KM,
    ),
    GridhuntSensorDescription(
        key="distance_left_km",
        translation_key="distance_left_km",
        suggested_display_precision=1,
        value_fn=lambda d: _get(d.state, "progress", "leftKm"),
        **_KM,
    ),
    GridhuntSensorDescription(
        key="distance_km",
        translation_key="distance_km",
        suggested_display_precision=1,
        value_fn=lambda d: d.state.get("distanceKm"),
        **_KM,
    ),
    GridhuntSensorDescription(
        key="new_tiles",
        translation_key="new_tiles",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: _get(d.state, "tiles", "mine"),
    ),
    GridhuntSensorDescription(
        key="square",
        translation_key="square",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_square,
    ),
    GridhuntSensorDescription(
        key="tiles_total",
        translation_key="tiles_total",
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.stats.get("tilesZ14"),
    ),
    GridhuntSensorDescription(
        key="tiles_this_year",
        translation_key="tiles_this_year",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.stats.get("newThisYear"),
    ),
    GridhuntSensorDescription(
        key="last_ride",
        translation_key="last_ride",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=_last_ride_at,
        attrs_fn=_last_ride_attrs,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: GridhuntConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data.coordinator
    entities: list[SensorEntity] = [GridhuntSensor(coordinator, d) for d in SENSORS]
    for ext in coordinator.extensions:
        if hook := getattr(ext, "sensor_entities", None):
            entities.extend(hook(coordinator))
    async_add_entities(entities)


class GridhuntSensor(GridhuntEntity, SensorEntity):
    """Generic value-function sensor."""

    entity_description: GridhuntSensorDescription

    def __init__(self, coordinator: GridhuntCoordinator, description: GridhuntSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        fn = self.entity_description.attrs_fn
        return fn(self.coordinator.data) if fn else None
