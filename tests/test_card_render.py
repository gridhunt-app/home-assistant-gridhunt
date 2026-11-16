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
    # year chips, stats and the playback bar like the iOS Map screen
    t = r["text"]
    assert "Wszystkie lata" in t and "2026" in t and "2025" in t
    assert "Odwiedzone" in t and "Rekord" in t and "Kwartał" in t and "×4" in t and "Podkład" not in t
    assert 'data-tplay="1"' in r["html"] and 'aria-label="Odtwórz wybrane lata"' in r["html"] and 'id="ghslider"' in r["html"]


def test_idle_tile_map_year_filter_and_play():
    tiles = {"tiles": _block(9000, 5300, 4), "square": {"x": 9000, "y": 5300, "s": 4}, "target": None,
             "view": {"x0": 8996, "y0": 5296, "x1": 9007, "y1": 5307}, "generated": None,
             "visits": {"2025": [v for i in range(12) for v in (i, 10 + i)], "2026": [v for i in range(12, 16) for v in (i, 5)]}}

    def act(pg):
        # all years selected: tapping a year keeps only that year (iOS YearFilter.tap)
        pg.locator("gridhunt-card").locator("[data-year='2026']").click()
        pg.wait_for_timeout(100)

    r = render(payload(STATE_IDLE) | {"tiles": tiles}, extra=False, actions=act, shot="card-idle-2026")
    assert not r["errors"], r["errors"]
    assert r["svg"].count('class="own nw"') == 4  # 2026: four tiles, all new that year
    assert r["svg"].count('class="own') == 4
    assert "Nowe w 2026" in r["text"] and "+4" in r["text"]

    def add(pg):
        pg.locator("gridhunt-card").locator("[data-year='2026']").click()
        pg.wait_for_timeout(100)
        pg.locator("gridhunt-card").locator("[data-year='2025']").click()  # unselected year: added
        pg.wait_for_timeout(100)

    r = render(payload(STATE_IDLE) | {"tiles": tiles}, extra=False, actions=add)
    assert r["svg"].count('class="own') == 16 and "Nowe w" not in r["text"]
    assert "class=\"ychip on\" data-yall=\"1\"" in r["html"]  # both years = all years again

    def play(pg):
        pg.locator("gridhunt-card").locator("#ghstep").select_option("day")  # day steps: still playing when checked
        pg.locator("gridhunt-card").locator("[data-tplay]").click()
        pg.wait_for_timeout(300)

    r = render(payload(STATE_IDLE) | {"tiles": tiles}, extra=False, actions=play, shot="card-idle-play")
    assert not r["errors"], r["errors"]
    assert 'aria-label="Pauza"' in r["html"]
    assert r["svg"].count('class="own') < 16  # playback starts from the beginning

    def layers(pg):
        pg.locator("gridhunt-card").locator("[data-layers]").click()
        pg.wait_for_timeout(100)
        pg.locator("gridhunt-card").locator("[data-ov='tiles']").uncheck()
        pg.wait_for_timeout(100)

    r = render(payload(STATE_IDLE) | {"tiles": tiles}, extra=False, actions=layers)
    assert "Podkład" in r["text"] and "Szczegółowy" in r["text"] and "Moje kafle" in r["text"]
    assert 'class="own' not in r["svg"] and 'class="sq"' in r["svg"]


def test_timeline_advance_matches_ios():
    """Port of the iOS/web timeline: quarter steps close the quarter, then jump to the next quarter end."""
    from .card.harness import evaluate_card

    res = evaluate_card("""(() => { const T = window.__ghTimeline; const td = {year: 2026, doy: 320}, ys = [2025, 2026];
      const out = []; let p = 0; for (let i = 0; i < 6; i++) { p = T.advance(p, "quarter", ys, td); out.push(T.playhead(p, ys, td)); }
      return {total: T.total(ys, td), out, week: T.advance(10, "week", ys, td), year: T.advance(1, "year", ys, td)}; })()""")
    assert res["total"] == 365 + 320
    assert [(o["year"], o["doy"]) for o in res["out"]] == [(2025, 90), (2025, 181), (2025, 273), (2025, 365), (2026, 90), (2026, 181)]
    assert res["week"] == 17 and res["year"] == 365


# ---- dashboard / view strategy (custom:gridhunt) ----
_KEYS = {"binary_sensor": ["riding"], "device_tracker": ["position"],
         "sensor": ["progress_pct", "distance_done_km", "distance_left_km", "distance_km", "new_tiles", "square", "tiles_total", "tiles_this_year", "last_ride"]}


