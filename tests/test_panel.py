"""Sidebar panel: added at setup, one for all accounts, option on/off without a restart."""

from __future__ import annotations

from homeassistant.components.frontend import DATA_PANELS
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gridhunt.const import CONF_BASE_URL, CONF_SHOW_PANEL, CONF_TOKEN, DOMAIN
from custom_components.gridhunt.panel import PANEL_URL

from .common import BASE, TOKEN, mock_api, setup_entry


def _panel(hass):
    return hass.data.get(DATA_PANELS, {}).get(PANEL_URL)


async def _second(hass):
    entry = MockConfigEntry(domain=DOMAIN, title="Jan", unique_id="def456", data={CONF_BASE_URL: BASE, CONF_TOKEN: TOKEN + "2"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_panel_registered_with_mark_icon(hass, aioclient_mock):
    mock_api(aioclient_mock)
    await setup_entry(hass)
    p = _panel(hass)
    assert p is not None
    assert p.sidebar_title == "gridhunt" and p.sidebar_icon == "gridhunt:mark" and p.require_admin is False
    custom = p.config["_panel_custom"]
    assert custom["name"] == "gridhunt-panel" and custom["embed_iframe"] is False
    assert custom["module_url"].startswith("/gridhunt_static/gridhunt-card.js?v=")


async def test_option_toggles_panel_without_reload(hass, aioclient_mock):
    mock_api(aioclient_mock)
    entry = await setup_entry(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "init"
    assert result["data_schema"]({}) == {CONF_SHOW_PANEL: True}
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_SHOW_PANEL: False})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options[CONF_SHOW_PANEL] is False
    assert _panel(hass) is None
    coordinator = entry.runtime_data.coordinator  # same runtime: no reload happened

    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["data_schema"]({}) == {CONF_SHOW_PANEL: False}
    await hass.config_entries.options.async_configure(result["flow_id"], {CONF_SHOW_PANEL: True})
    await hass.async_block_till_done()
    assert _panel(hass) is not None
    assert entry.runtime_data.coordinator is coordinator


async def test_one_panel_for_many_accounts_removed_with_last(hass, aioclient_mock):
    mock_api(aioclient_mock)
    first = await setup_entry(hass)
    second = await _second(hass)
    assert _panel(hass) is not None
    assert await hass.config_entries.async_unload(first.entry_id)
    await hass.async_block_till_done()
    assert _panel(hass) is not None  # second account still wants it
    assert await hass.config_entries.async_remove(second.entry_id)
    await hass.async_block_till_done()
    assert _panel(hass) is None
    assert await hass.config_entries.async_setup(first.entry_id)
    await hass.async_block_till_done()
    assert _panel(hass) is not None


async def test_panel_off_on_one_account_kept_by_other(hass, aioclient_mock):
    mock_api(aioclient_mock)
    first = await setup_entry(hass)
    await _second(hass)
    hass.config_entries.async_update_entry(first, options={CONF_SHOW_PANEL: False})
    await hass.async_block_till_done()
    assert _panel(hass) is not None
