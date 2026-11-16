"""Render the Lovelace card in Chromium (Playwright) with a fake `hass` object."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

WWW = Path(__file__).resolve().parents[2] / "custom_components" / "gridhunt" / "www"

PAGE = """<!doctype html><html><head><meta charset="utf-8">
<style>body{margin:0;padding:16px;font-family:system-ui,sans-serif;background:%(bg)s;color:%(fg)s;
--primary-color:#2447e0;--secondary-text-color:%(muted)s;--divider-color:%(line)s;--card-background-color:%(card)s;--secondary-background-color:%(bg2)s}
ha-card{display:block;background:var(--card-background-color);border-radius:16px;box-shadow:0 2px 10px rgba(0,0,0,.15)}</style>
</head><body><div style="max-width:%(width)spx"><gridhunt-card id="c"></gridhunt-card></div>
<script>window.__calls=[];</script>%(scripts)s
<script>
const payload = %(payload)s, routes = %(routes)s;
const el = document.getElementById("c");
el.setConfig(%(config)s);
el.hass = { locale: { language: "%(lang)s" }, language: "%(lang)s",
  callWS: async (m) => m.type === "gridhunt/card" ? payload : routes[m.route_id],
  callService: async (d, s, data) => { window.__calls.push([d, s, data]); } };
</script></body></html>"""

THEMES = {
    "light": {"bg": "#f3f4f6", "fg": "#111", "muted": "#5b6470", "line": "rgba(0,0,0,.12)", "card": "#fff", "bg2": "#eef1f6"},
    "dark": {"bg": "#111418", "fg": "#f2f4f7", "muted": "#9aa4b2", "line": "rgba(255,255,255,.14)", "card": "#1c2026", "bg2": "#151a20"},
}


def render(payload: dict[str, Any], *, extra: bool, routes: dict[str, Any] | None = None, lang: str = "pl", theme: str = "light",
           width: int = 520, config: dict[str, Any] | None = None, shot: str | None = None, actions=None) -> dict[str, Any]:
    from playwright.sync_api import sync_playwright

    # extension scripts (gridhunt-card-*.js) exist only in some builds
    files = ["gridhunt-card.js"] + (sorted(f.name for f in WWW.glob("gridhunt-card-*.js")) if extra else [])
    scripts = "".join(f"<script>{(WWW / f).read_text()}</script>" for f in files)
    html = PAGE % {**THEMES[theme], "width": width, "scripts": scripts, "payload": json.dumps(payload), "routes": json.dumps(routes or {}),
                   "config": json.dumps(config or {"map": "svg"}), "lang": lang}
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": width + 32, "height": 900}, color_scheme=theme)
        errors: list[str] = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.set_content(html)
        pg.wait_for_timeout(400)
        if actions:
            actions(pg)
            pg.wait_for_timeout(300)
        text = pg.evaluate("document.getElementById('c').shadowRoot.textContent")
        svg = pg.evaluate("(() => { const s = document.getElementById('c').shadowRoot.querySelector('svg.map'); return s ? s.outerHTML : ''; })()")
        calls = pg.evaluate("window.__calls")
        shadow = pg.evaluate("document.getElementById('c').shadowRoot.innerHTML")
        out_dir = os.environ.get("GRIDHUNT_CARD_SHOTS")
        if shot and out_dir:
            pg.locator("gridhunt-card").screenshot(path=str(Path(out_dir) / f"{shot}.png"))
        b.close()
    return {"text": text, "svg": svg, "calls": calls, "errors": errors, "html": shadow}


def evaluate_card(expr: str) -> Any:
    """Evaluate `expr` in a page with the card script loaded (pure helpers exposed for tests)."""
    from playwright.sync_api import sync_playwright

    html = "<!doctype html><html><body><script>" + (WWW / "gridhunt-card.js").read_text() + "</script></body></html>"
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page()
        pg.set_content(html)
        out = pg.evaluate(expr)
        b.close()
    return out
