"""Audit fixes 0.1.18: route id validation, webhook lifecycle, account unique_id, push polling, diagnostics."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from homeassistant.components import webhook as ha_webhook
from homeassistant.config_entries import ConfigEntryState
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gridhunt.api import GridhuntClient
from custom_components.gridhunt.const import (
    CONF_BASE_URL,
    CONF_TOKEN,
    CONF_WEBHOOK_ID,
    CONF_WEBHOOK_SECRET,
    DOMAIN,
    POLL_RIDING,
    POLL_RIDING_PUSH,
)
from custom_components.gridhunt.diagnostics import async_get_config_entry_diagnostics

from .common import BASE, ME, STATE_RIDING, TOKEN, mock_api, setup_entry

SECRET = "whsec_test"
URL = "https://ha.example.com/api/webhook/abc"
ACCOUNT = {**ME, "accountKey": "0123456789abcdef0123456789abcdef"}


def _puts(aioclient_mock):
    return [r for r in aioclient_mock.mock_calls if r[0] == "PUT"]


# -- 1. route id ----------------------------------------------------------------
async def test_route_id_traversal_rejected(hass, hass_ws_client, aioclient_mock):
    mock_api(aioclient_mock)
    await setup_entry(hass)
    before = len(aioclient_mock.mock_calls)
    ws = await hass_ws_client(hass)
    for n, bad in enumerate(("../state", "a/b", "x?y=1", "%2e%2e", ""), start=1):
        await ws.send_json({"id": n, "type": "gridhunt/route", "route_id": bad})
        msg = await ws.receive_json()
        assert not msg["success"] and msg["error"]["code"] == "invalid_format", bad
    assert len(aioclient_mock.mock_calls) == before  # nothing reached the server


async def test_client_quotes_route_id(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/api/ha/routes/a%2F..%2Fstate", json={"id": "x"})
    client = GridhuntClient(async_get_clientsession(hass), BASE, TOKEN)
    assert await client.route("a/../state") == {"id": "x"}


# -- 2. webhook lifecycle -------------------------------------------------------
async def _with_webhook(hass, aioclient_mock, **extra):
    mock_api(aioclient_mock)
    aioclient_mock.put(f"{BASE}/api/ha/webhook", json={"secret": SECRET})
    with patch.object(ha_webhook, "async_generate_url", return_value=URL):
        entry = await setup_entry(hass, **extra)
        await hass.async_block_till_done()
    return entry


async def test_reload_keeps_server_webhook_and_does_not_reregister(hass, aioclient_mock):
    entry = await _with_webhook(hass, aioclient_mock)
    assert entry.data[CONF_WEBHOOK_SECRET] == SECRET and len(_puts(aioclient_mock)) == 1
    with patch.object(ha_webhook, "async_generate_url", return_value=URL):
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert not [r for r in aioclient_mock.mock_calls if r[0] == "DELETE"]
    assert len(_puts(aioclient_mock)) == 1  # same address: no second PUT
    assert entry.data[CONF_WEBHOOK_SECRET] == SECRET


async def test_remove_deletes_server_webhook(hass, aioclient_mock):
    entry = await _with_webhook(hass, aioclient_mock)
    assert await hass.config_entries.async_remove(entry.entry_id)
    assert [r for r in aioclient_mock.mock_calls if r[0] == "DELETE"]


# -- 3. account unique_id + migration ------------------------------------------
async def test_migration_v2_adopts_account_id(hass, aioclient_mock):
    mock_api(aioclient_mock, me=ACCOUNT)
    entry = MockConfigEntry(domain=DOMAIN, version=2, unique_id="6f9fa3bcd5c1", data={CONF_BASE_URL: BASE, CONF_TOKEN: TOKEN})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.version == 3 and entry.unique_id == ACCOUNT["accountKey"]


async def test_setup_adopts_account_id_when_migration_offline(hass, aioclient_mock):
    mock_api(aioclient_mock, me=ACCOUNT)
    entry = MockConfigEntry(domain=DOMAIN, version=3, unique_id="6f9fa3bcd5c1", data={CONF_BASE_URL: BASE, CONF_TOKEN: TOKEN})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    assert entry.unique_id == ACCOUNT["accountKey"]


async def test_new_token_same_account_is_duplicate(hass, aioclient_mock):
    mock_api(aioclient_mock, me=ACCOUNT)
    MockConfigEntry(domain=DOMAIN, unique_id=ACCOUNT["accountKey"], data={CONF_BASE_URL: BASE, CONF_TOKEN: TOKEN}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "token"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TOKEN: "gha_other", CONF_BASE_URL: BASE})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "already_configured"


async def _reauth(hass, aioclient_mock, entry, me):
    mock_api(aioclient_mock, me=me)
    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "token"})
    return await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TOKEN: "gha_new", CONF_BASE_URL: BASE})


async def test_reauth_same_account_ok_and_other_account_aborts(hass, aioclient_mock):
    mock_api(aioclient_mock, me=ACCOUNT)
    entry = await setup_entry(hass)
    hass.config_entries.async_update_entry(entry, unique_id=ACCOUNT["accountKey"])
    result = await _reauth(hass, aioclient_mock, entry, {**ACCOUNT, "accountKey": "ffffffffffffffffffffffffffffffff"})
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "wrong_account"
    assert entry.data[CONF_TOKEN] == TOKEN
    result = await _reauth(hass, aioclient_mock, entry, ACCOUNT)
    assert result["reason"] == "reauth_successful" and entry.data[CONF_TOKEN] == "gha_new"


async def test_reauth_legacy_unique_id_upgrades(hass, aioclient_mock):
    mock_api(aioclient_mock)
    entry = await setup_entry(hass)
    hass.config_entries.async_update_entry(entry, unique_id="6f9fa3bcd5c1")
    result = await _reauth(hass, aioclient_mock, entry, ACCOUNT)
    assert result["reason"] == "reauth_successful" and entry.unique_id == ACCOUNT["accountKey"]


# -- 4. polling -----------------------------------------------------------------
async def test_riding_poll_is_slow_with_webhook_and_fast_without(hass, aioclient_mock):
    mock_api(aioclient_mock, state=STATE_RIDING)
    plain = await setup_entry(hass)
    assert plain.runtime_data.coordinator.update_interval == timedelta(seconds=POLL_RIDING)
    await hass.config_entries.async_unload(plain.entry_id)
    await hass.config_entries.async_remove(plain.entry_id)

    entry = await _with_webhook(hass, aioclient_mock)
    mock_api(aioclient_mock, state=STATE_RIDING)
    coordinator = entry.runtime_data.coordinator
    assert coordinator.push_active
    await coordinator.async_refresh()
    assert coordinator.update_interval == timedelta(seconds=POLL_RIDING_PUSH) and POLL_RIDING_PUSH >= 60


# -- 8. diagnostics -------------------------------------------------------------
async def test_diagnostics_redacts_secrets(hass, aioclient_mock):
    entry = await _with_webhook(hass, aioclient_mock)
    diag = await async_get_config_entry_diagnostics(hass, entry)
    text = str(diag)
    for secret in (TOKEN, SECRET, URL, entry.data[CONF_WEBHOOK_ID], "Łucja"):
        assert secret not in text, secret
    assert diag["entry"]["data"][CONF_TOKEN] == "**REDACTED**"
    assert diag["push_active"] is True