def _strategy_hass(skip=(), lang="pl", extra=True):
    ents, states = {}, {}
    for dom, keys in _KEYS.items():
        for k in keys:
            if k in skip:
                continue
            eid = f"{dom}.gh_{k}"
            ents[eid] = {"entity_id": eid, "platform": "gridhunt", "translation_key": k, "device_id": "d1"}
            states[eid] = {"state": "1"}
    if extra:
        ents["sensor.gh_odd"] = {"entity_id": "sensor.gh_odd", "platform": "gridhunt", "translation_key": None, "device_id": "d1"}
        states["sensor.gh_odd"] = {"state": "1"}
    ents["sensor.other"] = {"entity_id": "sensor.other", "platform": "hue", "device_id": "d9"}
    states["sensor.other"] = {"state": "1"}
    return {"entities": ents, "states": states, "devices": {"d1": {"name": "Łucja", "config_entries": ["e1"]}}, "locale": {"language": lang}}


def _generate(kind, hass, config=None):
    import json
    from .card.harness import evaluate_card
    return evaluate_card(f"customElements.get('ll-strategy-{kind}-gridhunt').generate({json.dumps(config or {})}, {json.dumps(hass)})")


def test_strategy_view_layout_pl():
    pytest.importorskip("playwright.sync_api")
    v = _generate("view", _strategy_hass())
    assert v["type"] == "sections" and v["max_columns"] == 3
    assert [b["entity"] for b in v["badges"]] == ["binary_sensor.gh_riding", "sensor.gh_tiles_total", "sensor.gh_square"]
    assert v["badges"][0]["color"] == "green" and v["badges"][0]["show_name"] is True
    live, rest = v["sections"]
    assert live["column_span"] == 2
    assert [c["type"] for c in live["cards"]] == ["heading", "custom:gridhunt-card", "map"]
    assert live["cards"][0]["heading"] == "Jazda na żywo" and live["cards"][0]["icon"] == "mdi:map-marker-path"
    assert live["cards"][1]["map"] == "live-page" and live["cards"][1]["grid_options"] == {"columns": "full"}
    m = live["cards"][2]
    assert m["entities"] == [{"entity": "device_tracker.gh_position"}] and m["hours_to_show"] == 12 and m["default_zoom"] == 14 and m["auto_fit"] is True
    assert m["grid_options"] == {"rows": 8}
    cards = rest["cards"]
    heads = [c["heading"] for c in cards if c["type"] == "heading"]
    assert heads == ["Bieżąca jazda", "Konto"]
    names = [c["name"] for c in cards if c["type"] == "tile" and "name" in c]
    assert names == ["Jadę", "Dystans", "Przejechane", "Do mety", "Postęp trasy", "Nowe kafle", "Kafle", "Kwadrat", "Nowe w tym roku", "Ostatnia jazda"]
    assert all(c["grid_options"] == {"columns": 6} for c in cards if c["type"] == "tile")
    assert cards[-1] == {"type": "tile", "entity": "sensor.gh_odd", "grid_options": {"columns": 6}}  # unknown account entity, no name override
    assert "sensor.other" not in str(v)


def test_strategy_view_skips_missing_entities_and_english():
    pytest.importorskip("playwright.sync_api")
    v = _generate("view", _strategy_hass(skip={"position", "last_ride", "riding"}, lang="de", extra=False))
    assert [b["entity"] for b in v["badges"]] == ["sensor.gh_tiles_total", "sensor.gh_square"]
    live, rest = v["sections"]
    assert [c["type"] for c in live["cards"]] == ["heading", "custom:gridhunt-card"]  # no tracker -> no map
    assert live["cards"][0]["heading"] == "Live ride"
    ents = [c["entity"] for c in rest["cards"] if c["type"] == "tile"]
    assert "binary_sensor.gh_riding" not in ents and "sensor.gh_last_ride" not in ents
    assert [c["name"] for c in rest["cards"] if c["type"] == "tile"][0] == "Distance"


def test_strategy_dashboard_and_empty():
    pytest.importorskip("playwright.sync_api")
    d = _generate("dashboard", _strategy_hass())
    assert d["views"] == [{"title": "Gridhunt", "path": "gridhunt", "icon": "mdi:bike", "strategy": {"type": "custom:gridhunt"}}]
    v = _generate("view", {"entities": {}, "states": {}, "locale": {"language": "en"}})
    assert v["sections"][0]["cards"][0]["type"] == "markdown"
    from .card.harness import evaluate_card
    assert evaluate_card("window.customStrategies.filter(c => c.type === 'gridhunt').map(c => c.strategyType)") == ["dashboard"]
