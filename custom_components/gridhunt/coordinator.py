"""Data coordinator for Gridhunt."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import timedelta
import time
from types import ModuleType
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApiError, AuthError, GridhuntClient, ScopeError
from .const import (
    DOMAIN,
    EVENT_NEW_SQUARE,
    EVENT_RIDE_FINISHED,
    EVENT_RIDE_STARTED,
    KNOWN_EVENTS,
    LIVE_MAX_AGE,
    LOGGER,
    ME_INTERVAL,
    POLL_IDLE,
    POLL_RIDING,
    RETRY_INTERVAL,
    ROUTES_INTERVAL,
    STATS_INTERVAL,
)


@dataclass
class GridhuntData:
    """Snapshot handed to entities."""

    me: dict[str, Any]
    state: dict[str, Any]
    live: dict[str, Any] | None = None
    stats: dict[str, Any] = field(default_factory=dict)
    routes: list[dict[str, Any]] = field(default_factory=list)
    ext: dict[str, Any] = field(default_factory=dict)

    @property
    def riding(self) -> bool:
        return bool(self.state.get("riding"))

    @property
    def features(self) -> dict[str, Any]:
        return self.me.get("features") or {}


@dataclass
class GridhuntRuntime:
    """Stored in ConfigEntry.runtime_data."""

    client: GridhuntClient
    coordinator: GridhuntCoordinator
    webhook_id: str


type GridhuntConfigEntry = ConfigEntry[GridhuntRuntime]


def _square_size(state: dict[str, Any] | None) -> int | None:
    sq = (state or {}).get("square")
    if isinstance(sq, dict):
        size = sq.get("size")
    else:
        size = sq
    return size if isinstance(size, (int, float)) and not isinstance(size, bool) else None


class GridhuntCoordinator(DataUpdateCoordinator[GridhuntData]):
    """Polls the Gridhunt API with per-endpoint cadences."""

    config_entry: GridhuntConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: GridhuntConfigEntry,
        client: GridhuntClient,
        candidates: list[ModuleType],
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=POLL_IDLE),
        )
        self.client = client
        self.candidates = candidates
        self.extensions: list[ModuleType] = []
        self._ext_names: frozenset[str] | None = None
        self._next: dict[str, float] = {}
        self._me: dict[str, Any] | None = None
        self._stats: dict[str, Any] = {}
        self._routes: list[dict[str, Any]] = []
        self._ext_data: dict[str, Any] = {}
        self._live: dict[str, Any] | None = None
        self._live_at: float | None = None
        self._tiles: dict[str, Any] | None = None
        self._tiles_at: float | None = None
        self._prev_state: dict[str, Any] | None = None
        self._fired: OrderedDict[str, None] = OrderedDict()

    # ------------------------------------------------------------------ helpers
    def _due(self, key: str, interval: float) -> bool:
        now = time.monotonic()
        if now < self._next.get(key, 0):
            return False
        self._next[key] = now + interval
        return True

    def force_refresh_all(self) -> None:
        """Make every cadence due on the next update."""
        self._next.clear()

    async def _required[T](self, fn: Callable[[], Awaitable[T]]) -> T:
        try:
            return await fn()
        except AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (ScopeError, ApiError) as err:
            raise UpdateFailed(str(err)) from err

    async def _optional[T](
        self, key: str, interval: float, fn: Callable[[], Awaitable[T]], default: T
    ) -> T:
        if not self._due(key, interval):
            return default
        try:
            return await fn()
        except AuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except (ScopeError, ApiError) as err:
            LOGGER.debug("Endpoint %s failed: %s", key, err)
            self._next[key] = time.monotonic() + RETRY_INTERVAL
            return default

    # ------------------------------------------------------------------- update
    async def _async_update_data(self) -> GridhuntData:
        if self._me is None:
            self._me = await self._required(self.client.me)
            self._due("me", ME_INTERVAL)
        else:
            self._me = await self._optional("me", ME_INTERVAL, self.client.me, self._me)

        self._sync_extensions(self._me)

        state = await self._required(self.client.state)
        riding = bool(state.get("riding"))

        self._stats = await self._optional(
            "stats", STATS_INTERVAL, self.client.stats, self._stats
        )
        self._routes = await self._optional(
            "routes", ROUTES_INTERVAL, self.client.routes, self._routes
        )

        if riding:
            live = await self._optional("live", 0, self.client.live, self._live)
            if live is not self._live:
                self._live_at = time.monotonic()
            self._live = live
        else:
            self._live = None
            self._live_at = None
            self._next.pop("live", None)

        for ext in self.extensions:
            update = getattr(ext, "async_update", None)
            if update is None:
                continue
            name = ext.__name__
            self._ext_data[name] = await self._optional(
                f"ext:{name}",
                getattr(ext, "INTERVAL", 600),
                lambda update=update: update(self.client),
                self._ext_data.get(name),
            )

        prev, self._prev_state = self._prev_state, state
        if prev is not None:
            self._detect_transitions(prev, state)

        self.update_interval = timedelta(seconds=POLL_RIDING if riding else POLL_IDLE)
        return GridhuntData(
            me=self._me,
            state=state,
            live=self._live,
            stats=self._stats,
            routes=self._routes,
            ext={k: v for k, v in self._ext_data.items() if v is not None},
        )

    def _sync_extensions(self, me: dict[str, Any]) -> None:
        features = me.get("features") or {}
        active = [e for e in self.candidates if features.get(getattr(e, "FEATURE", ""))]
        names = frozenset(e.__name__ for e in active)
        if self._ext_names is not None and names != self._ext_names:
            # Feature switched on or off on the server: rebuild entities.
            self.hass.config_entries.async_schedule_reload(self.config_entry.entry_id)
        self._ext_names = names
        self.extensions = active

    async def async_fetch_tiles(self) -> dict[str, Any] | None:
        """Tile map for the card when nobody rides; fetched on demand, cached for STATS_INTERVAL.

        Not stored in coordinator data (no entity attributes, nothing in the recorder). An older server
        without /api/ha/tiles answers 404: the card then shows only the routes.
        """
        now = time.monotonic()
        if self._tiles_at is not None and now - self._tiles_at < STATS_INTERVAL:
            return self._tiles
        try:
            self._tiles = await self.client.tiles()
        except (AuthError, ScopeError, ApiError) as err:
            LOGGER.debug("Tiles fetch failed: %s", err)
            self._tiles = None
        self._tiles_at = now
        return self._tiles

    async def async_fetch_live(self, max_age: float = LIVE_MAX_AGE) -> dict[str, Any] | None:
        """Return live data, fetching it if riding and older than max_age."""
        data = self.data
        if data is None or not data.riding:
            return None
        if (
            self._live is None
            or self._live_at is None
            or time.monotonic() - self._live_at > max_age
        ):
            try:
                self._live = await self.client.live()
                self._live_at = time.monotonic()
            except (AuthError, ScopeError, ApiError) as err:
                LOGGER.debug("On-demand live fetch failed: %s", err)
            data.live = self._live
        return self._live

    # ------------------------------------------------------------------- events
    def _detect_transitions(self, prev: dict[str, Any], cur: dict[str, Any]) -> None:
        was, now = bool(prev.get("riding")), bool(cur.get("riding"))
        if not was and now:
            self.async_handle_event(
                EVENT_RIDE_STARTED, self._poll_payload(EVENT_RIDE_STARTED, prev, cur), "poll"
            )
        elif was and not now:
            self.async_handle_event(
                EVENT_RIDE_FINISHED, self._poll_payload(EVENT_RIDE_FINISHED, prev, cur), "poll"
            )
        elif was and now:
            a, b = _square_size(prev), _square_size(cur)
            if a is not None and b is not None and b > a:
                self.async_handle_event(
                    EVENT_NEW_SQUARE, self._poll_payload(EVENT_NEW_SQUARE, prev, cur), "poll"
                )

    @staticmethod
    def _poll_payload(event: str, prev: dict[str, Any], cur: dict[str, Any]) -> dict[str, Any]:
        src = prev if event == EVENT_RIDE_FINISHED else cur
        last = cur.get("lastRide") or {}
        payload: dict[str, Any] = {
            "event": event,
            "kind": src.get("kind"),
            "routeName": src.get("routeName"),
            "startedAt": src.get("startedAt"),
            "endedAt": last.get("endedAt") if event == EVENT_RIDE_FINISHED else None,
            "distanceKm": (
                last.get("distanceKm")
                if event == EVENT_RIDE_FINISHED
                else cur.get("distanceKm")
            ),
            "progress": src.get("progress"),
            "tiles": cur.get("tiles"),
            "square": cur.get("square"),
            "riding": bool(cur.get("riding")),
            "liveUrl": cur.get("liveUrl"),
        }
        if event == EVENT_NEW_SQUARE:
            payload["square"] = {"from": _square_size(prev), "to": _square_size(cur)}
        return payload

    @staticmethod
    def _dedupe_keys(event: str, payload: dict[str, Any]) -> list[str]:
        keys: list[str] = []
        if delivery := payload.get("deliveryId"):
            keys.append(f"d:{delivery}")
        started = payload.get("startedAt")
        if event == EVENT_NEW_SQUARE:
            sq = payload.get("square")
            to = sq.get("to") if isinstance(sq, dict) else sq
            keys.append(f"sq:{started}:{to}")
        elif event in (EVENT_RIDE_STARTED, EVENT_RIDE_FINISHED) and started:
            keys.append(f"{event}:{started}")
        return keys

    def async_handle_event(self, event: str, payload: dict[str, Any], source: str) -> bool:
        """Fire gridhunt_<event> once per logical event. Returns True if fired."""
        if event not in KNOWN_EVENTS:
            return False
        keys = self._dedupe_keys(event, payload)
        if any(k in self._fired for k in keys):
            for k in keys:
                self._fired[k] = None
            return False
        for k in keys:
            self._fired[k] = None
        while len(self._fired) > 100:
            self._fired.popitem(last=False)
        data = {
            **payload,
            "event": event,
            "source": source,
            "entry_id": self.config_entry.entry_id,
        }
        self.hass.bus.async_fire(f"{DOMAIN}_{event}", data)
        return True
