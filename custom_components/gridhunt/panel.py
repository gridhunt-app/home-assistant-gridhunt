"""Sidebar panel "Gridhunt": one panel for all accounts, rendered by gridhunt-card.js.

Public API only: panel_custom.async_register_panel / frontend.async_remove_panel.
The panel element (gridhunt-panel) builds the same layout as the custom:gridhunt view strategy.
"""

from __future__ import annotations

from homeassistant.components import frontend, panel_custom
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import CONF_SHOW_PANEL, DEFAULT_SHOW_PANEL, DOMAIN, LOGGER

PANEL_URL = "gridhunt"
PANEL_ELEMENT = "gridhunt-panel"
PANEL_TITLE = "gridhunt"  # lower case like the logo (owner decision 16.11.2026), all languages
PANEL_ICON = "gridhunt:mark"  # icon set registered by gridhunt-card.js
FALLBACK_ICON = "mdi:bike"

_ENTRIES = "panel_entries"
_REGISTERED = "panel_registered"


def show_panel(entry: ConfigEntry) -> bool:
    """Option "Show Gridhunt in the sidebar" (on by default)."""
    return bool(entry.options.get(CONF_SHOW_PANEL, DEFAULT_SHOW_PANEL))


def _data(hass: HomeAssistant) -> dict:
    return hass.data.setdefault(DOMAIN, {})


@callback
def async_track_entry(hass: HomeAssistant, entry: ConfigEntry, active: bool) -> None:
    """Mark an account as wanting the panel (or not) and add/remove the panel to match."""
    entries: set[str] = _data(hass).setdefault(_ENTRIES, set())
    if active and show_panel(entry):
        entries.add(entry.entry_id)
    else:
        entries.discard(entry.entry_id)
    async_sync(hass)


@callback
def async_sync(hass: HomeAssistant) -> None:
    """Register the panel while at least one account wants it; remove it otherwise."""
    data = _data(hass)
    wanted = bool(data.get(_ENTRIES))
    if wanted and not data.get(_REGISTERED):
        card_url = data.get("card_url")
        if not card_url:
            return  # frontend files not served (no http), nothing to render the panel with
        hass.async_create_task(_async_register(hass, card_url), eager_start=True)
        data[_REGISTERED] = True
    elif not wanted and data.get(_REGISTERED):
        frontend.async_remove_panel(hass, PANEL_URL, warn_if_unknown=False)
        data[_REGISTERED] = False


async def _async_register(hass: HomeAssistant, card_url: str) -> None:
    try:
        await panel_custom.async_register_panel(
            hass,
            frontend_url_path=PANEL_URL,
            webcomponent_name=PANEL_ELEMENT,
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON if _data(hass).get("card_file") else FALLBACK_ICON,
            module_url=card_url,
            require_admin=False,
        )
    except ValueError:
        # another panel already uses /gridhunt (e.g. a YAML panel_custom): leave it alone
        LOGGER.warning("Sidebar panel /%s already exists, Gridhunt panel not added", PANEL_URL)
        _data(hass)[_REGISTERED] = False
