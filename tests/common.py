"""Shared helpers for tests."""

from __future__ import annotations

import copy
from typing import Any

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gridhunt.const import CONF_BASE_URL, CONF_TOKEN, DOMAIN

BASE = "https://gridhunt.app"
TOKEN = "gha_testtoken0123456789abcdefghijkl"

ME = {"name": "Łucja", "units": "metric", "scopes": ["read"], "pollSec": 20, "features": {}}

STATE_IDLE: dict[str, Any] = {
    "riding": False,
    "kind": None,
    "routeName": None,
    "startedAt": None,
    "updatedAt": "2026-10-25T10:00:00Z",
    "progress": None,
    "distanceKm": None,
    "tiles": {"mine": 0, "total": 0},
    "square": {"size": 11, "from": 11},
    "position": None,
    "lastRide": {
        "name": "Pętla",
        "kind": "route",
        "startedAt": "2026-10-24T08:00:00Z",
        "endedAt": "2026-10-24T11:30:00Z",
        "distanceKm": 58.3,
        "tiles": 14,
    },
    "liveUrl": "https://gridhunt.app/live/ha/ghk_x",
    "pollSec": 60,
}

STATE_RIDING: dict[str, Any] = {
    "riding": True,
    "kind": "route",
    "routeName": "Pętla przez Puszczę",
    "startedAt": "2026-10-25T09:00:00Z",
    "updatedAt": "2026-10-25T10:00:00Z",
    "progress": {"doneKm": 41.2, "leftKm": 22.6, "totalKm": 63.8, "pct": 64.6},
    "distanceKm": 42.0,
    "offRoute": False,
    "tiles": {"mine": 9, "total": 9},
    "square": {"size": 12, "from": 11},
    "position": {
        "lat": 53.43,
        "lon": 14.55,
        "ageSec": 12,
        "recordedAt": "2026-10-25T10:00:00Z",
        "speedKmh": 24.1,
    },
    "lastRide": None,
    "liveUrl": "https://gridhunt.app/live/ha/ghk_x",
    "pollSec": 20,
}

STATS = {
    "name": "Łucja",
    "tilesZ14": 1234,
    "tilesZ17": 99999,
    "uber": 14,
    "newThisYear": 321,
    "targetPct": 40,
    "generated": "2026-10-25T00:00:00Z",
    "rides": {"count": 50, "lastAt": "2026-10-24T11:30:00Z"},
}

ROUTES = {"routes": [{"id": "r1", "name": "Pętla", "km": 63.8, "ascentM": 300, "tileCount": 40, "createdAt": "2026-10-01T00:00:00Z"}]}
LIVE = {**STATE_RIDING, "me": {"name": "Łucja", "trail": [[53.4, 14.5]]}, "line": [[[53.4, 14.5], [53.43, 14.55], [53.47, 14.58], [53.5, 14.6]]], "myTiles": [8854, 5304, 8854, 5303, 8855, 5302], "moments": [{"kind": "tiles", "who": None, "me": True, "data": {"count": 2, "total": 9}, "createdAt": "2026-10-25T09:55:00Z"}]}


def mock_api(
    aioclient_mock,
    *,
    me: dict | None = None,
    state: dict | None = None,
    live: dict | None = None,
    stats: dict | None = None,
    routes: dict | None = None,
) -> None:
    """Register the standard endpoints (replaces earlier registrations)."""
    aioclient_mock.clear_requests()
    aioclient_mock.get(f"{BASE}/api/ha/me", json=copy.deepcopy(me or ME))
    aioclient_mock.get(f"{BASE}/api/ha/state", json=copy.deepcopy(state or STATE_IDLE))
    aioclient_mock.get(f"{BASE}/api/ha/live", json=copy.deepcopy(live or LIVE))
    aioclient_mock.get(f"{BASE}/api/ha/stats", json=copy.deepcopy(stats or STATS))
    aioclient_mock.get(f"{BASE}/api/ha/routes", json=copy.deepcopy(routes or ROUTES))
    aioclient_mock.get(f"{BASE}/api/ha/tiles", json={"tiles": [9000, 5300], "square": {"x": 9000, "y": 5300, "s": 1}, "target": None, "view": {"x0": 8996, "y0": 5296, "x1": 9004, "y1": 5304}, "generated": None})
    aioclient_mock.delete(f"{BASE}/api/ha/webhook", json={"ok": True})
    aioclient_mock.get(f"{BASE}/api/ha/routes/r1", json={"id": "r1", "name": "Pętla", "km": 63.8, "ascentM": 300, "line": [[[53.4, 14.5], [53.43, 14.55], [53.47, 14.58], [53.5, 14.6]]]})


async def setup_entry(hass: HomeAssistant, **data_extra: Any) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Łucja",
        unique_id="abc123",
        data={CONF_BASE_URL: BASE, CONF_TOKEN: TOKEN, **data_extra},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def unique(entry: MockConfigEntry, key: str) -> str:
    return f"{entry.entry_id}_{key}"
