"""Lovelace card renders in a real browser (core features only)."""

from __future__ import annotations

import copy

import pytest

from .common import LIVE, STATE_IDLE, STATE_RIDING

pw = pytest.importorskip("playwright.sync_api")
from .card.harness import render  # noqa: E402

STATS = {"name": "Łucja", "tilesZ14": 5321, "tilesZ17": 41876, "uber": 14, "newThisYear": 312, "targetPct": None, "rides": {"count": 214, "lastAt": None}}
ROUTES = [{"id": "r1", "name": "Pętla przez Puszczę", "km": 63.8, "ascentM": 420, "tileCount": 80, "createdAt": "2026-10-20T10:00:00Z"}]
ROUTE = {"r1": {"id": "r1", "name": "Pętla przez Puszczę", "km": 63.8, "ascentM": 420, "line": [[[53.40, 14.50], [53.45, 14.58], [53.50, 14.52], [53.42, 14.45]]]}}


def payload(state, live=None):
    return {"entry_id": "e1", "features": {}, "me": {"name": "Łucja"}, "state": state, "live": live, "stats": STATS, "routes": ROUTES}


def test_riding_map_stats_moments():
    live = copy.deepcopy(LIVE)
    r = render(payload(STATE_RIDING, live), extra=False, shot="card-riding")
    assert not r["errors"], r["errors"]
    t = r["text"]
    assert "Pętla przez Puszczę" in t and "NA ŻYWO" in t
    assert "przejechane" in t and "do mety" in t and "+9" in t and "12×12" in t
    assert 'class="route"' in r["svg"] and 'class="me"' in r["svg"]


def test_idle_last_ride_stats_and_route_map():
    r = render(payload(STATE_IDLE), extra=False, routes=ROUTE, shot="card-idle")
    assert not r["errors"], r["errors"]
    t = r["text"]
    assert "Teraz nikt nie jedzie" in t and "Ostatnia jazda" in t and "Zaplanowane trasy" in t
    assert "5" in t and "14×14" in t


def test_english_and_live_page_mode():
    r = render(payload(STATE_RIDING, copy.deepcopy(LIVE)), extra=False, lang="en", config={"map": "live-page"})
    assert "LIVE" in r["text"] and "to go" in r["text"]
    assert r["svg"] == ""


def _block(x0, y0, n):
    return [v for i in range(n * n) for v in (x0 + i % n, y0 + i // n)]


def test_idle_tile_map_square_and_target():
    tiles = {"tiles": _block(9000, 5300, 14) + _block(9016, 5302, 3), "square": {"x": 9000, "y": 5300, "s": 14},
             "target": {"x0": 8999, "y0": 5299, "x1": 9015, "y1": 5315, "name": "Cel"}, "view": {"x0": 8993, "y0": 5293, "x1": 9021, "y1": 5321}, "generated": None,
             "visits": {"2025": [v for i in range(196) for v in (i, 1 + i % 300)], "2026": [v for i in range(196, 205) for v in (i, 40)] + [0, 50]}}
    p = payload(STATE_IDLE) | {"tiles": tiles}
    r = render(p, extra=False, routes=ROUTE, shot="card-idle-tiles")
    assert not r["errors"], r["errors"]
    assert 'class="own"' in r["svg"] and 'class="sq"' in r["svg"] and 'class="tgt"' in r["svg"]
    assert "14×14" in r["text"] and "17×17" in r["text"]
    # with the tile map the route map waits for a tap
    assert 'class="route"' not in r["svg"]
    # year filter chips and play button
    assert "Wszystko" in r["text"] and "2026" in r["text"] and "2025" in r["text"] and "Odtwórz" in r["text"]


def test_idle_tile_map_year_filter_and_play():
    tiles = {"tiles": _block(9000, 5300, 4), "square": {"x": 9000, "y": 5300, "s": 4}, "target": None,
             "view": {"x0": 8996, "y0": 5296, "x1": 9007, "y1": 5307}, "generated": None,
             "visits": {"2025": [v for i in range(12) for v in (i, 10 + i)], "2026": [v for i in range(12, 16) for v in (i, 5)]}}

    def act(pg):
        pg.locator("gridhunt-card").locator("[data-tyear='2026']").click()
        pg.wait_for_timeout(100)

    r = render(payload(STATE_IDLE) | {"tiles": tiles}, extra=False, actions=act, shot="card-idle-2026")
    assert not r["errors"], r["errors"]
    assert r["svg"].count('class="own nw"') == 4  # 2026: four tiles, all new that year

    def play(pg):
        pg.locator("gridhunt-card").locator("[data-tplay]").click()
        pg.wait_for_timeout(1500)

    r = render(payload(STATE_IDLE) | {"tiles": tiles}, extra=False, actions=play, shot="card-idle-play")
    assert not r["errors"], r["errors"]
    assert "Pauza" in r["text"]
