"""Websocket API for the card."""

from .common import BASE, LIVE, ME, STATE_IDLE, STATE_RIDING, mock_api, setup_entry


async def test_card_payload_riding(hass, hass_ws_client, aioclient_mock):
    mock_api(aioclient_mock, state=STATE_RIDING)
    entry = await setup_entry(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "gridhunt/card"})
    msg = await ws.receive_json()
    assert msg["success"]
    r = msg["result"]
    assert set(r) == {"entry_id", "features", "me", "state", "live", "stats", "routes", "tiles"}
    assert r["entry_id"] == entry.entry_id
    assert r["features"] == {}
    assert r["me"]["name"] == "Łucja"
    assert r["state"]["riding"] is True
    assert r["live"]["line"] == LIVE["line"]
    assert r["stats"]["tilesZ14"] == 1234
    assert r["routes"][0]["id"] == "r1"
    assert "events" not in r


async def test_card_payload_idle_and_entry_id(hass, hass_ws_client, aioclient_mock):
    mock_api(aioclient_mock, state=STATE_IDLE)
    entry = await setup_entry(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "gridhunt/card", "entry_id": entry.entry_id})
    r = (await ws.receive_json())["result"]
    assert r["live"] is None
    await ws.send_json({"id": 2, "type": "gridhunt/card", "entry_id": "nope"})
    msg = await ws.receive_json()
    assert not msg["success"] and msg["error"]["code"] == "not_found"


async def test_route(hass, hass_ws_client, aioclient_mock):
    mock_api(aioclient_mock)
    await setup_entry(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": "gridhunt/route", "route_id": "r1"})
    msg = await ws.receive_json()
    assert msg["success"] and msg["result"]["id"] == "r1"
    aioclient_mock.get(f"{BASE}/api/ha/routes/zzz", status=404, json={"error": "not_found"})
    await ws.send_json({"id": 2, "type": "gridhunt/route", "route_id": "zzz"})
    msg = await ws.receive_json()
    assert not msg["success"] and msg["error"]["code"] == "not_found"


async def test_no_extension_features_without_flag(hass, aioclient_mock):
    mock_api(aioclient_mock, me={**ME, "features": {}})
    entry = await setup_entry(hass)
    assert entry.runtime_data.coordinator.extensions == []
