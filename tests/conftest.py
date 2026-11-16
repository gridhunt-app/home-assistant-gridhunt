"""Fixtures."""

from __future__ import annotations

from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def _enable_custom(enable_custom_integrations):
    yield


@pytest.fixture(autouse=True)
def _frontend_stub(hass):
    """The real frontend package is not installed for tests."""
    hass.config.components.add("frontend")
    with patch("custom_components.gridhunt.frontend.add_extra_js_url") as add:
        yield add
