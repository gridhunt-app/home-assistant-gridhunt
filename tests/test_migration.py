"""Config entry v1 -> v2: entity ids rafal_wasil_* -> gridhunt_* (only default ids, only when free)."""

from __future__ import annotations

from homeassistant.helpers import device_registry as dr, entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gridhunt.const import CONF_BASE_URL, CONF_TOKEN, DOMAIN

from .common import BASE, TOKEN, mock_api


def _v1(hass, title="Rafał Wasil", uid="abc123", token=TOKEN):
    entry = MockConfigEntry(domain=DOMAIN, title=title, unique_id=uid, version=1, data={CONF_BASE_URL: BASE, CONF_TOKEN: token})
    entry.add_to_hass(hass)
    return entry


def _old(reg, entry, platform, key, object_id):
    return reg.async_get_or_create(platform, DOMAIN, f"{entry.entry_id}_{key}", config_entry=entry, suggested_object_id=object_id).entity_id


async def test_migrates_default_ids_and_device_name(hass, aioclient_mock):
    mock_api(aioclient_mock)
    entry = _v1(hass)
    reg = er.async_get(hass)
    dr.async_get(hass).async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.entry_id)}, name="Rafał Wasil")
    assert _old(reg, entry, "binary_sensor", "riding", "rafal_wasil_riding") == "binary_sensor.rafal_wasil_riding"
    _old(reg, entry, "sensor", "tiles_total", "rafal_wasil_tiles")
    _old(reg, entry, "device_tracker", "position", "rafal_wasil_position")
    # renamed by the user: stays
    _old(reg, entry, "sensor", "square", "moj_kwadrat")
    # target taken by something else: stays
    reg.async_get_or_create("sensor", "demo", "x", suggested_object_id="gridhunt_last_ride")
    _old(reg, entry, "sensor", "last_ride", "rafal_wasil_last_ride")

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == 3
    get = lambda p, k: reg.async_get_entity_id(p, DOMAIN, f"{entry.entry_id}_{k}")
    assert get("binary_sensor", "riding") == "binary_sensor.gridhunt_riding"
    assert get("sensor", "tiles_total") == "sensor.gridhunt_tiles"
    assert get("device_tracker", "position") == "device_tracker.gridhunt_position"
    assert get("sensor", "square") == "sensor.moj_kwadrat"
    assert get("sensor", "last_ride") == "sensor.rafal_wasil_last_ride"
    assert hass.states.get("binary_sensor.gridhunt_riding").attributes["friendly_name"] == "Gridhunt Riding"
    assert next(d for d in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id) if (DOMAIN, entry.entry_id) in d.identifiers).name == "Gridhunt"


async def test_device_renamed_by_user_keeps_name(hass, aioclient_mock):
    mock_api(aioclient_mock)
    entry = _v1(hass)
    dev_reg = dr.async_get(hass)
    dev = dev_reg.async_get_or_create(config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.entry_id)}, name="Rafał Wasil")
    dev_reg.async_update_device(dev.id, name_by_user="Mój rower")
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert dev_reg.async_get(dev.id).name_by_user == "Mój rower"


async def test_second_account_gets_account_name(hass, aioclient_mock):
    mock_api(aioclient_mock)
    first = MockConfigEntry(domain=DOMAIN, title="Rafał Wasil", unique_id="a1", version=2, data={CONF_BASE_URL: BASE, CONF_TOKEN: TOKEN})
    first.add_to_hass(hass)
    second = MockConfigEntry(domain=DOMAIN, title="Jan", unique_id="a2", version=2, data={CONF_BASE_URL: BASE, CONF_TOKEN: TOKEN + "2"})
    second.add_to_hass(hass)
    assert await hass.config_entries.async_setup(first.entry_id)
    await hass.async_block_till_done()
    reg = er.async_get(hass)
    assert reg.async_get_entity_id("binary_sensor", DOMAIN, f"{first.entry_id}_riding") == "binary_sensor.gridhunt_riding"
    assert reg.async_get_entity_id("binary_sensor", DOMAIN, f"{second.entry_id}_riding") == "binary_sensor.gridhunt_jan_riding"
    assert next(d for d in dr.async_entries_for_config_entry(dr.async_get(hass), second.entry_id) if (DOMAIN, second.entry_id) in d.identifiers).name == "Gridhunt Jan"
