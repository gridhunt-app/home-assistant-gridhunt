"""Coordinator and entity tests."""

from homeassistant.helpers import entity_registry as er
from homeassistant.config_entries import ConfigEntryState

from custom_components.gridhunt.const import DOMAIN

from .common import (
    BASE,
    STATE_IDLE,
    STATE_RIDING,
    STATS,
    mock_api,
    setup_entry,
    unique,
)


def _state(hass, entry, platform, key):
    ent_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, unique(entry, key))
    assert ent_id, f"{platform}/{key} not registered"
    return hass.states.get(ent_id)


async def test_idle(hass, aioclient_mock):
    mock_api(aioclient_mock)
    entry = await setup_entry(hass)
    assert entry.state is ConfigEntryState.LOADED
    assert _state(hass, entry, "binary_sensor", "riding").state == "off"
    assert _state(hass, entry, "sensor", "progress_pct").state == "unknown"
    assert _state(hass, entry, "sensor", "tiles_total").state == "1234"
    assert _state(hass, entry, "sensor", "tiles_this_year").state == "321"
    assert _state(hass, entry, "sensor", "square").state == "11"
    last = _state(hass, entry, "sensor", "last_ride")
    assert last.state.startswith("2026-10-24T11:30:00")
    assert last.attributes["distanceKm"] == 58.3
    tracker = _state(hass, entry, "device_tracker", "position")
    assert "latitude" not in tracker.attributes
    assert entry.runtime_data.coordinator.update_interval.total_seconds() == 60
    # heavy data never in attributes
    assert "line" not in last.attributes
    # live only while riding
    assert not [r for r in aioclient_mock.mock_calls if r[1].path == "/api/ha/live"]


async def test_riding(hass, aioclient_mock):
    mock_api(aioclient_mock, state=STATE_RIDING)
    entry = await setup_entry(hass)
    assert _state(hass, entry, "binary_sensor", "riding").state == "on"
    assert _state(hass, entry, "sensor", "progress_pct").state == "64.6"
    assert float(_state(hass, entry, "sensor", "distance_done_km").state) == 41.2
    assert float(_state(hass, entry, "sensor", "distance_left_km").state) == 22.6
    assert float(_state(hass, entry, "sensor", "distance_km").state) == 42.0
    assert _state(hass, entry, "sensor", "new_tiles").state == "9"
    assert _state(hass, entry, "sensor", "square").state == "12"
    tracker = _state(hass, entry, "device_tracker", "position")
    assert tracker.attributes["latitude"] == 53.43
    assert tracker.attributes["longitude"] == 14.55
    assert tracker.attributes["speedKmh"] == 24.1
    assert tracker.attributes["ageSec"] == 12
    assert entry.runtime_data.coordinator.update_interval.total_seconds() == 20
    assert [r for r in aioclient_mock.mock_calls if r[1].path == "/api/ha/live"]


async def test_square_fallback_to_stats(hass, aioclient_mock):
    state = {**STATE_IDLE, "square": None}
    mock_api(aioclient_mock, state=state)
    entry = await setup_entry(hass)
    assert _state(hass, entry, "sensor", "square").state == str(STATS["uber"])


async def test_single_endpoint_failure_is_tolerated(hass, aioclient_mock):
    mock_api(aioclient_mock)
    entry = await setup_entry(hass)
    coordinator = entry.runtime_data.coordinator
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{BASE}/api/ha/state", json=STATE_IDLE)
    aioclient_mock.get(f"{BASE}/api/ha/stats", status=500)
    aioclient_mock.get(f"{BASE}/api/ha/me", status=500)
    aioclient_mock.get(f"{BASE}/api/ha/routes", status=500)
    coordinator.force_refresh_all()
    await coordinator.async_refresh()
    assert coordinator.last_update_success
    assert coordinator.data.stats["tilesZ14"] == 1234  # kept the previous value


async def test_refresh_service(hass, aioclient_mock):
    mock_api(aioclient_mock)
    await setup_entry(hass)
    before = len([r for r in aioclient_mock.mock_calls if r[1].path == "/api/ha/stats"])
    await hass.services.async_call(DOMAIN, "refresh", {}, blocking=True)
    after = len([r for r in aioclient_mock.mock_calls if r[1].path == "/api/ha/stats"])
    assert after == before + 1


async def test_unload(hass, aioclient_mock):
    mock_api(aioclient_mock)
    aioclient_mock.delete(f"{BASE}/api/ha/webhook", json={"ok": True})
    entry = await setup_entry(hass)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED
    assert [r for r in aioclient_mock.mock_calls if r[0] == "DELETE"]
