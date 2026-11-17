"""Constants for the Gridhunt integration."""

from __future__ import annotations

import logging

DOMAIN = "gridhunt"
LOGGER = logging.getLogger(__package__)

CONF_BASE_URL = "base_url"
CONF_TOKEN = "token"
CONF_WEBHOOK_ID = "webhook_id"
CONF_WEBHOOK_SECRET = "webhook_secret"
CONF_WEBHOOK_URL = "webhook_url"
CONF_CLOUDHOOK = "cloudhook"

# Options
CONF_SHOW_PANEL = "show_panel"
DEFAULT_SHOW_PANEL = True

DEFAULT_BASE_URL = "https://gridhunt.app"
PAIR_NAME = "Home Assistant"

# Polling (seconds)
POLL_RIDING = 20  # fallback when no webhook push is registered
POLL_RIDING_PUSH = 60  # webhook delivers ride events; polling is only a safety net
POLL_IDLE = 60
STATS_INTERVAL = 15 * 60
ROUTES_INTERVAL = 30 * 60
ME_INTERVAL = 60 * 60
RETRY_INTERVAL = 60
LIVE_MAX_AGE = 15

# Events fired on the HA bus (gridhunt_<name>)
EVENT_RIDE_STARTED = "ride_started"
EVENT_RIDE_FINISHED = "ride_finished"
EVENT_NEW_SQUARE = "new_square"
EVENT_TEST = "test"
KNOWN_EVENTS = (EVENT_RIDE_STARTED, EVENT_RIDE_FINISHED, EVENT_NEW_SQUARE, EVENT_TEST)

SIGNATURE_HEADER = "X-Gridhunt-Signature"
SIGNATURE_TOLERANCE = 300

# route ids as the server issues them (lowercase alnum, 20-32 chars); wider on purpose, never "/" or "."
ROUTE_ID_RE = r"^[A-Za-z0-9_-]{1,64}$"

STATIC_URL = "/gridhunt_static"
CARD_FILE = "gridhunt-card.js"

SERVICE_REFRESH = "refresh"
