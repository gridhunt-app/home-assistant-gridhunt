"""Webhook receiver and polling fallback events."""

import json
import time
from unittest.mock import patch

from homeassistant.components import webhook as ha_webhook
from pytest_homeassistant_custom_component.common import async_capture_events

from custom_components.gridhunt.const import CONF_WEBHOOK_SECRET, CONF_WEBHOOK_URL
from custom_components.gridhunt.webhooks import sign, verify_signature

from .common import BASE, STATE_IDLE, STATE_RIDING, mock_api, setup_entry

SECRET = "whsec_test"


async def _setup_with_webhook(hass, aioclient_mock):
    mock_api(aioclient_mock)
    aioclient_mock.put(f"{BASE}/api/ha/webhook", json={"host": "ha.example.com", "secret": SECRET})
    with patch.object(
        ha_webhook, "async_generate_url", return_value="https://ha.example.com/api/webhook/abc"
    ):
        return await setup_entry(hass)


def test_verify_signature():
    body = b'{"a":1}'
    now = 1_700_000_000
    good = sign(SECRET, body, now)
    assert verify_signature(SECRET, good, body, now=now + 10)
    assert not verify_signature(SECRET, good, body, now=now + 301)  # too old
    assert not verify_signature(SECRET, good, b'{"a":2}', now=now)  # tampered
    assert not verify_signature("other", good, body, now=now)
    assert not verify_signature(SECRET, None, body, now=now)
    assert not verify_signature(SECRET, "garbage", body, now=now)


async def test_registers_and_stores_secret(hass, aioclient_mock):
    entry = await _setup_with_webhook(hass, aioclient_mock)
    assert entry.data[CONF_WEBHOOK_SECRET] == SECRET
    assert entry.data[CONF_WEBHOOK_URL] == "https://ha.example.com/api/webhook/abc"
    put = [r for r in aioclient_mock.mock_calls if r[0] == "PUT"]
    assert put and put[0][2] == {"url": "https://ha.example.com/api/webhook/abc"}


async def test_no_external_url_means_polling_only(hass, aioclient_mock):
    mock_api(aioclient_mock)
    entry = await setup_entry(hass)
    assert CONF_WEBHOOK_SECRET not in entry.data
    assert not [r for r in aioclient_mock.mock_calls if r[0] == "PUT"]


async def test_webhook_good_signature_fires_event(hass, hass_client_no_auth, aioclient_mock):
    entry = await _setup_with_webhook(hass, aioclient_mock)
    events = async_capture_events(hass, "gridhunt_ride_started")
    client = await hass_client_no_auth()
    body = json.dumps({"event": "ride_started", "deliveryId": "d1", "startedAt": "S1", "routeName": "R"}).encode()
    resp = await client.post(
        f"/api/webhook/{entry.runtime_data.webhook_id}",
        data=body,
        headers={"X-Gridhunt-Signature": sign(SECRET, body), "Content-Type": "application/json"},
    )
    assert resp.status == 200
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data["routeName"] == "R"
    assert events[0].data["source"] == "webhook"

    # retry of the same delivery: no second event
    resp = await client.post(
        f"/api/webhook/{entry.runtime_data.webhook_id}",
        data=body,
        headers={"X-Gridhunt-Signature": sign(SECRET, body)},
    )
    assert resp.status == 200
    await hass.async_block_till_done()
    assert len(events) == 1


async def test_webhook_bad_signature_rejected(hass, hass_client_no_auth, aioclient_mock):
    entry = await _setup_with_webhook(hass, aioclient_mock)
    events = async_capture_events(hass, "gridhunt_ride_started")
    client = await hass_client_no_auth()
    body = json.dumps({"event": "ride_started", "startedAt": "S1"}).encode()
    for header in (sign("wrong", body), sign(SECRET, body, int(time.time()) - 1000), "", "t=1,v1=zz"):
        resp = await client.post(
            f"/api/webhook/{entry.runtime_data.webhook_id}",
            data=body,
            headers={"X-Gridhunt-Signature": header},
        )
        assert resp.status == 401
    await hass.async_block_till_done()
    assert events == []


