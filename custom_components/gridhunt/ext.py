"""Optional extension packages.

Any sub-package of this integration that sets ``GRIDHUNT_EXTENSION = True`` is
picked up here. An extension declares ``FEATURE`` (the key in ``/api/ha/me``
``features`` that switches it on) and may provide:

* ``INTERVAL`` and ``async_update(client)`` - extra polled data
* ``async_setup(hass)`` / ``async_unload(hass)`` - domain level hooks
* ``async_setup_entry(hass, coordinator)`` / ``async_unload_entry(hass, coordinator)``
* ``sensor_entities(coordinator)`` - extra sensor entities
* ``card_payload(coordinator)`` - extra keys for the websocket card payload

If no extension package is present, nothing happens.
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from types import ModuleType

from .const import LOGGER


def load_extensions() -> list[ModuleType]:
    """Import extension sub-packages (blocking; run in an executor)."""
    found: list[ModuleType] = []
    for info in pkgutil.iter_modules([str(Path(__file__).parent)]):
        if not info.ispkg:
            continue
        try:
            module = importlib.import_module(f"{__package__}.{info.name}")
        except ImportError:
            continue
        except Exception:  # noqa: BLE001 - a broken extension must not break the core
            LOGGER.exception("Extension %s failed to load", info.name)
            continue
        if getattr(module, "GRIDHUNT_EXTENSION", False):
            found.append(module)
    return found
