"""Config flow tests."""

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gridhunt.config_flow import unique_id_for
from custom_components.gridhunt.const import CONF_BASE_URL, CONF_TOKEN, DOMAIN

from .common import BASE, TOKEN, mock_api


async def _start(hass):
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.MENU
    assert result["menu_options"][0] == "pair"
    return result


async def test_pairing_pending_then_token(hass, aioclient_mock):
    mock_api(aioclient_mock)
    aioclient_mock.post(
        f"{BASE}/api/ha/pair",
        json={"userCode": "ABC234", "deviceCode": "dev1", "verificationUrl": f"{BASE}/settings/connections?ha-code=ABC234", "expiresIn": 900, "interval": 5},
    )
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "pair"})
    assert result["step_id"] == "pair"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_BASE_URL: BASE})
    assert result["step_id"] == "pair_wait"
    assert result["description_placeholders"]["user_code"] == "ABC234"
    assert "ha-code=ABC234" in result["description_placeholders"]["verification_url"]

    aioclient_mock.post(f"{BASE}/api/ha/pair/poll", json={"status": "pending"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "pair_wait"
    assert result["errors"] == {"base": "authorization_pending"}

    aioclient_mock.clear_requests()
    mock_api(aioclient_mock)
    aioclient_mock.post(f"{BASE}/api/ha/pair/poll", json={"token": TOKEN, "scopes": ["read"], "name": "Home Assistant"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Łucja"
    assert result["data"] == {CONF_BASE_URL: BASE, CONF_TOKEN: TOKEN}
    assert result["result"].unique_id == unique_id_for(TOKEN)
    await hass.async_block_till_done()


async def test_pairing_expired_code(hass, aioclient_mock):
    aioclient_mock.post(f"{BASE}/api/ha/pair", json={"userCode": "ABC234", "deviceCode": "d", "verificationUrl": f"{BASE}/x"})
    aioclient_mock.post(f"{BASE}/api/ha/pair/poll", status=400, json={"error": "invalid_code"})
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "pair"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_BASE_URL: BASE})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["step_id"] == "pair"
    assert result["errors"] == {"base": "code_expired"}


async def test_token_ok(hass, aioclient_mock):
    mock_api(aioclient_mock)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "token"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TOKEN: f" {TOKEN} ", CONF_BASE_URL: BASE + "/"})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_BASE_URL: BASE, CONF_TOKEN: TOKEN}
    await hass.async_block_till_done()


async def test_token_invalid(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/api/ha/me", status=404, json={"error": "not_found"})
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "token"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TOKEN: "bad", CONF_BASE_URL: BASE})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_token_unreachable(hass, aioclient_mock):
    aioclient_mock.get(f"{BASE}/api/ha/me", status=500)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "token"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TOKEN: "x", CONF_BASE_URL: BASE})
    assert result["errors"] == {"base": "cannot_connect"}


async def test_duplicate_token_aborts(hass, aioclient_mock):
    mock_api(aioclient_mock)
    MockConfigEntry(domain=DOMAIN, unique_id=unique_id_for(TOKEN), data={CONF_BASE_URL: BASE, CONF_TOKEN: TOKEN}).add_to_hass(hass)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"next_step_id": "token"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TOKEN: TOKEN, CONF_BASE_URL: BASE})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_on_404(hass, aioclient_mock):
    from .common import setup_entry

    mock_api(aioclient_mock)
    entry = await setup_entry(hass)
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{BASE}/api/ha/state", status=404, json={"error": "not_found"})
    aioclient_mock.get(f"{BASE}/api/ha/me", status=404, json={"error": "not_found"})
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(f["context"]["source"] == "reauth" for f in flows)

    mock_api(aioclient_mock)
    flow = next(f for f in flows if f["context"]["source"] == "reauth")
    result = await hass.config_entries.flow.async_configure(flow["flow_id"], {"next_step_id": "token"})
    new_token = "gha_newtoken"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TOKEN: new_token, CONF_BASE_URL: BASE})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_TOKEN] == new_token
    assert entry.unique_id == "abc123"  # server without account id: unique_id untouched
    await hass.async_block_till_done()