async def test_poll_fallback_events(hass, aioclient_mock):
    mock_api(aioclient_mock, state=STATE_IDLE)
    entry = await setup_entry(hass)
    coordinator = entry.runtime_data.coordinator
    started = async_capture_events(hass, "gridhunt_ride_started")
    finished = async_capture_events(hass, "gridhunt_ride_finished")
    square = async_capture_events(hass, "gridhunt_new_square")

    mock_api(aioclient_mock, state=STATE_RIDING)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert len(started) == 1 and started[0].data["source"] == "poll"
    assert started[0].data["routeName"] == "Pętla przez Puszczę"
    assert not square

    bigger = {**STATE_RIDING, "square": {"size": 13, "from": 12}}
    mock_api(aioclient_mock, state=bigger)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert len(square) == 1
    assert square[0].data["square"] == {"from": 12, "to": 13}

    await coordinator.async_refresh()  # same state again: nothing new
    assert len(square) == 1

    ended = {**STATE_IDLE, "lastRide": {**STATE_IDLE["lastRide"], "distanceKm": 60.1, "endedAt": "2026-10-25T12:00:00Z"}}
    mock_api(aioclient_mock, state=ended)
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert len(finished) == 1
    assert finished[0].data["distanceKm"] == 60.1
    assert finished[0].data["routeName"] == "Pętla przez Puszczę"
    assert len(started) == 1


async def test_no_double_event_when_webhook_and_poll_both_see_it(hass, hass_client_no_auth, aioclient_mock):
    entry = await _setup_with_webhook(hass, aioclient_mock)
    coordinator = entry.runtime_data.coordinator
    started = async_capture_events(hass, "gridhunt_ride_started")
    client = await hass_client_no_auth()
    body = json.dumps({"event": "ride_started", "deliveryId": "d9", "startedAt": STATE_RIDING["startedAt"]}).encode()
    await client.post(
        f"/api/webhook/{entry.runtime_data.webhook_id}",
        data=body,
        headers={"X-Gridhunt-Signature": sign(SECRET, body)},
    )
    await hass.async_block_till_done()
    mock_api(aioclient_mock, state=STATE_RIDING)
    aioclient_mock.put(f"{BASE}/api/ha/webhook", json={"secret": SECRET})
    await coordinator.async_refresh()
    await hass.async_block_till_done()
    assert len(started) == 1


async def test_test_event(hass, hass_client_no_auth, aioclient_mock):
    entry = await _setup_with_webhook(hass, aioclient_mock)
    events = async_capture_events(hass, "gridhunt_test")
    client = await hass_client_no_auth()
    body = json.dumps({"event": "test", "deliveryId": "t1"}).encode()
    resp = await client.post(
        f"/api/webhook/{entry.runtime_data.webhook_id}",
        data=body,
        headers={"X-Gridhunt-Signature": sign(SECRET, body)},
    )
    assert resp.status == 200
    await hass.async_block_till_done()
    assert len(events) == 1


async def test_cloudhook_mock_request_fires_event(hass, aioclient_mock):
    """Nabu Casa passes a MockRequest (no read()); the handler must accept it."""
    from homeassistant.components.webhook import async_handle_webhook
    from homeassistant.util.aiohttp import MockRequest

    entry = await _setup_with_webhook(hass, aioclient_mock)
    events = async_capture_events(hass, "gridhunt_ride_started")
    body = json.dumps({"event": "ride_started", "deliveryId": "c1", "startedAt": "S2", "routeName": "Cloud"}).encode()
    req = MockRequest(
        content=body,
        mock_source="cloud",
        method="POST",
        headers={"X-Gridhunt-Signature": sign(SECRET, body), "Content-Type": "application/json"},
    )
    resp = await async_handle_webhook(hass, entry.runtime_data.webhook_id, req)
    assert resp.status == 200
    await hass.async_block_till_done()
    assert len(events) == 1
    assert events[0].data["routeName"] == "Cloud"
